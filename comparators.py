from collections import defaultdict

from src.geodistance import geodistance

def match_latlon(latlon1, latlon2, limit=100):
    if geodistance(latlon1.lat, latlon1.lon, latlon2.lat, latlon2.lon) > limit:
        return False
    return True

def distance_m(gov_match, osm_all, osm_match, dist):
    mapping = {
        'osm': defaultdict(list),
        'gov': defaultdict(list)
    }

    for g_id, g in gov_match.items():
        latlon_g = g.location
        for o_id, o in osm_all.items():
            if hasattr(o, "location"):
                latlon_o = o.location
            elif id in osm_match:
                latlon_o = osm_match.get(id).location
            else:
                continue
            if match_latlon(latlon_g, latlon_o, limit=dist):
                mapping['osm'][o_id].append(g_id)
                mapping['gov'][g_id].append(o_id)
    return mapping

def tags_m(taglist, gov_match, osm_all, osm_match):
    mapping = {
        'osm': defaultdict(list),
        'gov': defaultdict(list)
    }

    for g_id, g in gov_match.items():
        gov_tags_a = [f'{x}={g.tags.get(x) or "_"}' for x in taglist]
        gov_tags = '&'.join(gov_tags_a)

        for o_id, o in osm_all.items():
            if hasattr(o, 'location'):
                osm_tags_a = [f'{x}={o.tags.get(x) or "_"}' for x in taglist]
            elif id in osm_match:
                osm_tags_a = [f'{x}={o.tags.get(x) or osm_match.get(o_id).tags.get(x) or "_"}' for x in taglist]
            else:
                continue

            osm_tags = '&'.join(osm_tags_a)

            if gov_tags == osm_tags:
                mapping['osm'][o_id].append(g_id)
                mapping['gov'][g_id].append(o_id)

    return mapping
