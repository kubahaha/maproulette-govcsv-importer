from src.utils import strip_number, force_https


prepare = {
    "accept": lambda _: True,
    "separator": ';',
    "tags": {
        'ref': 'Numer stacji',
        'name': 'Nazwa stacji',
        '__lat': 'Współrzędne1',
        '__lon': 'Współrzędne2',
        'capacity': 'Liczba stojaków'
    }
}

matching = [
    "location:100",
    ['name']
]

tags_to_delete = {
    'contact:website': '*',
    'contact:phone': '*'
}

tags_to_add = {
    'amenity': 'bicycle_rental',
    'email': 'ck@wroclawskirower.pl',
    'website': 'https://wroclawskirower.pl',
    'operator': 'NextBike',
    'operator:wikidata': 'Q2351279',
    'network': 'Wrocławski Rower Miejski',
    'network:wikidata': 'Q24941606',
    'network:short': 'WRM'
}

tags_source = {'source:position': 'https://wroclawskirower.pl/mapa-stacji'}

tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': False,
    'rewrite_tags': False
}
