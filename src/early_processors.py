import csv
import importlib.util
import os
import re

import requests
from rich.progress import track


def prepare_gov_data(name, console):
    f_in = open(f'data/{name}/gov.csv', 'r')
    f_out = open(f'data/{name}/gov_clean.csv', 'w')
    config = importlib.import_module(f'data.{name}.conf')

    tags = config.prepare['tags']
    r_in = csv.DictReader(f_in, delimiter=config.prepare.get('separator', ','), quotechar=config.prepare.get('quote', '"'))
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
            elif type(value) is dict:
                if len(value) != 1:
                    raise NotImplementedError(f'Error! Preparation rule: {key, value} not supported!')

                gov_key = list(value.keys())[0]
                gov_val = row.get(gov_key, '').strip()

                print(f'new_row[{key}] = {value.get(gov_key).get(gov_val)} - {value}')
                new_row[key] = value.get(gov_key).get(gov_val, '')
            elif callable(value):
                new_row[key] = (value(row) or '').strip()
            else:
                raise NotImplementedError(f'Error! Preparation rule: {key, value} not supported!')

        r_out.writerow(new_row)


def download_osm_data(name, console):
    overpass_path = f'data/{name}/query.overpass'
    if os.path.isfile(overpass_path):
        query = open(overpass_path, 'r').read()
    elif os.path.isfile(f'{overpass_path}ql'):
        query = open(f'{overpass_path}ql', 'r').read()
    data_out = open(f'data/{name}/data.osm', 'w')

    regex = re.compile(r'(\{\{geocodeArea: *([\w ]+) *\}\})')
    if regex.search(query):
        matches = re.findall(regex, query)
        for repl_elem, name in matches:
            resp = requests.get(f'https://nominatim.openstreetmap.org/search?X-Requested-With=overpass-turbo&format=json&q={name}')
            print(f'https://nominatim.openstreetmap.org/search?X-Requested-With=overpass-turbo&format=json&q={name}')
            try:
                data = resp.json()
            except requests.exceptions.JSONDecodeError:
                print(resp.text)
                raise
            id = data[0].get('osm_id')
            query = query.replace(repl_elem, f'area(id:{3600000000 + int(id)})')

    console.log('Downloading query:')
    print(query)
    resp = requests.post('https://overpass-api.de/api/interpreter', data={'data': query})
    data = resp.text
    data_out.write(data)
