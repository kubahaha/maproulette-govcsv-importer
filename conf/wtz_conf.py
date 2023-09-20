from src.utils import getaddr
from conf.helpers import wtz_get_housenumber, wtz_getstartdate, wtz_postcode

prepare = {
    "tags": {
        'addr:postcode': wtz_postcode,
        'addr:city': lambda it: it.get('Miejscowość') if it.get('Ulica') else '',
        'addr:place': lambda it: getaddr(it.get('Miejscowość'), place=True, housenumber=True, door=True).get('addr:place') if not it.get('Ulica') else '',
        'addr:street': lambda it: getaddr(it.get('Ulica'), street=True, housenumber=True, door=True).get('addr:street').split('/')[0] if it.get('Ulica') else '',
        'addr:housenumber': wtz_get_housenumber,
        'name': 'Nazwa wtz',
        'operator': 'Organizator',
        'start_date': wtz_getstartdate
    }
}

matching = [
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    ['addr:place', 'addr:postcode'],
    "location:300"
]

tags_to_delete = {
    'amenity': '*',
    'healthcare': '*',
    'office': '*',
    'social_facility': '*',
    'social_facility:for': '*'
}

tags_to_add = {
    'amenity': 'social_facility',
    'social_facility': 'workshop',
    'social_facility:for': 'mental_health',
    'source:amenity': 'Baza adresowa warsztatów terapii zajęciowej - wypis na dzień 19.09.2023'
}

overpass = """[out:xml][timeout:9999];
    {{geocodeArea: Polska;}}->.searchArea;

    (
        nw[amenity=social_facility](area.searchArea);
        nw[amenity=school](area.searchArea);
        nw[healthcare](area.searchArea);
        nw[office](area.searchArea);
        nw[amenity=community_centre](area.searchArea);
    ) -> .pois;
    nw.pois["name"~"Warsztaty? Terapii Zajęciowej", i];
    out meta;
    >;
    out meta;
    """