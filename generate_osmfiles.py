#!/usr/bin/env python3
import argparse
import csv
import requests
import itertools
from collections import defaultdict
import re
import sys
from math import sin, cos, sqrt, atan2, radians
from src.utils import getaddr, getopening, strip_number, getoperator, fieldnames
import random
import importlib.util

parser = argparse.ArgumentParser()
parser.add_argument('--distance', '-d', type=int, default=200)
parser.add_argument('name', type=str)
args = parser.parse_args()

print(f'Importing conf.{args.name}_conf')
config = importlib.import_module(f'conf.{args.name}_conf')
project_name = config.static['project_name']

# from config import static, comparision, fieldnames, tags_to_add, tags_to_delete, gov_fieldnames, tags_to_generate, tags_to_cond_delete

govfile = open(f'./tmp/{project_name}_gov_paired.csv')
osmfile = open(f'./tmp/{project_name}_osm_modified.csv')
dmpfile = open(f'./input/{project_name}.osm')

govreader = csv.DictReader(govfile, delimiter='|')
osmreader = csv.DictReader(osmfile, delimiter='|')

tagfix = open(f'output/{project_name}_tagfix.osm', 'w')
cooperative = open(f'output/{project_name}_cooperative.osm', 'w')

def line_type(line):
    tag_m = re.compile(r'<tag k="(.+)" v="(.+)"').search(line)
    start_m = re.compile(r'<(way|node|relation).* id="(\d+)"').search(line)
    end_m = re.compile(r'<\/(way|node|relation)').search(line)
    noderef_m = re.compile(r'(<nd|<member)').search(line)
    fileend_m = re.compile(r'<\/osm>').search(line)
    if tag_m:
        return ('tag', (tag_m[1], tag_m[2])) # <tag k="source" v="gis.um.szczecin.pl"/>
    elif start_m:
        return ('obj_start', f"{start_m[1]}/{start_m[2]}") # <way id="66860843" version="7" timestamp="2019-01-15T15:12:23Z" changeset="66334733" uid="4382212" user="Damian96">
    elif end_m:
        return ('obj_end', False) # </way>
    elif noderef_m:
        return ('node_ref', False) # <nd ref="807896460"/>
    elif fileend_m:
        return ('end', False) # </osm>
    if len(line) > 1:
        raise Exception(f"NO match: {line}")
    return ('empty', False)

def osm_to_dict(osm):
    res = {}
    for line in osm:
        res.update(line)
    return res

for _ in range(4):
    buf = dmpfile.readline()
    tagfix.write(buf)
    cooperative.write(buf)

fixme_ids = set()
add_ids = set()

gendict = {}
reverse_keys = {k.right: k.left for k in config.comparision.values()}

for row in govreader:
    current_id = row.get('@id') or 0 - int(random.random() * 1000000000)
    place_not_street, place_not_city = False, False
    genrow = {}
    
    place_not_street = (row.get(reverse_keys['addr:street']) or '').lower().find('osiedle') > -1
    place_not_city = not row.get(reverse_keys['addr:street'])
    # addr = {
    #     'postcode': row.get('KOD POCZTOWY'),
    #     'street': row.get('ULICA') if not place_not_street else '',
    #     'housenumber': row.get('NRDOMU'),
    #     'city': row.get('MIEJSCOWOŚĆ'),
    #     'place': row.get('ULICA') if place_not_street else row.get('MIEJSCOWOŚĆ') if place_not_city else ''
    # }
    for k in fieldnames['tech']:
        genrow.update({k: row[k]})

    for k,v in config.comparision.items():
        govkey, osmkey, transform_fun = v.left, v.right, v.print
        tmp = transform_fun(row[govkey])
        if tmp:
            genrow[osmkey] = tmp

    if place_not_city:
        genrow['addr:place'] = genrow.get('addr:city')
        del genrow['addr:city']
    if place_not_street:
        genrow['addr:place'] = genrow.get('addr:street')
        del genrow['addr:street']
    if genrow.get('addr:place') == genrow.get('addr:city'):
        del genrow['addr:place']

    for k, v in config.tags_to_add.items():
        genrow[k] = v
        
    for k, values in config.tags_to_generate.items():
        if type(values) == type({}):
            for v, check_fun in values.items():
                if check_fun(row):
                    genrow[k] = v
        elif type(values) == type(lambda x: x):
            genrow[k] = values(row)
        
    gendict[current_id] = genrow

# print(gendict.keys())
current=False
current_id=''
writer = False
for line in dmpfile:
    # print(line_type(line))
    label, val = line_type(line)
    
    if label == 'tag':
        k, v = val
        if current != 'modify':
            continue
        if k in config.tags_to_delete:
            continue
        if k in gendict[current_id].keys():
            continue
        tagfix.write(line)

    elif label == 'obj_start':
        if val not in gendict.keys():
            continue
        
        current = 'modify'
        current_id = val
        new_line = line.replace('version', f'action="{current}" version')
        tagfix.write(new_line)

        for k, v in gendict[current_id].items():
            if k in fieldnames['tech'] or k in fieldnames['addr']:
                continue
            is_cond_deleted = False
            tmp = config.tags_to_cond_delete.get(k)
            if tmp:
                if not tmp(gendict[current_id]):
                    is_cond_deleted = True
            if not v or k in config.tags_to_delete:
                continue
            if is_cond_deleted:
                continue
        
            tagfix.write(f'    <tag k="{k}" v="{v}" />\n')

    elif label == 'obj_end':
        if current == 'modify':
            tagfix.write(line)
        current_id = ''
        current = False
    
    elif label == 'node_ref':
        if current == 'modify':
            tagfix.write(line)
    
    elif label == 'end':
        tagfix.write(line)

for osmid, osmtags in gendict.items():
    if type(osmid) != type(-1):
        continue

    cooperative.write(f'  <node id="{osmid}" lat="{osmtags["@lat"]}" lon="{osmtags["@lon"]}" action="modify" visible="true">\n')
    for k, v in osmtags.items():
        if k in fieldnames['tech']:
            continue
        is_cond_deleted = False
        tmp = config.tags_to_cond_delete.get(k)
        if tmp:
            if not tmp(osmtags):
                is_cond_deleted = True
        if not v or k in config.tags_to_delete:
            continue
        if is_cond_deleted:
            continue
        
        cooperative.write(f'    <tag k="{k}" v="{v}" />\n')
    cooperative.write(f'  </node>\n')
cooperative.write(f'</osm>\n')    
        