import GameConstants as Consts
import hexgrid
from typing import List


class Colors:

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    TEAL = '\033[96m'
    GREEN = '\033[32m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    WHITE = '\033[35m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def colorify(st):
    colors = {
        'FOREST': Colors.GREEN,
        'SHEEP': Colors.TEAL,
        'WHEAT': Colors.WARNING,
        'BRICK': Colors.FAIL,
        'DESERT': Colors.WHITE,
        'ORE': Colors.OKBLUE
    }
    return colors[str(st)] + str(st) + Colors.ENDC


class HexTile:
    """
    Class represents a tile in the hexgrid (board)
    """
    def __init__(self, hex_id: int, resource: Consts.ResourceType, token: int, has_robber: bool = False):
        self.__hex_id = hex_id
        self.__resource = resource
        self.__token = token
        self.__has_robber = has_robber

    def resource(self) -> Consts.ResourceType:
        return self.__resource

    def id(self) -> int:
        return self.__hex_id

    def coord(self) -> int:
        """:returns coordinate of this hex tile, *this is not the same as hex id* (see hexgrid)"""
        return hexgrid.tile_id_to_coord(self.__hex_id + 1)

    def edges(self) -> List[int]:
        """:returns list of this tile's edge coordinates"""
        return hexgrid.edges_touching_tile(self.__hex_id + 1)

    def nodes(self) -> List[int]:
        """:returns list of this tile's node coordinates"""
        return hexgrid.nodes_touching_tile(self.__hex_id + 1)

    def token(self) -> int:
        return self.__token if self.__token is not None else ''

    def has_robber(self) -> bool:
        return self.__has_robber

    def set_robber(self, val: bool) -> None:
        self.__has_robber = val

    def info(self) -> str:
        return f'[HEX] resource = {self.__resource:>8}, ' \
               f'hex_id = {hex(self.__hex_id):>5}, token = {self.__token:2}, robber ? {self.__has_robber}'

    def __str__(self):
        return colorify(self.__resource)

    def __repr__(self):
        return colorify(self.__resource)
