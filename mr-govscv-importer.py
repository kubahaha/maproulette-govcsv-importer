#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
import importlib.util
import osmium
import requests

from src.utils import strip_number, fieldnames, nominatim_addr, komoot_addr

NOMINATIM_SERVER = 'https://nominatim.openstreetmap.org'


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

def _haveaddr(tags):
    if not all(x in tags for x in ['addr:postcode', 'addr:housenumber']):
        return False
    else:
        if all(x in tags for x in ['addr:city', 'addr:street']):
            return True
        if 'addr:place' in tags:
            return True
        return False

class OsmHandler(osmium.SimpleHandler):
    def __init__(self, name):
        super(OsmHandler, self).__init__()
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.match = {}
        self.nomatch = []
        self.filled = []
        self.all = {}


    def node(self, n):
        self.all.update({f'N{n.id}': {
            'id': n.id,
            'version': n.version,
            'tags': {k:v for k,v in n.tags},
            'location': n.location
        }})
        if _haveaddr(n.tags):
            self.filled.append(f'N{n.id}')
        else:
            self.nomatch.append(f'N{n.id}')

    def way(self, w):
        self.all.update({f'W{w.id}': {
            'id': w.id,
            'version': w.version,
            'tags': {k:v for k,v in w.tags},
            'nodes': [{'x': node.x, 'y': node.y} for node in w.nodes]
        }})

        if _haveaddr(w.tags):
            self.filled.append(f'W{w.id}')
        else:
            self.nomatch.append(f'W{w.id}')

class GovHandler():
    def __init__(self, name):
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.all = {}
        self.match = {}
        self.nomatch = []

    def import_csv(self, filename):
        f = open(filename, 'r')
        r = csv.DictReader(f)
        for row in r:
            self.all.append(row)


parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
# parser.add_argument('-g', '--geocode', choices=['nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-r', '--reverse-geocode', choices=['komoot', 'nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-i', '--input-file', type=str.lower)
args = parser.parse_args()

# add addresses to osm
osm = OsmHandler(args.name)
osm.apply_file(f'input/{args.name}.osm')
batches = [osm.nomatch[i:i+50] for i in range(0, len(osm.nomatch), 50)]

for b in batches:
    url = f'{NOMINATIM_SERVER}/lookup?osm_ids={",".join(b)}&format=json'
    print(f'Downloading: {url}')
    res = requests.get(url).json()
    for it in res:
        key = f'{it.get("osm_type")[0].upper()}{it.get("osm_id")}'
        osm.match[key] = it.get('address')
        osm.nomatch.remove(key)

total = len(osm.match) + len(osm.nomatch) + len(osm.filled)
print(f'{total} items in total, {len(osm.filled)} filled. {len(osm.match)} updated, {len(osm.nomatch)} not matched')

# add cords to gov
gov = GovHandler(args.name)
gov.import_csv(f'input/{args.name}_gov.csv')


for k,v in gov.items():
    addr = '&'.join([f'{k}={v(it)}' for k,v in gov.config.search.items()])
    url = f'{NOMINATIM_SERVER}/search?{addr}&addressdetails=1&format=json'
    # print(url)
    res = requests.get(url).json()
    if res:
        gov.match.update({k: res[0]})
    else:
        print(f'Downloading {url} failed - not found!')
        gov.nomatch.append(k)
        

total = len(gov.match) + len(gov.nomatch)
print(f'{total} items in total. {len(gov.match)} updated, {len(gov.nomatch)} not matched')

# match
mapping = {
    'osm': defaultdict(list),
    'gov': defaultdict(list)
}

# by addr
for g in gov.match:
    print(g)
    addr_g = nominatim_to_addr(g.get('nominatim').get('address'))
    for o in osm.filled:
        addr_o = osm_to_addr(osm.all.get(o).get('tags'))
        match_all = ['postcode', 'city', 'street', 'housenumber']
        if all([addr_o[m] == addr_g[m] for m in match_all]):
            mapping['osm'].append('gov')



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