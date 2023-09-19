#!/usr/bin/env python3
import argparse
import csv
import importlib.util
from collections import defaultdict

import osmium

from comparators import distance_m, tags_m
from src.geodistance import geodistance
from src.place_handlers import GovHandler, OsmHandler


parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
parser.add_argument('-p', '--prepare', action='store_true')
# parser.add_argument('-g', '--geocode', choices=['nominatim', 'komoot'], default='nominatim', type=str.lower)
args = parser.parse_args()

print(f'Importing conf/{args.name}_conf.py')
config = importlib.import_module(f'conf.{args.name}_conf')

if args.prepare:
    f_in = open(f'input/{args.name}_gov.csv', 'r')
    f_out = open(f'input/{args.name}_gov_clean.csv', 'w') 
    tags = config.prepare['tags']
    r_in = csv.DictReader(f_in,
        delimiter=config.prepare.get('separator', ','),
        quotechar=config.prepare.get('quote', '"'))
    r_out = csv.DictWriter(f_out, fieldnames=tags.keys())
    r_out.writeheader()
    for row in r_in:
        # print(row)
        if config.prepare.get('accept'):
            if not config.prepare['accept'](row):
                continue
        new_row = {}
        for key, value in tags.items():
            if type(value) is str:
                new_row[key] = row.get(value, '').strip()
            elif callable(value):
                new_row[key] = (value(row) or '').strip()
            else:
                raise NotImplementedError
        r_out.writerow(new_row)

# add addresses to osm
osm = OsmHandler(args.name)
osm.apply_file(f'input/{args.name}.osm')
osm.add_addresses()

# add cords to gov
gov = GovHandler(args.name)
gov.import_csv(f'input/{args.name}_gov_clean.csv')



# match
mapping = {
    'osm': defaultdict(list),
    'gov': defaultdict(list)
}

for rule in config.matching:
    print(f'Matching with rule: {rule}')

    if isinstance(rule, str):
        if rule.split(':')[0] == 'location':
            max_dist = int(rule.split(':')[1])
            output = distance_m(gov.match, osm.all, osm.match, max_dist)
            mapping['osm'].update(output.get('osm'))
            mapping['gov'].update(output.get('gov'))
        else:
            raise NotImplementedError(f'rule {rule} not supported!')
    elif isinstance(rule, list):
        output = tags_m(rule, gov.match, osm.all, osm.match)
        mapping['osm'].update(output.get('osm'))
        mapping['gov'].update(output.get('gov'))
    else:
        raise NotImplementedError(f'rule {rule} not supported!')

# for arr in mapping.values():
    # print([x for x in arr])

new_writer = osmium.SimpleWriter(f'output/{args.name}_cooperative.osm')
edit_writer = osmium.SimpleWriter(f'output/{args.name}_tagfix.osm')

for g in gov.all.keys():
    # print(g)
    tags_e, location_e = {}, {}
    writer, edit = new_writer, False

    for t, tv in dict(gov.all[g].tags).items():
        if tv:
            tags_e[t] = tv

    tags_e.update(config.tags_to_add)

    if g in mapping['gov'] and len(mapping['gov'].get(g, [])) == 1:
        # print('MATCH')
        o = mapping['gov'].get(g)[0]

        for k,v in dict(osm.all[o].tags).items():
            if k in config.tags_to_delete:
                val_to_del = config.tags_to_delete[k]
                if val_to_del == '*' or v == val_to_del:
                    continue
            tags_e.update({k: v})

        # print(o)
        if o[0] == 'N':
            node = osmium.osm.mutable.Node(
                osm.all[o],
                tags = tags_e
                )
            edit_writer.add_node(node)
        elif o[0] == 'W':
            # May contain bugs
            way = osmium.osm.mutable.Way(
                osm.all[o],
                tags = tags_e
            )
            edit_writer.add_way(way)
            print(osm.waynodes)
        else:
            raise NotImplementedError(o)

    else:
        # print('NEW')
        m = gov.match.get(g)
        if m:
            location_e = m.location
            
            # print(tags_e, location_e, gov.all[g].id)
            node = osmium.osm.mutable.Node(
                tags = tags_e,
                location = location_e,
                id = int(gov.all[g].id)
            )
            new_writer.add_node(node)
    