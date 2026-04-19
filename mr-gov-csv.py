#!/usr/bin/env python3

import argparse
import subprocess
import shlex

from rich.console import Console

from src.engines.komoot import Komoot
from src.engines.nominatim import Nominatim
from src.check_files import check_files
from src.early_processors import prepare_gov_data, download_osm_data
from src.fill.fill_csv import check_addresses, fill_lat_lon_for_unmatched, fill_with_matches
from src.osm_model.reader import read_file
from src.match.match_and_fill import match, add_new
from src.save import save
from src.workspace_manager import prepare_workspace

console = Console()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', type=str)
    parser.add_argument('-p', '--prepare', action='store_true', help='Clean and prepare gov data')
    parser.add_argument('-d', '--download', action='store_true', help='Download fresh copy of OSM data')
    parser.add_argument('-e', '--engine', choices=['nominatim', 'komoot'], default='nominatim', help='Engine for downloading addressess and lat_lon')

    args = parser.parse_args()

    check_files(args.name, args.prepare, args.download)

    engine = {
        'nominatim': Nominatim(),
        # 'komoot': Komoot()
    }.get(args.engine)

    if args.prepare:
        console.log('Starting preparation step...')
        prepare_gov_data(args.name, console)

    if args.download:
        console.log('Starting download step...')
        download_osm_data(console, args.name, engine)

    console.log('Creating copy of files for matching...')
    prepare_workspace(args.name)

    console.log('Matching gov to osm...')
    match(args.name, engine, console, names=True, addr=True, tags=True)

    console.log('Downloading location for unmatched gov data...')
    fill_lat_lon_for_unmatched(args.name, console, engine)

    console.log('Matching gov to osm by location...')
    match(args.name, engine, console, location=True)

    console.log('Preparing list of matched POIs where addr should be updated...')
    addresses_needed = check_addresses(args.name, engine, console)

    console.log('Saving matched POIs...')
    to_change = fill_with_matches(args.name, console, addresses_needed)
    save(f'data/{args.name}/to_change.osm', "\n".join([tc.print() for tc in to_change]))

    console.log('Saving unmatched POIs')
    to_add = add_new(console, args.name)
    save(f'data/{args.name}/to_add.osm', "\n".join([ta.print() for ta in to_add]))

    console.log('Generating MapRoulette tasks...')
    subprocess.run(shlex.split(f'mr cooperative change --out data/{args.name}/mr_new.geojson data/{args.name}/to_add.osm'), check=True)
    subprocess.run(shlex.split(f'mr cooperative tag --out data/{args.name}/mr_tagfix.geojson data/{args.name}/to_change.osm'), check=True)

    console.log('Successfully finished all steps!')

main()
