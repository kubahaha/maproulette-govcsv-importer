from src.utils import strip_number, force_https, parse_address


prepare = {
    "separator": ',',
    "tags": {
        'name': 'Nazwa Muzeum',
        'addr:postcode': 'Kod pocztowy',
        'addr:city': 'Miejscowość',
        'addr:street': 'Ulica',
        'addr:housenumber': 'Numer domu',
        'operator': 'Nazwa Organizatora/ Założyciela',
        'operator:type': {
            'Status muzeum': {
                'Państwowe': 'government',
                'Samorządowe': 'government',
                'samorządowe': 'government',
                'Współprowadzone wpisane do rejestru prowadzonego przez jednostkę samorządu terytorialnego': 'government',
                'Współprowadzone wpisane do rejestru prowadzonego przez Ministra Kultury i Dziedzictwa Narodowego': 'government',
                'Współprowadzone wpisane do rejestru prowdzonego przez jednostkę samorządu terytorialnego': 'government',
                'Współprowadzone wpisane przez rejestru prowadzonego przez jednostkę samorządu terytorialnego': 'government',
                'Wspólprowadzone wpisane do rejestru prowadzonego przez jedostkę samorządu terytorialnego': 'government',
                'Kościelne': 'religious',
                'Utworzone przez osoby fizyczne': 'private',
                'Utworzone przez osoby Fizyczne': 'private',
                'Utworzoneprzez osoby fizyczne': 'private',
                'Utworzone przez osoby prawne': 'ngo',
                'utworzone przez osoby prawne': 'ngo',
                'Utworzone przez osobę prawną': 'ngo',
                'Utworzone prze osoby prawne': 'ngo'
            }
        }
    }
}

match_by = {
    "names": True,
    "address": {
        "single_in_city": False,
    },
    "location": 300,
    "tags": []
}

tags_to_delete = {
    'amenity': '*'
}

tags_to_add = {
    'tourism': 'museum'
}
tags_source = {'source:tourism': 'Wykaz Muzeów, wypis na dzień 2026-04-09'}
tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': True
}
