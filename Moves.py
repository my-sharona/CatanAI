from __future__ import annotations
import GameConstants as Consts
import Player
import Hand
from enum import Enum
from typing import Union


class MoveType(Enum):
    """Enum representing different move types"""
    TRADE = 1
    BUY_DEV = 2
    USE_DEV = 3
    BUILD = 4
    THROW = 5
    PASS = 6
    
    def __str__(self):
        return self.name


class Move:
    """Class representing a possible action that a player can perform in Catan"""
    def __init__(self, player: Player, mtype: MoveType):
        self.__player = player
        self.__type = mtype

    def set_player(self, player: Player) -> None:
        """sets the player making the move"""
        self.__player = player

    def player(self) -> Player:
        """:returns the id of the player making the move"""
        return self.__player
    
    def get_type(self) -> MoveType:
        """:returns the type of move as a MoveType enum"""
        return self.__type

    def info(self) -> str:
        """:returns an informative string about this move"""
        return f'[MOVE] player = {self.player()}, type = {self.get_type().name}'

    def __str__(self) -> str:
        return str(self.__type)

    def __eq__(self, other):
        return isinstance(other, Move) and self.player() == other.player() and self.get_type() == other.get_type()


class TradeMove(Move):
    """A Move that trades cards with the main deck"""
    def __init__(self, player: Player, cards_out: Hand, cards_in: Hand):
        super().__init__(player, MoveType.TRADE)
        self.__cards_out = cards_out
        self.__cards_in = cards_in

    def gives(self) -> Hand:
        """:returns cards to be given away by the player (as a Hand object)"""
        return self.__cards_out

    def gets(self) -> Hand:
        """:returns cards to be obtained by the player (as a Hand object)"""
        return self.__cards_in

    def info(self) -> str:
        """:returns an informative string about this trade move"""
        return f'[MOVE] player = {self.player()}, ' \
               f'type = {self.get_type().name}, gives = {self.gives()}, gets = {self.gets()}'

    def __eq__(self, other):
        return isinstance(other, TradeMove) and self.gives() == other.gives() and self.gets() == other.gets()


class BuyDevMove(Move):
    """A Move that buys a development card"""
    def __init__(self, player: Player):
        super().__init__(player, MoveType.BUY_DEV)


class UseDevMove(Move):
    """A Move that uses a development card"""
    def __init__(self, player: Player, dtype: Consts.DevType):
        super().__init__(player, MoveType.USE_DEV)
        self.__dev_to_use = dtype

    def uses(self) -> Consts.DevType:
        """:returns the dev card to be used as a DevType enum"""
        return self.__dev_to_use

    def info(self) -> str:
        """:returns an informative string about this Use Dev card move"""
        return f'[MOVE] player = {self.player()}, type = {self.get_type().name}, uses = {self.uses().name}'

    def __eq__(self, other):
        return isinstance(other, UseDevMove) and self.player() == other.player() and self.uses() == other.uses()


class UseRoadBuildingDevMove(UseDevMove):
    """A Move that uses a Road Building Development Card"""
    def __init__(self, player: Player):
        super().__init__(player, Consts.DevType.ROAD_BUILDING)


class UseYopDevMove(UseDevMove):
    """A Move that uses a Year of Plenty Development Card"""
    def __init__(self, player: Player, *resources: Consts.ResourceType):
        super().__init__(player, Consts.DevType.YEAR_OF_PLENTY)
        self.__resources = Hand.Hand(*resources)
        assert len(resources) == Consts.YOP_NUM_RESOURCES

    def resources(self) -> Hand:
        return self.__resources

    def __eq__(self, other):
        return isinstance(other, UseYopDevMove) and self.player() == other.player() and \
               self.resources() == other.resources()


class UseMonopolyDevMove(UseDevMove):
    """A Move that uses a Monopoly Development Card"""
    def __init__(self, player: Player, resource: Consts.ResourceType):
        super().__init__(player, Consts.DevType.MONOPOLY)
        self.__resource = resource

    def resource(self) -> Consts.ResourceType:
        return self.__resource

    def __eq__(self, other):
        return isinstance(other, UseDevMove) and self.player() == other.player() and \
               self.resource() == other.resource()


class UseKnightDevMove(UseDevMove):
    """A Move that uses a Knight Development Card / displaces the Robber when activated"""
    def __init__(self, player: Player, hex_id: int, opp: Union[Player, None],
                 robber_activated: bool = False):
        super().__init__(player, Consts.DevType.KNIGHT)
        self.__hex_id = hex_id
        self.__opp = opp
        self.__robber = robber_activated

    def robber_activated(self) -> bool:
        """:returns True iff this move is actuated because of a Robber Activation (vs a Knight Dev)"""
        return self.__robber

    def hex_id(self) -> int:
        """:returns the hex id to place robber"""
        return self.__hex_id

    def take_from(self) -> Union[Player, None]:
        """:returns the player from which to take a card (from the vicinity of the robber hex)"""
        return self.__opp

    def info(self) -> str:
        """:returns an informative string about this move"""
        return f'[MOVE] player = {self.player()}, ' \
               f'type = {self.get_type().name}, ' \
               f'places robber at hex = {self.hex_id()}, takes card from = {self.take_from()}'

    def __eq__(self, other):
        return isinstance(other, UseKnightDevMove) and self.player() == other.player() and \
               self.hex_id() == other.hex_id() and self.take_from() == other.take_from() and \
               self.robber_activated() == other.robber_activated()


class ThrowMove(Move):
    """A Move that throws a card from the player's hand"""
    def __init__(self, player: Player, hand: Hand):
        super().__init__(player, MoveType.THROW)
        self.__hand = hand

    def throws(self) -> Hand:
        """:returns card to throw as a Hand object"""
        return self.__hand

    def info(self) -> str:
        """:returns an informative string about this throw move"""
        return f'[MOVE] player = {self.player()}, type = {self.get_type()}, throws = {self.throws()}'

    def __eq__(self, other):
        return isinstance(other, ThrowMove) and self.player() == other.player() and \
               self.throws() == other.throws()


class BuildMove(Move):
    """A Move that builds a Buildable on the board"""
    def __init__(self, player: Player, btype: Consts.PurchasableType, location: int, free: bool = False):
        super().__init__(player, MoveType.BUILD)
        self.__to_build = btype
        self.__loc = location
        self.__is_free = free

    def is_free(self) -> bool:
        """:returns True iff buildable can be placed without cost for the player"""
        return self.__is_free

    def builds(self) -> Consts.PurchasableType:
        """:returns the building type as a PurchasableType enum"""
        return self.__to_build

    def at(self) -> int:
        """:returns int value of node / edge idx of location to build on the board (see HexGrid)"""
        return self.__loc

    def info(self) -> str:
        """:returns an informative string about this build move"""
        return f'[MOVE] player = {self.player()}, ' \
               f'type = {self.get_type().name}, builds = {self.builds().name}, at = {hex(self.at())}'

    def __eq__(self, other):
        return isinstance(other, BuildMove) and self.player() == other.player() and \
               self.builds() == other.builds() and self.at() == other.at() and self.is_free() == other.is_free()
