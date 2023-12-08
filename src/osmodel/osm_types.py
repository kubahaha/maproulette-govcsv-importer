class OsmObject:
    def __init__(self, id, version, timestamp, changeset, uid, user, tags):
        self.id = id
        self.version = version
        self.timestamp = timestamp
        self.changeset = changeset
        self.uid = uid
        self.user = user
        self.tags = tags

class OsmNode(OsmObject):
    def __init__(self, attributes, lat, lon):
        super(attributes)
        self.lat = lat
        self.lon = lon

class OsmWay(OsmObject):
    def __init__(self, attributes, nodes):
        super(attributes)
        child_nodes_ids = nodes

