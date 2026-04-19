from typing import List
import csv
import os
from rich.console import Console

from src.engines.abstract_engine import AbstractEngine
from src.osm_model.osm_types import OsmObject
from src.osm_model.reader import read_file
from src.match.match_file import read_matches
from src.match.match_and_fill import fill


def fill_lat_lon_for_unmatched(name: str, console: Console, engine: AbstractEngine):
    locations_file = f'data/{name}/locations.csv'
    
    if os.path.exists(locations_file):
        console.log(f"Skipping downloading locations - {locations_file} already exists")
        return
    
    matches = read_matches(name)
    gov = read_file(f'data/{name}/gov_clean.csv', console, 'csv')

    unmatched_gov = [poi for poi in gov if poi.id not in matches]
    console.log(f"Found {len(unmatched_gov)} unmatched POIs.")

    coords = {}
    for poi in unmatched_gov:
        if not poi.has_loc():
            coords[poi.id] = poi.download_lat_lon(engine=engine)

    if coords:
        valid_coords = {pid: (lat, lon) for pid, (lat, lon) in coords.items() if lat and lon}
        if valid_coords:
            with open(locations_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['__id', '__lat', '__lon'])
                writer.writeheader()
                for poi_id, (lat, lon) in valid_coords.items():
                    writer.writerow({'__id': poi_id, '__lat': lat, '__lon': lon})
            console.log(f"Saved {len(valid_coords)} coordinates to {locations_file}")
        else:
            console.log("No valid coordinates to save")

def check_addresses(name: str, engine: AbstractEngine, console: Console):
    matches = read_matches(name)
    osm = read_file(f'data/{name}/data.osm', console, 'osm')

    matched_ids = [osmobject.get_uid() for osmobject in osm if osmobject.id in matches.values() and not osmobject.get_tag('addr:housenumber')]
    addresses = engine.query_elements(matched_ids)

    needed_ids = []
    for oid, addr in addresses.items():
        if 'addr:housenumber' not in addr:
            console.log(f"Address needed for OSM object ID {oid}")
            needed_ids.append(oid)
    return needed_ids

def fill_with_matches(name: str, console: Console, addresses_needed: list[str]) -> List[OsmObject]:
    matches = read_matches(name)
    gov = read_file(f'data/{name}/gov_clean.csv', console, 'csv')
    osm = read_file(f'data/{name}/data.osm', console, 'osm')

    output = []
    for gov_id, osm_id in matches.items():
        # print(gov_id, [g.id for g in gov])
        gov_object = next(g for g in gov if g.id == gov_id)
        osm_object = next(o for o in osm if o.id == osm_id)

        filled_object = fill(name, osm_object, gov_object, update_addr=osm_object.id in addresses_needed)
        output.append(filled_object)

    return output
