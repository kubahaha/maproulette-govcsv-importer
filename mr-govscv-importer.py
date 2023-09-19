#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
import importlib.util
import osmium
import requests

from src.utils import strip_number, fieldnames, nominatim_addr, komoot_addr
from src.place_handlers import OsmHandler, GovHandler, ADDR_FIELDS
from src.geodistance import geodistance
from comparators import distance_m, tags_m

def nominatim_to_addr(nominatim):
    return {
        'postcode': nominatim.get('postcode'),
        'city': nominatim.get('city') or nominatim.get('town') or nominatim.get('village'),
        'street': nominatim.get('road'),
        'housenumber': nominatim.get('house_number')
    }

def osm_to_addr(osm):
    return {
        'postcode': osm.get('addr:postcode'),
        'city': osm.get('addr:city') or osm.get('addr:place'),
        'street': (osm.get('addr:street') or osm.get('addr:place')) if osm.get('addr:city') else '',
        'housenumber': osm.get('addr:housenumber')
    }

def match_addr(addr1, addr2, mapping, skpinumber=False):
    match_all = ['postcode', 'city', 'place', 'street', 'housenumber']

    if skpinumber:
        match_all.remove('housenumber')

    tmp = False
    for key in match_all:
        a_k, b_k = addr1.get(f'addr:{key}'), addr2.get(f'addr:{key}')
        
        if (not a_k and b_k) or (a_k and not b_k):
            return False
        
        if a_k == b_k:
            tmp = True

        if not tmp:
            return False

    return tmp
    # return all([addr1[f'addr:{m}'] == addr2[f'addr:{m}'] for m in match_all])

def match_latlon(latlon1, latlon2, limit=100):
    if geodistance(latlon1.lat, latlon1.lon, latlon2.lat, latlon2.lon) > limit:
        return False
    return True

def geocenter(latlons):
    x = sum([it.lat for it in latlons])
    y = sum([it.on for it in latlons])
    return (x, y)

parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
parser.add_argument('-p', '--prepare', action='store_true')
# parser.add_argument('-g', '--geocode', choices=['nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-r', '--reverse-geocode', choices=['komoot', 'nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-i', '--input-file', type=str.lower)
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

new_writer = osmium.SimpleWriter(f'output/{args.name}_new.osm')
edit_writer = osmium.SimpleWriter(f'output/{args.name}_edit.osm')

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
    



for k, v in osm.all2:
    print(osm.all)
print(osm.match)

for g, o in mapping['gov'].items():
    if len(o) != 1:
        continue
    o = o[0]
    # loc = {'x': float(osm.all.get(o).get('lat')), 'y': float(osm.all.get(o).get('lon'))}
    if o in osm.filled:
        loc = (float(osm.all.get(o).get('lon')), float(osm.all.get(o).get('lat')))
    elif o in osm.match:
        loc = (float(osm.match.get(o).get('lon')), float(osm.match.get(o).get('lat')))
    else:
        raise NotImplementedError
    
    item = {}
    
    
    item['heritage'] = '7'
    


project_name = config.static["project_name"]
clear_fieldnames = config.fieldnames_after_mod + fieldnames['addr'] + fieldnames['tech']

osmfile = open(f'./input/{project_name}_osm.csv')
outfile = open(f'./tmp/{project_name}_osm_modified.csv', 'w')
errfile = open(f'./tmp/{project_name}_osm_errors_{args.mode}.csv', 'w')
osmreader = csv.DictReader(osmfile, delimiter='|')
outwriter = csv.DictWriter(outfile, fieldnames=clear_fieldnames, delimiter='|')
errwriter = csv.DictWriter(errfile, fieldnames=osmreader.fieldnames, delimiter='|')
outwriter.writeheader()

row_count = sum(1 for row in osmreader)
osmfile.seek(0)
osmreader = csv.DictReader(osmfile, delimiter='|')

stats = defaultdict(int)
stats['total'] = row_count

for row in osmreader:
    if not (row.get('addr:city') or row.get('addr:place')) or not row.get('addr:housenumber'):
        newrow = {}
        if args.mode == 'nominatim':
            response = requests.get(f'https://nominatim.openstreetmap.org/reverse.php?lat={row["@lat"]}&lon={row["@lon"]}&zoom=18&format=jsonv2').json()
            newrow = nominatim_addr(response)
        elif args.mode == 'komoot':
            response = requests.get(f'https://photon.komoot.io/reverse?lon={row["@lon"]}&lat={row["@lat"]}').json()
            newrow = komoot_addr(response)

        if (newrow.get('addr:city') or newrow.get('addr:place')) and newrow.get('addr:housenumber'):
            stats['filled'] += 1
        else:
            print()
            if args.mode == 'nominatim':
                print(f'missing!  https://nominatim.openstreetmap.org/ui/reverse.html?lat={row["@lat"]}&lon={row["@lon"]}&zoom=18&format=jsonv2')
            elif args.mode == 'komoot':
                print(f'missing!  https://photon.komoot.io/reverse?lat={row["@lat"]}&lon={row["@lon"]}  https://osm.org/#map=19/{row["@lat"][0:7]}/{row["@lon"][0:7]}')
            
            errwriter.writerow(row)
            stats['missing'] += 1
        row.update(newrow)
    else:
        stats['found'] += 1

    outrow = {k: (row.get(k) or '').strip() for k in clear_fieldnames}
    outrow['@id'] = f'{row["@type"]}/{row["@id"]}'

    outwriter.writerow(outrow)
    print(f"Total: {stats['found'] + stats['filled'] + stats['missing']}/{stats['total']} {100*(stats['found'] + stats['filled'] + stats['missing'])/stats['total']:.0f}% | found: {stats['found']} {100*stats['found']/(stats['found'] + stats['filled'] + stats['missing']):.0f}% | filled: {stats['filled']} {100*stats['filled']/(stats['found'] + stats['filled'] + stats['missing']):.0f}% | missing: {stats['missing']} {100*stats['missing']/(stats['found'] + stats['filled'] + stats['missing']):.0f}%")