import GameConstants as Consts
import Hand
import Player


class Buildable:
    """Class representing a buildable object in Catan (City, Settlement, Road, etc.)"""
    def __init__(self, player: Player, coord: int, btype: Consts.PurchasableType):
        self.__player = player
        self.__coord = coord
        if btype not in Consts.BUILDABLES:
            raise ValueError(f'cannot build {btype}')
        self.__type = btype

    def player(self) -> Player:
        """:returns Player that owns this buildable"""
        return self.__player

    def coord(self) -> int:
        """:returns hexgrid coordinate this buildable is built at"""
        return self.__coord

    def cost(self) -> Hand:
        """:returns a Hand representing the cards needed to buy this buildable"""
        return Consts.COSTS[self.type()]

    def type(self) -> Consts.PurchasableType:
        """:returns PurchasableType Enum type of this buildable"""
        return self.__type

    def info(self) -> str:
        """:returns an informative string about this buildable"""
        return f'[{self.type().name}] node_id = {hex(self.coord())}, player = {self.player()}'

    def __str__(self):
        return f'{self.type()} at {hex(self.coord())} belonging to player {self.player()}'
