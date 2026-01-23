import abc
from src.osm_model.types import OsmNode, OsmWay
from src.compare import distance


class AbstractMatcher(abc.ABC):
    @abc.abstractmethod
    def check(self, item: OsmWay | OsmNode):
        raise NotImplementedError()

    @abc.abstractmethod
    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        raise NotImplementedError()

class TagsListMatcher(AbstractMatcher):
    def __init__(self, rule: list[str]):
        self.rule = rule

    def check(self, item: OsmWay | OsmNode):
        return all(item.has_tag(tag) for tag in self.rule)

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        return all(
            left.get_tag(tag) == right.get_tag(tag) for tag in self.rule
        )

class LocationMatcher(AbstractMatcher):
    def __init__(self, dist: int, engine = None, download_latlon: bool = True):
        self.dist = dist
        self.download_latlon = download_latlon
        self.engine = engine

    def check(self, item: OsmWay | OsmNode):
        if not item.has_loc() and self.download_latlon:
            item.download_lat_lon(engine=self.engine)

        return item.has_loc()

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        return distance(left.loc, right.loc) <= self.dist
