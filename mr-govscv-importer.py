#!/usr/bin/env python3
import argparse
import csv
import fileinput
import importlib.util
from collections import defaultdict
import subprocess
from time import sleep

import osmium
from rich.console import Console
from rich.live import Live
from rich.progress import track

from comparators import distance_m, tags_m
from src.check_files import check_files
from src.place_handlers import GovHandler, OsmHandler

console = Console()
parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
parser.add_argument('-p', '--prepare', action='store_true')
# parser.add_argument('-g', '--geocode', choices=['nominatim', 'komoot'], default='nominatim', type=str.lower)
args = parser.parse_args()

check_files(args.name, args.prepare)

console.log(f'[bold]Importing conf/{args.name}_conf.py')
config = importlib.import_module(f'conf.{args.name}_conf')

if args.prepare:
    console.log(f'Starting preparation step...')
    
    f_in = open(f'input/{args.name}_gov.csv', 'r')
    f_out = open(f'input/{args.name}_gov_clean.csv', 'w') 
    tags = config.prepare['tags']
    r_in = csv.DictReader(f_in,
        delimiter=config.prepare.get('separator', ','),
        quotechar=config.prepare.get('quote', '"'))
    r_out = csv.DictWriter(f_out, fieldnames=tags.keys())
    r_out.writeheader()

    for row in track(r_in, description='Preparing gov data'):
        with console.status("Preparation starting") as status:
            status.update(f'Processing {row}')

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
                raise NotImplementedError(f'Error! Preparation rule: {key, value} not supported!')
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
    console.log(f'Matching with rule: {rule}')

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
    
    new = sum(filter(lambda x: x == 1, [len(x) for x in mapping['gov'].values()]))
    console.log(f'Found {new} new matches for gov data')

new_writer = osmium.SimpleWriter(f'output/{args.name}_cooperative.osm')
edit_writer = osmium.SimpleWriter(f'output/{args.name}_tagfix.osm')

for g in gov.all.keys():
    tags_e, location_e = {}, {}
    writer, edit = new_writer, False

    for t, tv in dict(gov.all[g].tags).items():
        if tv:
            tags_e[t] = tv

    tags_e.update(config.tags_to_add)

    if g in mapping['gov'] and len(mapping['gov'].get(g, [])) == 1:
        o = mapping['gov'].get(g)[0]

        for k,v in dict(osm.all[o].tags).items():
            if k in config.tags_to_delete:
                val_to_del = config.tags_to_delete[k]
                if val_to_del == '*' or v == val_to_del:
                    continue
            tags_e.update({k: v})

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
        m = gov.match.get(g)
        if m:
            location_e = m.location
            node = osmium.osm.mutable.Node(
                tags = tags_e,
                location = location_e,
                id = int(gov.all[g].id)
            )
            new_writer.add_node(node)

# with fileinput.FileInput(f'./output/{args.name}_tagfix.osm', inplace=True) as file:
#     for line in file:
#         print(line.replace("<node ", "<node action='modify' "), end='')

subprocess.run(f'mr cooperative change --out ./output/{args.name}_cooperative.geojson ./output/{args.name}_cooperative.osm', shell=True, check=True)
subprocess.run(f'mr cooperative tag --out ./output/{args.name}_tagfix.geojson ./output/{args.name}_tagfix.osm', shell=True, check=True)
