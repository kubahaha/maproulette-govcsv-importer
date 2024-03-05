from src.utils import strip_number, force_https, get_opening_hours, get_operator


prepare = {
    "accept": lambda x: x.get('Czy podmiot prowadzący zawiesił działalność gospodarczą?') == 'NIE',
    "separator": ';',
    "tags": {
        'amenity': {'Typ instytucji': {'Żłobek': 'kindergarten', 'Klub dziecięcy': 'childcare'}},
        'capacity': 'Liczba miejsc',
        'email': 'E-mail żłobka/klubu',
        'name': lambda x: x.get('Nazwa', '').replace('"', '').capitalize().strip() if x.get('Nazwa', '').replace('"', '').isupper() else x.get('Nazwa', '').replace('"', '').strip(),
        'official_name': 'Nazwa',
        'opening_hours': lambda x: get_opening_hours(x.get('Godziny otwarcia', '')),
        'operator': lambda x: x.get('Podmiot prowadzący - nazwa', '').replace('"', '').capitalize().strip() if x.get('Podmiot prowadzący - nazwa', '').replace('"', '').isupper() else x.get('Podmiot prowadzący - nazwa', '').replace('"', '').strip().replace('m.st. Warszawa - ZESPÓŁ ŻŁOBKÓW M. ST. WARSZAWY', 'Zespół Żłobków Miasta Stołecznego Warszawy'),
        'operator:type': lambda x: get_operator(x.get('Nazwa', ''), x.get('Podmiot prowadzący - nazwa', '')),
        'operator:website': 'Adres WWW podmiotu prowadzącego żłobek/klub',
        'phone': lambda x: strip_number(x.get('Telefon żłobka/klubu'), format='333'),
        'website': lambda x: force_https(x.get('Adress WWW żłobka/klubu')),
        'wheelchair': lambda x: 'yes' if x.get('Czy żłobek/klub jest dostosowany do potrzeb dzieci niepełnosprawnych lub wymagających szczególnej opieki?', '') == 'TAK' else 'no'
    }
}

matching = [
    ['official_name'],
    ['name', 'addr:city'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    "location:300",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode']
]

tags_to_delete = {
    'access': '*',
    'addr:city:simc': '*',
    'addr:country': '*',
    'mobile': '*',
    'addr:county': '*',
    'addr:housename': '*',
    'addr:state': '*',
    'addr:street:sym_ul': '*',
    'contact:email': '*',
    'contact:fax': '*',
    'contact:phone': '*',
    'contact:website': '*',
    'name:pl': '*',
    'opening_hours:covid19': '*',
    'source': '*',
    'designation': '*',
    'ref': '*'
}

tags_to_add = {}

tags_source = {'source:office': 'Rejestr Żłobków na dzień 04.03.2024'}

tags_to_replace = {}

rules = {
    # 'allow_empty_values': False,
    'update_addr': False,
    'download_latlon': True
}
