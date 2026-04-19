import importlib.util
import copy
import csv
import os

from rich.console import Console
from rich.progress import Progress, track

from src.osm_model.reader import read_file
from src.match.matchers import AbstractMatcher, LocationMatcher, TagsListMatcher, NamesMatcher, AddressMatcher
from src.utils import FIELDS, WORKDIR
from src.osm_model.osm_types import OsmObject
from src.match.match_file import read_matches, save_matches


def add_new(console: Console, name: str) -> list[OsmObject]:
    gov: list[OsmObject] = read_file(f'data/{name}/gov_clean.csv', console, 'csv')
    tags_source = importlib.import_module(f'data.{name}.conf').tags_source

    # Load locations from locations.csv if available
    locations = {}
    locations_file = f'data/{name}/locations.csv'
    if os.path.exists(locations_file):
        with open(locations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    poi_id = int(row.get('__id'))
                    lat_str = row.get('__lat', '').strip()
                    lon_str = row.get('__lon', '').strip()
                    if lat_str and lon_str and lat_str != 'False' and lon_str != 'False':
                        lat = float(lat_str)
                        lon = float(lon_str)
                        locations[poi_id] = (lat, lon)
                except (ValueError, TypeError):
                    continue
        console.log(f"Loaded {len(locations)} coordinates from locations.csv")

    to_add = []
    for govitem in gov:
        if not govitem.is_found():
            govitem.modify = True
            ready = copy.deepcopy(govitem)

            # Update coordinates from locations.csv if available
            if ready.id in locations:
                lat, lon = locations[ready.id]
                ready._lat = lat
                ready._lon = lon

            ready_tags = delete_add_tags_conf(ready.tags, name)
            ready_tags = replace_tags_conf(ready_tags, name)

            ready_tags.update(tags_source)
            ready.tags = ready_tags

            to_add.append(ready)
    return to_add

def _find_matches(matcher: AbstractMatcher, console: Console, osm: list[OsmObject], gov: list[OsmObject], matches: dict[int, int]) -> dict[int, int]:
    found = {}
    excluded_gov = matches.keys()
    excluded_osm = matches.values()

    for govitem in track(gov, description='Matching gov data'):
        with console.status("Matching starting") as status:
            status.update(f"Processing: {govitem.tags.get('name', govitem.tags.get('short_name', govitem.tags.get('official_name', govitem.id)))}")
        if govitem.id in excluded_gov or not matcher.check(govitem):
            continue

        for osmitem in osm:
            if osmitem.id in excluded_osm or not matcher.check(osmitem):
                continue

            if matcher.compare(govitem, osmitem):
                if govitem.id in found:
                    del found[govitem.id]
                    break
                if osmitem.id in found.values():
                    del found[next(key for key, value in found.items() if value == osmitem.id)]
                    continue
                found[govitem.id] = osmitem.id
    return found

def _get_matchers(config, engine, names, addr, location, tags) -> list[AbstractMatcher]:
    matchers = []

    if names and config.match_by.get('names', False):
        matchers.append(NamesMatcher())
    if addr and config.match_by.get('address', False):
        matchers.append(AddressMatcher(config.match_by.get('address').get('single_in_city', False)))
    if location and config.match_by.get('location', False):
        matchers.append(LocationMatcher(config.match_by['location'], engine))
    if tags and config.match_by.get('tags', False):
        for tags_group in config.match_by.get('tags', []):
            matchers.append(TagsListMatcher(tags_group))

    return matchers


def match(name, engine, console: Console, names=False, addr=False, location=False, tags=False):
    if not any([names, addr, location, tags]):
        console.log('No matching criteria selected, skipping matching step.')
        return

    config = importlib.import_module(f'data.{name}.conf')
    gov: list[OsmObject] = read_file(f'{WORKDIR.format(name=name)}/gov.csv', console, 'csv')
    osm: list[OsmObject] = read_file(f'{WORKDIR.format(name=name)}/data.osm', console, 'osm')
    matches = read_matches(name)

    for matcher in _get_matchers(config, engine, names, addr, location, tags):
        console.log(f'Validating against rule {matcher}')
        found = _find_matches(matcher, console, osm, gov, matches)
        console.log(f'Matched {len(found)} POIs')
        matches.update(found)

    console.log(f'Matched {len(matches)} POIs in total')
    save_matches(matches, name)
    # to_add = _add_new(gov, name, config.tags_source)


def fill(conf_name: str, osm: OsmObject, gov: OsmObject, update_addr=False) -> OsmObject:
    conf = importlib.import_module(f'data.{conf_name}.conf')
    ready = copy.deepcopy(osm)

    ready_tags = update_with_gov(ready.tags, gov.tags, update_addr)
    ready_tags = delete_add_tags_conf(ready_tags, conf_name)
    ready_tags = replace_tags_conf(ready_tags, conf_name)

    if conf.rules.get('rewrite_tags', False):
        ready_tags = rewrite_tags(ready_tags, conf_name)

    if ready_tags != gov.tags:
        ready.modify = True
        ready_tags.update(conf.tags_source)

    ready.tags = ready_tags

    return ready


def update_with_gov(osm_tags, gov_tags, update_addr=False):
    tags = copy.deepcopy(osm_tags)
    tags_gov = copy.deepcopy(gov_tags)

    if not update_addr:
        for key in FIELDS['addr']:
            if tags.get(key) and tags_gov.get(key):
                del tags_gov[key]

    tags.update(tags_gov)
    return tags


def delete_add_tags_conf(tags_to_mod, conf_name):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    tags = copy.deepcopy(tags_to_mod)

    for key_d, val_d in conf.tags_to_delete.items():
        if key_d in tags:
            if val_d == '*' or tags[key_d] == val_d:
                del tags[key_d]

    for key_a, val_a in conf.tags_to_add.items():
        tags[key_a] = val_a

    return tags


def replace_tags_conf(tags_to_mod, conf_name):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    tags = copy.deepcopy(tags_to_mod)

    for key, fn in conf.tags_to_replace.items():
        if tags.get(key):
            tags[key] = fn(tags[key])

    return tags


def rewrite_tags(tags_to_mod, conf_name):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    old_tags = copy.deepcopy(tags_to_mod)
    new_tags = copy.deepcopy(tags_to_mod)

    for old_key, new_key in conf.rules['rewrite_tags'].items():
        if old_tags.get(old_key):
            new_tags[new_key] = old_tags[old_key]
            del new_tags[old_key]

    return new_tags
