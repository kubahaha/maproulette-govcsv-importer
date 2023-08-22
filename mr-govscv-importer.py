#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
import importlib.util
import osmium
import requests

from src.utils import strip_number, fieldnames, nominatim_addr, komoot_addr


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


    def node(self, n):
        if _haveaddr(n.tags):
            self.filled.append(f'N{n.id}')
        else:
            self.nomatch.append(f'N{n.id}')

    def area(self, a):
        if not _haveaddr(a.tags):
            self.filled.append(f'W{a.id}')
        else:
            self.nomatch.append(f'W{a.id}')

class GovHandler():
    def __init__(self, name):
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.match = []
        self.nomatch = []

    def import_csv(self, filename):
        f = open(filename, 'r')
        r = csv.DictReader(f)
        for row in r:
            self.nomatch.append(row)


parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
parser.add_argument('-g', '--geocode', choices=['nominatim'], default='nominatim', type=str.lower)
parser.add_argument('-r', '--reverse-geocode', choices=['komoot', 'nominatim'], default='nominatim', type=str.lower)
# parser.add_argument('-i', '--input-file', type=str.lower)
args = parser.parse_args()

# places = PlacesList(args.name)
osm = OsmHandler(args.name)
osm.apply_file(f'input/{args.name}.osm')
batches = [osm.nomatch[i:i+50] for i in range(0, len(osm.nomatch), 50)]

for b in batches:
    print(f'Downloading: https://nominatim.openstreetmap.org/lookup?osm_ids={",".join(b)}&format=json')
    res = requests.get(f'https://nominatim.openstreetmap.org/lookup?osm_ids={",".join(b)}&format=json').json()
    for it in res:
        key = f'{it.get("osm_type")[0].upper()}{it.get("osm_id")}'
        osm.match[key] = it.get('address')
        osm.nomatch.remove(key)

total = len(osm.match) + len(osm.nomatch) + len(osm.filled)
print(f'{total} items in total, {len(osm.filled)} filled. {len(osm.match)} updated, {len(osm.nomatch)} not matched')

gov = GovHandler(args.name)
gov.import_csv(f'input/{args.name}_gov.csv')

for it in gov.nomatch:
    url = f'https://nominatim.openstreetmap.org/search?street={gov.config.search.get("street")(it)}&city={gov.config.search.get("city")(it)}&country={gov.config.search.get("country")(it)}&postalcode={gov.config.search.get("postalcode")(it)}&format=json'
    print(f'Downloading {url}')
    res = requests.get(url).json()
    gov.match.append({
        'org': it,
        'nominatim': res
    })
    gov.nomatch.remove(it)

total = len(gov.match) + len(gov.nomatch)
print(f'{total} items in total. {len(gov.match)} updated, {len(gov.nomatch)} not matched')





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