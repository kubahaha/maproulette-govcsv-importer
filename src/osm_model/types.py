import random
from datetime import datetime

from src.utils import download_latlon
from src.engines.Nominatim import Nominatim
from src.engines.Komoot import Komoot


class OsmObject:
    def __init__(self, id=None, version=1, timestamp=datetime.utcnow().isoformat() + 'Z', changeset=None, uid=None, user=None, tags={}):
        self.id = id or -random.getrandbits(30)
        self._version = version
        self._timestamp = timestamp
        self._changeset = changeset
        self._uid = uid
        self._user = user
        self._tags = tags
        self._found = False
        self._modify = False

    @property
    def tags(self):
        return self._tags or {}

    @tags.setter
    def tags(self, value):
        self._tags = value

    @property
    def modify(self):
        return self._modify

    @modify.setter
    def modify(self, value):
        self._modify = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def get_tag(self, tag):
        return self._tags.get(tag, False)

    def get_attr(self, attr):
        return self.__getattribute__(attr)

    def has_tag(self, tag):
        return True if self._tags.get(tag) else False

    def __str__(self):
        return f'{self.id}: {self._tags}'

    def found(self):
        self._found = True

    def is_found(self):
        return self._found

    def download_lat_lon(self, engine):
        if engine == 'nominatim':
            run_engine = Nominatim
        if engine == 'komoot':
            run_engine = Komoot

        latlon = download_latlon(self._tags, engine=run_engine)

        lat, lon = float(latlon.get('lat')) if latlon.get('lat') else False, float(latlon.get('lon')) if latlon.get('lon') else False
        self._lat = lat
        self._lon = lon
        return {'lat': lat, 'lon': lon}


class OsmNode(OsmObject):
    def __init__(self, lat, lon, **kwargs):
        super(OsmNode, self).__init__(**kwargs)
        self._lat = lat
        self._lon = lon

    def has_loc(self):
        return all([self._lat, self._lon])

    @property
    def loc(self):
        return (self._lat, self._lon)

    @loc.setter
    def loc(self, value):
        self._loc = value

    def get_child_nodes(self):
        return []

    def print(self, mode='xml'):
        if not self.has_loc():
            return ''
        if mode == 'xml':
            tags_str = "\n".join("\t<tag k=\"{}\" v=\"{}\"/>".format(k, " ".join(v.split())) for k, v in self.tags.items())
            return f'''<node id="{self._id}" lat="{self._lat}" lon="{self._lon}" version="{self._version}" timestamp="{self._timestamp}" {'action="modify"' if self._modify else ''} {'changeset="' + str(self._changeset) + '"' if self._changeset else ''} {'uid="' + str(self._uid) + '"' if self._uid else ''} {'user="' + str(self._user) + '"' if self._user else ''}>
{tags_str}
</node>'''
        else:
            raise NotImplementedError()


class OsmWay(OsmObject):
    def __init__(self, nodes_ordered=[], **kwargs):
        super(OsmWay, self).__init__(**kwargs)
        self._child_nodes = []
        self._nodes_ordered = nodes_ordered

    @property
    def child_nodes(self):
        return self._child_nodes

    @child_nodes.setter
    def child_nodes(self, value):
        self._child_nodes = value

    def has_loc(self):
        return all(node.has_loc() for node in self._child_nodes)

    @property
    def loc(self):
        if len(self._child_nodes) > 0:
            return self._child_nodes[0].loc
        return (0, 0)
        # x, y = 0, 0
        # n = len(self._child_nodes)
        # print(f'{self._id} childnodes: {n}')
        # signed_area = 0
        # for i in range(n):
        #     x0, y0 = self._child_nodes[i].loc
        #     x1, y1 = self._child_nodes[(i + 1) % n].loc

        #     area = (x0 * y1) - (x1 * y0)

        #     signed_area += area
        #     print(signed_area)
        #     x += (x0 + x1) * area
        #     y += (y0 + y1) * area
        # signed_area *= 0.5
        # x /= 6 * signed_area
        # y /= 6 * signed_area
        #
        # return x, y

    @loc.setter
    def loc(self, value):
        self._loc = value

    def print(self, mode='xml'):
        if not self.has_loc():
            return ''
        if mode == 'xml':
            tags_str = "\n".join("\t<tag k=\"{}\" v=\"{}\"/>".format(k, " ".join(v.split())) for k, v in self._tags.items())
            nodes_ref_str = "\n".join("\t<nd ref=\"{}\"/>".format(cn) for cn in self._nodes_ordered)
            nodes_str = "\n".join(node.print() for node in self._child_nodes)

            return f'''<way id="{self._id}" version="{self._version}" timestamp="{self._timestamp}" {'action="modify"' if self._modify else ''} changeset="{self._changeset}" uid="{self._uid}" user="{self._user}">
{tags_str}
{nodes_ref_str}
</way>
{nodes_str}'''
