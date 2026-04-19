import abc
from src.osm_model.osm_types import OsmNode, OsmWay
from src.compare import distance


class AbstractMatcher(abc.ABC):
    @abc.abstractmethod
    def check(self, item: OsmWay | OsmNode):
        raise NotImplementedError()

    @abc.abstractmethod
    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        raise NotImplementedError()

    @abc.abstractmethod
    def __str__(self):
        raise NotImplementedError()


class TagsListMatcher(AbstractMatcher):
    def __init__(self, rule: list[str]):
        self.rule = rule

    def __str__(self):
        return f'TagsListMatcher({self.rule})'

    def check(self, item: OsmWay | OsmNode):
        return all(item.has_tag(tag) for tag in self.rule)

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        return all(
            left.get_tag(tag) == right.get_tag(tag) for tag in self.rule
        )

class LocationMatcher(AbstractMatcher):
    def __init__(self, dist: int, engine):
        self.dist = dist
        self.engine = engine

    def __str__(self):
        return f'LocationMatcher({self.dist}m)'

    def check(self, item: OsmWay | OsmNode):
        # if not item.has_loc() and self.download_latlon:
            # item.download_lat_lon(engine=self.engine)
        return item.has_loc()

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        return distance(left.loc, right.loc) <= self.dist

class NamesMatcher(AbstractMatcher):
    def __str__(self):
        return 'NamesMatcher()'

    def check(self, item: OsmWay | OsmNode):
        return item.has_tag('name') or item.has_tag('official_name') or item.has_tag('short_name')

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        left_names = {v for v in (
            left.get_tag('name'),
            left.get_tag('official_name'),
            left.get_tag('short_name'),
        ) if v}

        right_names = {v for v in (
            right.get_tag('name'),
            right.get_tag('official_name'),
            right.get_tag('short_name'),
        ) if v}

        left_names = {self._normalize(name) for name in left_names}
        right_names = {self._normalize(name) for name in right_names}

        return not left_names.isdisjoint(right_names)

    def _normalize(self, name: str) -> str:
        return name.strip().lower()

class AddressMatcher(AbstractMatcher):
    def __init__(self, single_in_city: bool):
        self.single_in_city = single_in_city

    def __str__(self):
        return f'AddressMatcher(single_in_city={self.single_in_city})'

    def check(self, item: OsmWay | OsmNode):
        return item.has_tag('addr:housenumber') and (item.has_tag('addr:street') or item.has_tag('addr:place')) and item.has_tag('addr:city') or \
                item.has_tag('addr:housenumber') and item.has_tag('addr:place')

    def compare(self, left: OsmWay | OsmNode, right: OsmWay | OsmNode):
        if self.single_in_city:
            if left.get_tag('addr:postcode') and right.get_tag('addr:postcode'):
                if left.get_tag('addr:postcode') == right.get_tag('addr:postcode'):
                    return True

            left_addr = f"{left.get_tag('addr:housenumber')} {left.get_tag('addr:city') or left.get_tag('addr:place')}"
            right_addr = f"{right.get_tag('addr:housenumber')} {right.get_tag('addr:city') or right.get_tag('addr:place')}"
            if self._normalize(left_addr) == self._normalize(right_addr):
                return True

        left_addr = f"{left.get_tag('addr:housenumber')} {left.get_tag('addr:street')} {left.get_tag('addr:city')}"
        right_addr = f"{right.get_tag('addr:housenumber')} {right.get_tag('addr:street')} {right.get_tag('addr:city')}"
        if self._normalize(left_addr) == self._normalize(right_addr):
            return True

        left_addr = f"{left.get_tag('addr:housenumber')} {left.get_tag('addr:place')} {left.get_tag('addr:city')}"
        right_addr = f"{right.get_tag('addr:housenumber')} {right.get_tag('addr:place')} {right.get_tag('addr:city')}"
        if self._normalize(left_addr) == self._normalize(right_addr):
            return True

        return False

    def _normalize(self, name: str) -> str:
        return name.strip().lower()
