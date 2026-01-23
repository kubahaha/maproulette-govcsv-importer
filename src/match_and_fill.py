import importlib.util
import copy

from rich.console import Console
from rich.progress import Progress

from src.match_rules import AbstractMatcher, LocationMatcher, TagsListMatcher
from src.utils import FIELDS
from src.osm_model.types import OsmObject


def _select_matcher(rule, engine, download_latlon: bool = True) -> AbstractMatcher:
    if isinstance(rule, list):
        return TagsListMatcher(rule)

    if isinstance(rule, str) and rule.split(':')[0] == 'location':
        dist = int(rule.split(':')[1])
        return LocationMatcher(dist, engine=engine, download_latlon=download_latlon)

    raise NotImplementedError()

def _add_new(gov: list[OsmObject], name: str, tags_source: dict) -> list[OsmObject]:
    to_add = []
    for govitem in gov:
        if not govitem.is_found():
            govitem.modify = True
            ready = copy.deepcopy(govitem)

            ready_tags = delete_add_tags_conf(ready.tags, name)
            ready_tags = replace_tags_conf(ready_tags, name)

            ready_tags.update(tags_source)
            ready.tags = ready_tags

            to_add.append(ready)
    return to_add

def _find_matches(govitem, osm, matcher: AbstractMatcher):
    matchgov, matchosm = [], []

    for osmitem in osm:
        if osmitem.is_found() or not matcher.check(osmitem):
            continue

        if matcher.compare(govitem, osmitem):
            matchgov.append(govitem)
            matchosm.append(osmitem)

    return matchgov, matchosm

def _process_gov_items(gov, osm, matcher, name, to_change, console: Console):
    counter = 0

    with Progress() as progress:
        task = progress.add_task("Matching gov data", total=len(gov))

        for govitem in gov:
            progress.update(task, description=f"Processing: {govitem.tags.get('name', govitem.tags.get('short_name', govitem.tags.get('official_name', govitem.id)))}")
            progress.advance(task)

            if govitem.is_found() or not matcher.check(govitem):
                continue

            matchgov, matchosm = _find_matches(govitem, osm, matcher)

            if len(matchgov) == 1 == len(matchosm):
                matchosm[0].found()
                matchgov[0].found()
                to_change.append(fill(name, matchosm[0], matchgov[0]))
                counter += 1

    return counter

def match(gov: list[OsmObject], osm: list[OsmObject], name, engine, console: Console) -> tuple[list, list]:
    config = importlib.import_module(f'data.{name}.conf')
    to_change, to_add = [], []

    for rule in config.matching:
        console.log(f'Validating against rule {rule}')
        matcher = _select_matcher(rule, engine, config.rules.get('download_latlon', True))

        counter = _process_gov_items(gov, osm, matcher, name, to_change, console)
        console.log(f'Matched {counter} POIs')

    to_add = _add_new(gov, name, config.tags_source)
    return to_change, to_add


def fill(conf_name, osm, gov):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    ready = copy.deepcopy(osm)

    ready_tags = update_with_gov(ready.tags, gov.tags, conf_name)
    ready_tags = delete_add_tags_conf(ready_tags, conf_name)
    ready_tags = replace_tags_conf(ready_tags, conf_name)

    if conf.rules.get('rewrite_tags', False):
        print('rewrite')
        print(ready_tags)
        ready_tags = rewrite_tags(ready_tags, conf_name)
        print(ready_tags)

    if ready_tags != gov.tags:
        ready.modify = True
        ready_tags.update(conf.tags_source)

    ready.tags = ready_tags

    return ready


def update_with_gov(osm_tags, gov_tags, conf_name):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    tags = copy.deepcopy(osm_tags)
    tags_gov = copy.deepcopy(gov_tags)

    if not conf.rules['update_addr']:
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
