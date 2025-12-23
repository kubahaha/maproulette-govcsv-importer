import csv
import importlib
import os
import re

import requests
from rich.progress import track
from rich.console import Console

from src.engines.abstract_engine import AbstractEngine

def prepare_gov_data(name: str, console: Console):
    with open(f'data/{name}/gov.csv', 'r', encoding='utf-8') as f_in, \
         open(f'data/{name}/gov_clean.csv', 'w', encoding='utf-8') as f_out:
        config = importlib.import_module(f'data.{name}.conf')

        tags = config.prepare['tags']
        r_in = csv.DictReader(f_in, delimiter=config.prepare.get('separator', ','), quotechar=config.prepare.get('quote', '"'))
        r_out = csv.DictWriter(f_out, fieldnames=tags.keys())
        r_out.writeheader()

        for row in track(r_in, description='Preparing gov data'):
            with console.status("Preparation starting") as status:
                status.update(f'Processing {row}')

            if config.prepare.get('accept', lambda x: False)(row):
                continue
            new_row = {}
            for key, value in tags.items():
                new_row[key] = _prepare_row(value, row)

            r_out.writerow(new_row)


def _prepare_row(value, row):
    if isinstance(value, str):
        return row.get(value, '').strip()
    if isinstance(value, dict):
        if len(value) != 1:
            raise NotImplementedError(f'Error! Preparation rule: {value} not supported!')

        gov_key = list(value.keys())[0]
        gov_val = row.get(gov_key, '').strip()

        return value.get(gov_key).get(gov_val, '')
    if callable(value):
        return (value(row) or '').strip()

    raise NotImplementedError(f'Error! Preparation rule: {value} not supported!')


def download_osm_data(console, name, engine: AbstractEngine) -> None:
    overpass_path = f'data/{name}/query.overpass'
    if os.path.isfile(overpass_path):
        with open(overpass_path, 'r', encoding="utf-8") as fd:
            query = fd.read()
    elif os.path.isfile(f'{overpass_path}ql'):
        with open(f"{overpass_path}ql", 'r', encoding="utf-8") as fd:
            query = fd.read()
    else:
        raise FileNotFoundError(f"File {overpass_path} not found!")

    geocode_regex = re.compile(r'(\{\{geocodeArea: *([\w ]+) *\}\})')
    if geocode_regex.search(query):
        matches = re.findall(geocode_regex, query)
        for repl_elem, geocode_name in matches:
            osm_id = engine.query(geocode_name).get('osm_id')
            query = query.replace(repl_elem, f'area(id:{3600000000 + int(osm_id)})')

    timeout_regex = re.compile(r'\[timeout:(\d+)\]')
    timeout = int(timeout_regex.search(query).group(1)) if timeout_regex.search(query) else 90

    console.log(f'Downloading query:\n{query}')
    resp = requests.post('https://overpass-api.de/api/interpreter', data={'data': query}, timeout=timeout+10)
    data = resp.text
    console.log(f'Download complete ({len(data)} bytes), saving data...')

    with open(f'data/{name}/data.osm', 'w', encoding="utf-8") as data_out:
        data_out.write(data)
