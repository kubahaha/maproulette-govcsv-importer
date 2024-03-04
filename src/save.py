from datetime import datetime


def save(location, data):
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Overpass API 0.7.61.5 4133829e">
<note>The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.</note>
<meta osm_base="{datetime.utcnow().isoformat() + 'Z'}" areas="datetime.utcnow().isoformat() + 'Z'"/>
"""
    footer = """</osm>"""

    file = open(location, 'w')
    file.write(header + data + footer)
    file.close()
