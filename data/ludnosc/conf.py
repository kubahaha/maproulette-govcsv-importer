from src.utils import strip_number, force_https
import re
import requests

prepare = {
    "accept": lambda x: x.get('Kod')[-1] in ['1', '4'],
    "separator": ';',
    "tags": {
        'teryt:terc': 'Kod',
        'name': lambda x: x.get('Nazwa').replace(' - miasto (4)', '').replace(' (1)', '').strip(),
        'population': 'ogolem',
        'teryt:simc': lambda x: get_simc(x.get('Kod'))
    }
}

matching = [
    ['teryt:terc'],
    ['teryt:simc']
]

tags_to_delete = {}

tags_to_add = {}
tags_source = {
    'source:population': 'Narodowy Spis Powszechny 2021',
    'population:date': '2021-06-30'
}
tags_to_replace = {}

rules = {
    'update_addr': False
}


def get_simc(terc):
    simc = requests.get(f'http://127.0.0.1:5000/terc2simc/{terc}')
    return simc.text
