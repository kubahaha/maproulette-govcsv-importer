import csv
from .types import OsmNode, OsmWay
import json
import copy


def read_file(path, mode="osm"):
    f_in = open(path, 'r')
    objects = []

    if mode == 'osm':
        child_nodes_mapping = {}
        osm = json.load(open(path, 'r'))
        for elem in osm.get('elements', []):
            elem_type = elem.get('type')
            if elem_type == 'way':
                id = elem.get('id')
                version = elem.get('version')
                timestamp = elem.get('timestamp')
                changeset = elem.get('changeset')
                uid = elem.get('uid')
                user = elem.get('user')
                tags = elem.get('tags', {})

                nodes_ordered = []
                for child_node_id in elem.get('nodes'):
                    child_nodes_mapping[child_node_id] = id
                    nodes_ordered.append(child_node_id)

                obj = OsmWay(id=id, nodes_ordered=nodes_ordered, version=version, timestamp=timestamp, changeset=changeset, uid=uid, user=user, tags=tags)
                objects.append(obj)

        for elem in osm.get('elements', []):
            elem_type = elem.get('type')
            if elem_type == 'node':
                id = elem.get('id')
                version = elem.get('version')
                timestamp = elem.get('timestamp')
                changeset = elem.get('changeset')
                uid = elem.get('uid')
                user = elem.get('user')
                tags = elem.get('tags', {})
                obj = OsmNode(
                    elem.get('lat'),
                    elem.get('lon'),
                    id=id, version=version, timestamp=timestamp, changeset=changeset, uid=uid, user=user, tags=tags)
                if id in child_nodes_mapping:
                    for way in objects:
                        if way.id == child_nodes_mapping[id]:
                            children = copy.deepcopy(way.child_nodes)
                            children.append(obj)
                            way.child_nodes = children
                            break
                else:
                    objects.append(obj)
        # for elem in objects:
        #     if isinstance(elem, OsmWay):
        #         # TODO: sort children
        #         # sort_children(elem, order)
        #         children = copy.deepcopy(elem.child_nodes)
        #         children.append(children[0])
        #         elem.child_nodes = children

    elif mode == "csv":
        r_in = csv.DictReader(f_in)
        tags = [field for field in r_in.fieldnames if field[0:2] != '__']
        # properties = [field for field in r_in.fieldnames if field not in tags]

        for row in r_in:
            lat = float(row.get('__lat').replace(',', '.')) if row.get('__lat') else False
            lon = float(row.get('__lon').replace(',', '.')) if row.get('__lon') else False

            obj = OsmNode(lat, lon, tags={k: row.get(k) for k in tags if row.get(k)})
            objects.append(obj)
    else:
        raise NotImplementedError()

    return objects
