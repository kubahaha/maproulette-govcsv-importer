from math import sin, cos, sqrt, atan2, radians

# Approximate radius of earth in km
R = 6373.0
R = R * 1000

def geodistance(lat1, lon1, lat2, lon2):
    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

if __name__ == '__main__':
    geodistance()