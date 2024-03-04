from collections import defaultdict
from math import radians, cos, sin, asin, sqrt


CACHE = defaultdict(dict)


def compare(left, right):
    return left == right


def distance(left, right):
    distance = harvestine(left, right)

    return distance


def harvestine(left, right):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """

    lat1, lon1 = left
    lat2, lon2 = right
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 * 1_000  # Radius of earth in meters.
    return c * r
