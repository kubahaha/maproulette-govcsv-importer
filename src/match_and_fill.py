import importlib.util
import copy

from rich.console import Console

from src.compare import compare, distance
from src.utils import fieldnames


console = Console()


def match(gov, osm, name, engine='nominatim'):
    to_change, to_add = [], []
    config = importlib.import_module(f'data.{name}.conf')

    for rule in config.matching:
        counter = 0
        console.log(f'Validating against rule {rule}')
        if isinstance(rule, list):
            def check(x):
                return all([x.has_tag(tag) for tag in rule])

            def comp(x, y):
                return all([compare(x.get_tag(tag), y.get_tag(tag)) for tag in rule])
        elif isinstance(rule, str):
            if rule.split(':')[0] == 'location':
                dist = int(rule.split(':')[1])

                def check(x):
                    if not x.has_loc() and config.rules.get('download_latlon'):
                        x.download_lat_lon(engine=engine)

                    return x.has_loc()

                def comp(x, y):
                    return distance(x.loc, y.loc) <= dist
            else:
                raise NotImplementedError()

        for govitem in gov:
            matchgov, matchosm = [], []

            if govitem.is_found():
                continue
            if not check(govitem):
                continue

            for osmitem in osm:
                if osmitem.is_found():
                    continue
                if not check(osmitem):
                    continue

                if comp(govitem, osmitem):
                    matchgov.append(govitem)
                    matchosm.append(osmitem)

            if len(matchgov) == 1 == len(matchosm):
                matchosm[0].found()
                matchgov[0].found()
                to_change.append(fill(name, matchosm[0], matchgov[0]))
                counter += 1

        console.log(f'Matched {counter} POIs')

    for govitem in gov:
        if not govitem.is_found():
            govitem.modify = True
            ready = copy.deepcopy(govitem)

            ready_tags = delete_add_tags_conf(ready.tags, name)
            ready_tags = replace_tags_conf(ready_tags, name)

            ready_tags.update(config.tags_source)
            ready.tags = ready_tags

            to_add.append(ready)

    return to_change, to_add


def fill(conf_name, osm, gov):
    conf = importlib.import_module(f'data.{conf_name}.conf')
    ready = copy.deepcopy(osm)

    ready_tags = update_with_gov(ready.tags, gov.tags, conf_name)
    ready_tags = delete_add_tags_conf(ready_tags, conf_name)
    ready_tags = replace_tags_conf(ready_tags, conf_name)

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
        for key in fieldnames['addr']:
            if tags.get(key):
                if tags_gov.get(key):
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
