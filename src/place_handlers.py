import csv
import importlib.util
import random
import requests
import urllib.parse

import osmium
from rich.console import Console
from rich.live import Live
from rich.progress import track, BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from src.utils import nominatim_addr, nominatim_searchurl


console = Console()
NOMINATIM_SERVER = 'https://nominatim.openstreetmap.org'

progress_bar = Progress(
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    BarColumn(),
    MofNCompleteColumn(),
    TextColumn("•"),
    TimeElapsedColumn(),
    TextColumn("•"),
    TimeRemainingColumn(),
)

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
        console.log(f'Importing OSM data from file: `input/{name}.osm`')
        self.name = name
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
        console.log('Starting adding addresses for OSM data...')
        batches = [self.nomatch[i:i+50] for i in range(0, len(self.nomatch), 50)]

        with progress_bar as p:
            for b in p.track(batches, description='Filling addresses and location data'):
                url = f'{NOMINATIM_SERVER}/lookup?osm_ids={",".join(b)}&format=json'
                p.console.log(f'Processing url: {url}')
                res = requests.get(url).json()
                for it in res:
                    key = f'{it.get("osm_type")[0].upper()}{it.get("osm_id")}'
                    self.match[key] = osmium.osm.mutable.Node(
                        tags=nominatim_addr(it),
                        location=osmium.osm.Location(float(it.get("lon")), float(it.get("lat"))),
                        id=it.get("osm_id")
                    )
                    self.nomatch.remove(key)
            p.console.log('Finished processing OSM data.')

        total = len(self.match) + len(self.nomatch) + len(self.filled)
        t = Table(title="OSM data details", title_justify="center")
        t.add_column("Label", justify="left")
        t.add_column("Count", justify="right")
        t.add_column("Percentage", justify="right")
        t.add_row('[green]Address available in object', str(len(self.filled)), str(round(100 * len(self.filled)/total)) + '%')
        t.add_row('[yellow]Address matched with OSM', str(len(self.match)), str(round(100 * len(self.match)/total)) + '%')
        t.add_row('[red]Not matched addresses', str(len(self.nomatch)), str(round(100 * len(self.nomatch)/total)) + '%')
        t.add_row('[bold]total', str(total))
        console.print(t)

class GovHandler():
    def __init__(self, name, fill_details=True):
        self.name = name
        self.config = importlib.import_module(f'conf.{name}_conf')
        self.all = {}
        self.match = {}
        self.nomatch = []
        self.fill_details = fill_details

    def import_csv(self, filename):
        console.log(f'Importing GOV data from file: `{filename}`')
        f = open(filename, 'r')
        r = csv.DictReader(f)
        for row in r:
            id = f'-{round(random.random() * 10 ** 10)}'
            location = ''
            if '__lat' in row and '__lon' in row:
                location = osmium.osm.Location(float(row.get("__lat").replace(',', '.')), float(row.get("__lon").replace(',', '.'))),
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
        console.log('Starting adding coordinates for gov data...')
        with progress_bar as p:
            for it_k, it_v in p.track(self.all.items(), description='Filling addresses and location data'):
                search = nominatim_searchurl(it_v.tags)
                url = f'{NOMINATIM_SERVER}/search?{search}&addressdetails=1&format=json'
                # print(url)
                res = requests.get(url).json()
                if not res:
                    search2 = nominatim_searchurl(it_v.tags, single=True)
                    url2 = f'{NOMINATIM_SERVER}/search?q={search2}&addressdetails=1&format=json'
                    res2 = requests.get(url2).json()
                if not res2:
                    p.console.log(f'[bold][red]Downloading failed - Addr not found! {search}')
                    p.console.log(f'{NOMINATIM_SERVER}/ui/search.html?{urllib.parse.quote(search)}&addressdetails=1')
                    p.console.log(f'{NOMINATIM_SERVER}/ui/search.html?q={urllib.parse.quote(search2)}&addressdetails=1')
                    self.nomatch.append(it_k)
                    continue

                item = osmium.osm.mutable.Node(
                    tags=nominatim_addr(res[0]),
                    location=osmium.osm.Location(float(res[0].get("lon")), float(res[0].get("lat"))),
                    id=res[0].get('osm_id')
                )
                self.match.update({it_k: item})
                
            p.console.log('Finished processing gov data.')

        total = len(self.match) + len(self.nomatch)
        t = Table(title="OSM data details", title_justify="center")
        t.add_column("Label", justify="left")
        t.add_column("Count", justify="right")
        t.add_column("Percentage", justify="right")
        t.add_row('[green]Address found on OSM', str(len(self.match)), str(round(100 * len(self.match)/total)) + '%')
        t.add_row('[red]Address not found on OSM', str(len(self.nomatch)), str(round(100 * len(self.nomatch)/total)) + '%')
        t.add_row('[bold]total', str(total))
        console.print(t)