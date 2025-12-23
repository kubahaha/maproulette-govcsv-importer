from src.utils import strip_number, force_https


prepare = {
    "accept": lambda x: True,
    "separator": ',',
    "tags": {
        'name': 'NAZWA',
        'addr:postcode': 'KOD',
        'addr:city': 'MIASTO',
        'addr:street': 'ULICA',
        'addr:housenumber': 'NUMER'
    }
}

matching = [
    ['name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode'],
    "location:300"
]

tags_to_delete = {}

tags_to_add = {'amenity': 'cinema'}

tags_source = {}

tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': True
}
