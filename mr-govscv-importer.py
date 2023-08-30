#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
import osmium
import requests

from src.utils import strip_number, fieldnames, nominatim_addr, komoot_addr
from src.place_handlers import OsmHandler, GovHandler
from src.geodistance import geodistance

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
    match_all = ['postcode', 'city', 'street', 'housenumber']

    if skpinumber:
        match_all.remove('housenumber')

    return all([addr1[m] == addr2[m] for m in match_all])

def match_latlon(latlon1, latlon2, limit=100):
    if geodistance(latlon1[0], latlon1[1], latlon2[0], latlon2[1]) > limit:
        return False
    return True

def geocenter(latlons):
    x = sum([it.lat for it in latlons])
    y = sum([it.on for it in latlons])
    return (x, y)

parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
# parser.add_argument('-g', '--geocode', choices=['nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-r', '--reverse-geocode', choices=['komoot', 'nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-i', '--input-file', type=str.lower)
args = parser.parse_args()

# add addresses to osm
osm = OsmHandler(args.name)
osm.apply_file(f'input/{args.name}.osm')
osm.add_addresses()

# add cords to gov
gov = GovHandler(args.name)
gov.import_csv(f'input/{args.name}_gov.csv')
gov.add_cords()

# match
mapping = {
    'osm': defaultdict(list),
    'gov': defaultdict(list)
}

# by addr
for g in gov.match:
    addr_g = nominatim_to_addr(gov.match.get(g).get('address'))
    for o in osm.filled:
        addr_o = osm_to_addr(osm.all.get(o).get('tags'))
        if match_addr(addr_g, addr_o, mapping):
            mapping['osm'][o].append(g)
            mapping['gov'][g].append(o)
    for o in osm.match:
        addr_o = nominatim_to_addr(osm.match.get(o).get('address'))
        if match_addr(addr_g, addr_o, mapping):
            mapping['osm'][o].append(g)
            mapping['gov'][g].append(o)

#by cords
for g in gov.match:
    if g in mapping['gov']:
        continue
    latlon_g = (gov.match.get(g).get('lat'), gov.match.get(g).get('lon'))
    for id,o in osm.all.items():
        latlon_o = ''
        if id in mapping['osm']:
            continue

        if o.get('location'):
            latlon_o = (o['location'].lat, o['location'].lon)
        elif id in osm.match:
            latlon_o = (osm.match.get(id).get('lat'), osm.match.get(id).get('lon'))
        else:
            continue

        if match_latlon(latlon_g, latlon_o):
            mapping['osm'][id].append(g)
            mapping['gov'][g].append(id)

for k, v in mapping['gov'].items():
    if(len(v) > 0):
        print(f'GOV: {gov.all.get(k)}')
        for it in v:
            print(osm.all.get(it))

writer = osmium.SimpleWriter('result.osm')

# for k, v in osm.all2:
#     print(osm.all)
# print(osm.match)

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
    node = osmium.osm.mutable.Node(tags=item, location=loc, id=g[1:])
    writer.add_node(node)



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