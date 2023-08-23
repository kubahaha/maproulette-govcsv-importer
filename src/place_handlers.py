import csv
import importlib.util
import osmium
import random
import requests


NOMINATIM_SERVER = 'https://nominatim.openstreetmap.org'

def _haveaddr(tags):
    if not all(x in tags for x in ['addr:postcode', 'addr:housenumber']):
        return False
    else:
        if all(x in tags for x in ['addr:city', 'addr:street']):
            return True
        if 'addr:place' in tags:
            return True
        return False


class OsmHandler(osmium.SimpleHandler):
    def __init__(self, name):
        super(OsmHandler, self).__init__()
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.match = {}
        self.nomatch = []
        self.filled = []
        self.all = {}


    def node(self, n):
        self.all.update({f'N{n.id}': {
            'id': n.id,
            'version': n.version,
            'tags': {k:v for k,v in n.tags},
            'location': n.location
        }})
        if _haveaddr(n.tags):
            self.filled.append(f'N{n.id}')
        else:
            self.nomatch.append(f'N{n.id}')

    def way(self, w):
        # print([node.location for node in w.nodes])
        self.all.update({f'W{w.id}': {
            'id': w.id,
            'version': w.version,
            'tags': {k:v for k,v in w.tags}
            # 'nodes': [{'x': node.x, 'y': node.y} for node in w.nodes]
        }})

        if _haveaddr(w.tags):
            self.filled.append(f'W{w.id}')
        else:
            self.nomatch.append(f'W{w.id}')

    def add_addresses(self):
        batches = [self.nomatch[i:i+50] for i in range(0, len(self.nomatch), 50)]

        for b in batches:
            url = f'{NOMINATIM_SERVER}/lookup?osm_ids={",".join(b)}&format=json'
            # print(f'Downloading: {url}')
            res = requests.get(url).json()
            for it in res:
                key = f'{it.get("osm_type")[0].upper()}{it.get("osm_id")}'
                self.match[key] = it
                self.nomatch.remove(key)

        total = len(self.match) + len(self.nomatch) + len(self.filled)
        print(f'{total} items in total, {len(self.filled)} filled. {len(self.match)} updated, {len(self.nomatch)} not matched')

class GovHandler():
    def __init__(self, name):
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.all = {}
        self.match = {}
        self.nomatch = []

    def import_csv(self, filename):
        f = open(filename, 'r')
        r = csv.DictReader(f)
        for row in r:
            id = f'-{round(random.random() * 10 ** 10)}'
            self.all.update({id: row})

    def add_cords(self):
        for it_k, it_v in self.all.items():
            addr = '&'.join([f'{k}={v(it_v)}' for k,v in self.config.search.items()])
            url = f'{NOMINATIM_SERVER}/search?{addr}&addressdetails=1&format=json'
            # print(url)
            res = requests.get(url).json()
            if res:
                self.match.update({it_k: res[0]})
            else:
                print(f'Downloading {url} failed - not found!')
                self.nomatch.append(it_k)


        total = len(self.match) + len(self.nomatch)
        print(f'{total} items in total. {len(self.match)} updated, {len(self.nomatch)} not matched')