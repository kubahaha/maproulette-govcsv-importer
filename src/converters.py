def nominatim_addr(nominatim):
    prefix = nominatim['address']
    city = prefix.get('city') or prefix.get('town') or prefix.get('village')
    city_not_place = prefix.get('road') or (city and prefix.get('place'))

    return {
        'addr:housenumber': prefix.get('house_number'),
        'addr:street': prefix.get('road'),
        'addr:city': city if city_not_place else '',
        'addr:place': city if not city_not_place else prefix.get('place'),
        'addr:postcode': prefix.get('postcode'),
        'addr:door': prefix.get('door')
    }


def komoot_addr(komoot):
    prefix = komoot['features'][0]['properties']
    is_city = prefix.get('city') and (prefix.get('street') or prefix.get('locality'))

    return {
        'addr:housenumber': prefix.get('housenumber'),
        'addr:street': prefix.get('street'),
        'addr:city': prefix.get('city') if is_city else '',
        'addr:place': prefix.get('city') if not is_city else prefix.get('locality'),
        'addr:postcode': prefix.get('postcode'),
        'addr:door': prefix.get('door')
    }
