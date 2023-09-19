import csv
import importlib.util
import osmium
import random
import requests
from src.utils import nominatim_addr, nominatim_searchurl

NOMINATIM_SERVER = 'https://nominatim.openstreetmap.org'
ADDR_FIELDS = 'addr:postcode', 'addr:city', 'addr:place', 'addr:street', 'addr:housenumber'

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
        self.waynodes = set()


    def node(self, n):
        self.all.update({f'N{n.id}': n.replace(tags=dict(n.tags))})
        if _haveaddr(n.tags):
            self.filled.append(f'N{n.id}')
        else:
            self.nomatch.append(f'N{n.id}')

    def way(self, w):
        self.waynodes.update([n.ref for n in w.nodes])
        self.all.update({f'W{w.id}': w.replace(tags=dict(w.tags))})
        if _haveaddr(w.tags):
            self.filled.append(f'W{w.id}')
        else:
            self.nomatch.append(f'W{w.id}')

    def add_addresses(self):
        batches = [self.nomatch[i:i+50] for i in range(0, len(self.nomatch), 50)]

        for b in batches:
            url = f'{NOMINATIM_SERVER}/lookup?osm_ids={",".join(b)}&format=json'
            print(f'Downloading: {url}')
            res = requests.get(url).json()
            for it in res:
                key = f'{it.get("osm_type")[0].upper()}{it.get("osm_id")}'
                self.match[key] = osmium.osm.mutable.Node(
                    tags=nominatim_addr(it),
                    location=osmium.osm.Location(float(it.get("lon")), float(it.get("lat"))),
                    id=it.get("osm_id")
                )
                self.nomatch.remove(key)

        total = len(self.match) + len(self.nomatch) + len(self.filled)
        print(f'{total} items in total, {len(self.filled)} filled. {len(self.match)} updated, {len(self.nomatch)} not matched')

class GovHandler():
    def __init__(self, name, fill_details=True):
        print(f'Importing conf/{name}_conf.py')
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.all = {}
        self.match = {}
        self.nomatch = []
        self.fill_details = fill_details

    def import_csv(self, filename):
        f = open(filename, 'r')
        r = csv.DictReader(f)
        for row in r:
            id = f'-{round(random.random() * 10 ** 10)}'
            location = ''
            if '__lat' in row and '__lon' in row:
                location = osmium.osm.Location(float(row.get("__lat")), float(row.get("__lon"))),
                del row['__lat']
                del row['__lon']

            tags = row
            self.all.update({id: osmium.osm.mutable.Node(
                    tags=tags,
                    location=location,
                    id=id
                )})
        
        if self.fill_details:
            self.add_cords()
        else:
            self.nomatch = list(self.al.keys())

    def add_cords(self):
        for it_k, it_v in self.all.items():
            search = nominatim_searchurl(it_v.tags)
            url = f'{NOMINATIM_SERVER}/search?{search}&addressdetails=1&format=json'
            # print(url)
            res = requests.get(url).json()
            if res:
                item = osmium.osm.mutable.Node(
                    tags=nominatim_addr(res[0]),
                    location=osmium.osm.Location(float(res[0].get("lon")), float(res[0].get("lat"))),
                    id=res[0].get("osm_id")
                )
                self.match.update({it_k: item})
            else:
                search2 = nominatim_searchurl(it_v.tags, single=True)
                url2 = f'{NOMINATIM_SERVER}/search?q={search2}&addressdetails=1&format=json'
                # print(url)
                res2 = requests.get(url2).json()
                if res2:
                    item = osmium.osm.mutable.Node(
                        tags=nominatim_addr(res2[0]),
                        location=osmium.osm.Location(float(res2[0].get("lon")), float(res2[0].get("lat"))),
                        # location=osmium.osm.Location(float(res2[0].get("lon")), float(res2[0].get("lat"))),
                        id=res2[0].get("osm_id")
                    )
                    self.match.update({it_k: item})
                else:
                    print(f'Downloading failed - not found!')
                    print(f'  {url}')
                    print(f'  {url2}')
                    self.nomatch.append(it_k)


        total = len(self.match) + len(self.nomatch)
        print(f'{total} items in total. {len(self.match)} updated, {len(self.nomatch)} not matched')