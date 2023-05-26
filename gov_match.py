#!/usr/bin/env python3
import argparse
import csv
import requests
import itertools
from collections import defaultdict
import re
import random
import importlib.util

# from comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, fieldnames, nominatim_addr

NOMINATIM_URL='https://nominatim.openstreetmap.org'
# NOMINATIM_URL='https://osm-nominatim.gs.mil'

def compare(gov, osm, fields):
    def iterate_help(name):
        field = list(filter(lambda it: it.name == name, fields))[0]

        if not gov.get(field.left) or not osm.get(field.right):
            return False

        return field.left_strip(gov[field.left]) == field.right_strip(osm[field.right])
    comparision = []
    for comp in fields:
        if comp.single_match:
            comparision.append(comp.name)
    
    comparision += ['addr:city-addr:housenumber-addr:street', 'addr:housenumber-addr:place']
    comparision += ['addr:housenumber-addr:place-addr:postcode', 'addr:street-addr:housenumber-addr:postcode']

    results = defaultdict(int)
    results_values = {}
    for op in comparision:
        if(all(map(iterate_help, op.split('-')))):
            results[op] += 1
            results_values.update({op: (gov, osm)})

    return (results, results_values)

parser = argparse.ArgumentParser()
parser.add_argument('name', type=str)
parser.add_argument('-m', '--mode', choices=['komoot', 'nominatim'], default='nominatim', type=str.lower)
args = parser.parse_args()

print(f'Importing conf.{args.name}_conf')
config = importlib.import_module(f'conf.{args.name}_conf')
project_name = config.static['project_name']

# govfile = open(f'./input/tmp.csv')
govfile = open(f'./input/{project_name}_gov.csv')
osmfile = open(f'./tmp/{project_name}_osm_modified.csv')
clearfile = open(f'./tmp/{project_name}_gov_paired.csv', 'w', newline='')
errfile = open(f'./tmp/{project_name}_gov_errors_{args.mode}.csv', 'w')

govreader = csv.DictReader(govfile, delimiter=',')
osmreader = csv.DictReader(osmfile, delimiter='|')
fieldnames_clear = govreader.fieldnames + fieldnames['tech']
paired = csv.DictWriter(clearfile, fieldnames=fieldnames_clear, delimiter='|')
errwriter = csv.DictWriter(errfile, fieldnames=govreader.fieldnames, delimiter='|')

paired.writeheader()

used_osm = []
stats = defaultdict(int)
stats['total'] = sum(1 for row in govreader)

govfile.seek(0)
govreader = csv.DictReader(govfile, delimiter=',')
reverse_keys = {k.right: k.left for k in config.comparision.values()}

for office in govreader:
    counter = defaultdict(int)
    counter_values = {}
    osmfile.seek(0)

    for row in osmreader:
        results, results_values = compare(office, row, config.comparision.values())
        for key in results.keys():
            counter[key] += results[key]
            counter_values.update(results_values)

    is_match = False

    for (k, v) in counter.items():
        if is_match:
            break
        if v == 1:
            gov, osm = counter_values[k]
            if osm['@id'] in used_osm:
                continue
            
            stats['paired'] +=1

            row = {}
            for k in fieldnames['addr']:
                if k in config.comparision.keys():
                    printed = config.comparision[k].left_print(office[reverse_keys[k]])
                    if printed:
                        row.update({k: printed.capitalize()})

            for k in fieldnames_clear:
                if k in govreader.fieldnames:
                    row[k] = office.get(k, '')
                elif k in fieldnames['tech']:
                    row[k] = osm.get(k, '')

            paired.writerow(row)
            used_osm.append(osm['@id'])
            is_match = True

    if not is_match:
        newrow = {}
        for comp in config.comparision.values():
            if office.get(comp.left):
                newrow[comp.right] = comp.left_print(office[comp.left])

        newaddr = {}
        cords = {}
        if args.mode == 'nominatim':             
            print(newrow)
            street = newrow.get('addr:street'),
            number = newrow.get('addr:housenumber'),
            city = newrow.get('addr:city'),
            place = newrow.get('addr:place'),
            postcode = newrow.get('addr:postcode')

            response = requests.get(f"{NOMINATIM_URL}/search.php?street={street or place} {number}&city={city or place}&country=Polska&format=jsonv2").json()
            
            responce_dict = next(iter(response), None)
            if not responce_dict:
                stats['missing'] += 1
                errwriter.writerow(office)
                print()
                print(f"Nominatim failed! {NOMINATIM_URL}/search.php?street={street or place} {number}&city={city or place}&country=Polska&format=jsonv2")
                print(f"total: {stats['paired'] + stats['missing'] + stats['to_add']}/{stats['total']} {100*(stats['paired'] + stats['missing'] + stats['to_add'])/stats['total']:.0f}% - paired: {stats['paired']}/{(stats['paired'] + stats['missing'] + stats['to_add'])} {100*stats['paired']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - missing: {stats['missing']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['missing']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - to_add: {stats['to_add']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['to_add']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}%")
                continue
            
            response = requests.get(f"{NOMINATIM_URL}/details.php?osmtype={responce_dict['osm_type'][0].upper()}&osmid={responce_dict['osm_id']}&addressdetails=1&format=json").json()
            # print(f"{NOMINATIM_URL}/details.php?osmtype={responce_dict['osm_type'][0].upper()}&osmid={responce_dict['osm_id']}&addressdetails=1&format=json")
            newaddr = response['addresstags']
            cords['@lon'], cords['@lat'] = response['geometry']['coordinates']
            stats['to_add'] += 1
        elif args.mode == 'komoot':
            response = requests.get(f"https://photon.komoot.io/api/?q={office[reverse_keys['addr:city']] or office[reverse_keys['addr:place']]}, {office[reverse_keys['addr:street']] or office[reverse_keys['addr:place']]} {office[reverse_keys['addr:housenumber']]}").json()
            # print(f"https://photon.komoot.io/api/?q={office[reverse_keys['addr:city']] or office[reverse_keys['addr:place']]}, {office[reverse_keys['addr:street']] or office[reverse_keys['addr:place']]} {office[reverse_keys['addr:housenumber']]}")
            if not response['features']:
                stats['missing'] += 1
                errwriter.writerow(office)
                print()
                print(f"Komoot failed! https://photon.komoot.io/api/?q={office[reverse_keys['addr:street']] or office[reverse_keys['addr:place']]} {office[reverse_keys['addr:housenumber']]} {office[reverse_keys['addr:city']] or office[reverse_keys['addr:place']]} {office[reverse_keys['addr:postcode']]}")
                print(f"total: {stats['paired'] + stats['missing'] + stats['to_add']}/{stats['total']} {100*(stats['paired'] + stats['missing'] + stats['to_add'])/stats['total']:.0f}% - paired: {stats['paired']}/{(stats['paired'] + stats['missing'] + stats['to_add'])} {100*stats['paired']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - missing: {stats['missing']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['missing']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - to_add: {stats['to_add']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['to_add']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}%")
                continue

            prefix = response['features'][0]['properties']
            newaddr = {f'addr:{k}': v for k,v in prefix.items() if f'addr:k' in fieldnames['addr']}
            cords['@lon'], cords['@lat'] = response['features'][0]['geometry']['coordinates']
            stats['to_add'] += 1
            pass
        
        newrow.update(newaddr)
        newrow.update(cords)

        row = {}
        for k in fieldnames_clear:
            if office.get(k):
                row[k] = office[k]
            if newrow.get(k):
                row[k] = newrow.get(k, '')

        paired.writerow(row)
        is_match = False
    print(f"total: {stats['paired'] + stats['missing'] + stats['to_add']}/{stats['total']} {100*(stats['paired'] + stats['missing'] + stats['to_add'])/stats['total']:.0f}% - paired: {stats['paired']}/{(stats['paired'] + stats['missing'] + stats['to_add'])} {100*stats['paired']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - missing: {stats['missing']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['missing']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}% - to_add: {stats['to_add']}/{stats['paired'] + stats['missing'] + stats['to_add']} {100*stats['to_add']/(stats['paired'] + stats['missing'] + stats['to_add']):.0f}%")
