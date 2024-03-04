#!/usr/bin/env python3

import argparse
from rich.console import Console
from src.check_files import check_files
from src.early_processors import prepare_gov_data, download_osm_data
from src.osm_model.reader import read_file
from src.match_and_fill import match
from src.save import save
import subprocess
import shlex


console = Console()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', type=str)
    parser.add_argument('-p', '--prepare', action='store_true', help='Clean and prepare gov data')
    parser.add_argument('-d', '--download', action='store_true', help='Download fresh copy of OSM data')
    args = parser.parse_args()

    check_files(args.name, args.prepare, args.download)

    if args.prepare:
        console.log('Starting preparation step...')
        prepare_gov_data(args.name, console)

    if args.download:
        console.log('Starting download step...')
        download_osm_data(args.name, console)

    console.log('Loading GOV data...')
    gov = read_file(f'data/{args.name  }/gov_clean.csv', 'csv')
    console.log(f'Loaded {len(gov)} elements')

    console.log('Loading OSM data...')
    osm = read_file(f'data/{args.name}/data.osm', 'osm')
    console.log(f'Loaded {len(osm)} elements')

    to_change, to_add = match(gov, osm, args.name)
    console.log(f'To add: {len(to_add)} elements, To update: {len(to_change)} elements.')

    save(f'data/{args.name}/to_add.osm', "\n".join([ta.print() for ta in to_add]))
    save(f'data/{args.name}/to_change.osm', "\n".join([tc.print() for tc in to_change]))

    subprocess.run(shlex.split(f'mr cooperative change --out data/{args.name}/mr_new.geojson data/{args.name}/to_add.osm'))
    subprocess.run(shlex.split(f'mr cooperative tag --out data/{args.name}/mr_tagfix.geojson data/{args.name}/to_change.osm'))


main()
