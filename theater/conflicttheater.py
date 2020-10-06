import json
import typing

import dcs
from dcs.mapping import Point
from dcs.terrain import caucasus, persiangulf, nevada, normandy, thechannel, syria

from .controlpoint import ControlPoint
from .landmap import poly_contains, load_landmap

SIZE_TINY = 150
SIZE_SMALL = 600
SIZE_REGULAR = 1000
SIZE_BIG = 2000
SIZE_LARGE = 3000

IMPORTANCE_LOW = 1
IMPORTANCE_MEDIUM = 1.2
IMPORTANCE_HIGH = 1.4

"""
ALL_RADIALS = [0, 45, 90, 135, 180, 225, 270, 315, ]
COAST_NS_E = [45, 90, 135, ]
COAST_EW_N = [315, 0, 45, ]
COAST_NSEW_E = [225, 270, 315, ]
COAST_NSEW_W = [45, 90, 135, ]

COAST_NS_W = [225, 270, 315, ]
COAST_EW_S = [135, 180, 225, ]
"""

LAND = [0, 45, 90, 135, 180, 225, 270, 315, ]

COAST_V_E = [0, 45, 90, 135, 180]
COAST_V_W = [180, 225, 270, 315, 0]

COAST_A_W = [315, 0, 45, 135, 180, 225, 270]
COAST_A_E = [0, 45, 90, 135, 180, 225, 315]

COAST_H_N = [270, 315, 0, 45, 90]
COAST_H_S = [90, 135, 180, 225, 270]

COAST_DL_E = [45, 90, 135, 180, 225]
COAST_DL_W = [225, 270, 315, 0, 45]
COAST_DR_E = [315, 0, 45, 90, 135]
COAST_DR_W = [135, 180, 225, 315]


class ConflictTheater:
    terrain = None  # type: dcs.terrain.Terrain
    controlpoints = None  # type: typing.List[ControlPoint]

    reference_points = None  # type: typing.Dict
    overview_image = None  # type: str
    landmap = None  # type: landmap.Landmap
    """
    land_poly = None  # type: Polygon
    """
    daytime_map = None  # type: typing.Dict[str, typing.Tuple[int, int]]

    def __init__(self):
        self.controlpoints = []
        """
        self.land_poly = geometry.Polygon(self.landmap[0][0])
        for x in self.landmap[1]:
            self.land_poly = self.land_poly.difference(geometry.Polygon(x))
        """

    def add_controlpoint(self, point: ControlPoint, connected_to: [ControlPoint] = []):
        for connected_point in connected_to:
            point.connect(to=connected_point)

        self.controlpoints.append(point)

    def find_ground_objects_by_obj_name(self, obj_name):
        found = []
        for cp in self.controlpoints:
            for g in cp.ground_objects:
                if g.obj_name == obj_name:
                    found.append(g)
        return found

    def is_in_sea(self, point: Point) -> bool:
        if not self.landmap:
            return False

        for inclusion_zone in self.landmap[0]:
            if poly_contains(point.x, point.y, inclusion_zone):
                return False

        return True

    def is_on_land(self, point: Point) -> bool:
        if not self.landmap:
            return True

        is_point_included = False
        for inclusion_zone in self.landmap[0]:
            if poly_contains(point.x, point.y, inclusion_zone):
                is_point_included = True

        if not is_point_included:
            return False

        for exclusion_zone in self.landmap[1]:
            if poly_contains(point.x, point.y, exclusion_zone):
                return False

        return True

    def player_points(self) -> typing.Collection[ControlPoint]:
        return [point for point in self.controlpoints if point.captured]

    def conflicts(self, from_player=True) -> typing.Collection[typing.Tuple[ControlPoint, ControlPoint]]:
        for cp in [x for x in self.controlpoints if x.captured == from_player]:
            for connected_point in [x for x in cp.connected_points if x.captured != from_player]:
                yield (cp, connected_point)

    def enemy_points(self) -> typing.Collection[ControlPoint]:
        return [point for point in self.controlpoints if not point.captured]

    def add_json_cp(self, theater, p: dict) -> ControlPoint:

        if p["type"] == "airbase":

            airbase = theater.terrain.airports[p["id"]].__class__

            if "radials" in p.keys():
                radials = p["radials"]
            else:
                radials = LAND

            if "size" in p.keys():
                size = p["size"]
            else:
                size = SIZE_REGULAR

            if "importance" in p.keys():
                importance = p["importance"]
            else:
                importance = IMPORTANCE_MEDIUM

            cp = ControlPoint.from_airport(airbase, radials, size, importance)
        elif p["type"] == "carrier":
            cp = ControlPoint.carrier("carrier", Point(p["x"], p["y"]), p["id"])
        else:
            cp = ControlPoint.lha("lha", Point(p["x"], p["y"]), p["id"])

        if "captured_invert" in p.keys():
            cp.captured_invert = p["captured_invert"]
        else:
            cp.captured_invert = False

        return cp

    @staticmethod
    def from_file(filename):
        with open(filename, "r") as content:
            json_data = json.loads(content.read())


            theaters = {
                "Caucasus": CaucasusTheater,
                "Nevada": NevadaTheater,
                "Persian Gulf": PersianGulfTheater,
                "Normandy": NormandyTheater,
                "The Channel": TheChannelTheater,
                "Syria": SyriaTheater,
            }
            theater = theaters[json_data["theater"]]
            t = theater()
            cps = {}

            for p in json_data["player_points"]:
                cp = t.add_json_cp(theater, p)
                cp.captured = True
                cps[p["id"]] = cp
                t.add_controlpoint(cp)

            for p in json_data["enemy_points"]:
                cp = t.add_json_cp(theater, p)
                cps[p["id"]] = cp
                t.add_controlpoint(cp)

            for l in json_data["links"]:
                cps[l[0]].connect(cps[l[1]])
                cps[l[1]].connect(cps[l[0]])

            return t


class CaucasusTheater(ConflictTheater):
    terrain = caucasus.Caucasus()
    overview_image = "caumap.gif"
    reference_points = {(-317948.32727306, 635639.37385346): (278.5 * 4, 319 * 4),
                        (-355692.3067714, 617269.96285781): (263 * 4, 352 * 4), }

    landmap = load_landmap("resources\\caulandmap.p")
    daytime_map = {
        "dawn": (6, 9),
        "day": (9, 18),
        "dusk": (18, 20),
        "night": (0, 5),
    }


class PersianGulfTheater(ConflictTheater):
    terrain = dcs.terrain.PersianGulf()
    overview_image = "persiangulf.gif"
    reference_points = {
        (persiangulf.Shiraz_International_Airport.position.x, persiangulf.Shiraz_International_Airport.position.y): (
        772, -1970),
        (persiangulf.Liwa_Airbase.position.x, persiangulf.Liwa_Airbase.position.y): (1188, 78), }
    landmap = load_landmap("resources\\gulflandmap.p")
    daytime_map = {
        "dawn": (6, 8),
        "day": (8, 16),
        "dusk": (16, 18),
        "night": (0, 5),
    }


class NevadaTheater(ConflictTheater):
    terrain = dcs.terrain.Nevada()
    overview_image = "nevada.gif"
    reference_points = {(nevada.Mina_Airport_3Q0.position.x, nevada.Mina_Airport_3Q0.position.y): (45 * 2, -360 * 2),
                        (nevada.Laughlin_Airport.position.x, nevada.Laughlin_Airport.position.y): (440 * 2, 80 * 2), }
    landmap = load_landmap("resources\\nev_landmap.p")
    daytime_map = {
        "dawn": (4, 6),
        "day": (6, 17),
        "dusk": (17, 18),
        "night": (0, 5),
    }


class NormandyTheater(ConflictTheater):
    terrain = dcs.terrain.Normandy()
    overview_image = "normandy.gif"
    reference_points = {(normandy.Needs_Oar_Point.position.x, normandy.Needs_Oar_Point.position.y): (-170, -1000),
                        (normandy.Evreux.position.x, normandy.Evreux.position.y): (2020, 500)}
    landmap = load_landmap("resources\\normandylandmap.p")
    daytime_map = {
        "dawn": (6, 8),
        "day": (10, 17),
        "dusk": (17, 18),
        "night": (0, 5),
    }


class TheChannelTheater(ConflictTheater):
    terrain = dcs.terrain.TheChannel()
    overview_image = "thechannel.gif"
    reference_points = {(thechannel.Abbeville_Drucat.position.x, thechannel.Abbeville_Drucat.position.y): (2400, 4100),
                        (thechannel.Detling.position.x, thechannel.Detling.position.y): (1100, 2000)}
    landmap = load_landmap("resources\\channellandmap.p")
    daytime_map = {
        "dawn": (6, 8),
        "day": (10, 17),
        "dusk": (17, 18),
        "night": (0, 5),
    }


class SyriaTheater(ConflictTheater):
    terrain = dcs.terrain.Syria()
    overview_image = "syria.gif"
    reference_points = {(syria.Eyn_Shemer.position.x, syria.Eyn_Shemer.position.y): (1300, 1380),
                        (syria.Tabqa.position.x, syria.Tabqa.position.y): (2060, 570)}
    landmap = load_landmap("resources\\syrialandmap.p")
    daytime_map = {
        "dawn": (6, 8),
        "day": (8, 16),
        "dusk": (16, 18),
        "night": (0, 5),
    }
