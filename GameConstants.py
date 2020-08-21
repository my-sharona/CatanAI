from enum import Enum
from Hand import Hand
from typing import Union

"""A Module containing all constants in the Settlers of Catan game"""


class ResourceType(Enum):
    FOREST = 1
    ORE = 2
    BRICK = 3
    SHEEP = 4
    WHEAT = 5
    DESERT = 6
    ANY = 7  # this is used by general harbors
    UNKNOWN = 8  # used for mock playing moves with non-deterministic outcomes

    def __str__(self):
        return self.name


YIELDING_RESOURCES = [ResourceType.FOREST,
                      ResourceType.ORE,
                      ResourceType.BRICK,
                      ResourceType.SHEEP,
                      ResourceType.WHEAT]


class DevType(Enum):
    KNIGHT = 1
    VP = 2
    MONOPOLY = 3
    YEAR_OF_PLENTY = 4
    ROAD_BUILDING = 5
    UNKNOWN = 6

    def __str__(self):
        return self.name


HARBOR_NODES = {
    ResourceType.SHEEP: [0x5a, 0x6b],
    ResourceType.ORE: [0x25, 0x34],
    ResourceType.BRICK: [0xc9, 0xda],
    ResourceType.FOREST: [0xa5, 0xb6],
    ResourceType.WHEAT: [0x43, 0x52],
    ResourceType.ANY: [0x72, 0x83, 0x27, 0x38, 0x9c, 0xad, 0xcd, 0xdc]
}

DECK_TRADE_RATIO = 4
GENERAL_HARBOR_TRADE_RATIO = 3
RESOURCE_HARBOR_TRADE_RATIO = 2
NUM_RESOURCES_PER_CITY = 2
NUM_RESOURCES_PER_SETTLEMENT = 1
YOP_NUM_RESOURCES = 2
ROAD_BUILDING_NUM_ROADS = 2
ROBBER_DICE_VALUE = 7
MAX_CARDS_IN_HAND = 7
MAX_SETTLEMENTS_PER_PLAYER = 5
MAX_CITIES_PER_PLAYER = 4
MAX_ROADS_PER_PLAYER = 15
MAX_PLAYERS = 4
MIN_PLAYERS = 3
MIN_LARGEST_ARMY_SIZE = 3
MIN_LONGEST_ROAD_SIZE = 5
WINNING_VP = 10
VP_LARGEST_ARMY = 2
VP_LONGEST_ROAD = 2
VP_DEV_CARD = 1  # only for VP dev card
VP_SETTLEMENT = 1
VP_CITY = 2
VP_ROAD = 0  # in case we want a version where roads also have vp


class CatanExpansion(Enum):
    BASIC = 1
    SEAFARERS = 2


CATAN = CatanExpansion.BASIC  # support for other versions to come in the future

TOKEN_ORDER = []
HEX_COUNTS = {}
RESOURCE_COUNTS = {}
DEV_COUNTS = {}

if CATAN == CatanExpansion.BASIC:
    TOKEN_ORDER = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]

    HEX_COUNTS = {
        ResourceType.ORE: 3,
        ResourceType.BRICK: 3,
        ResourceType.WHEAT: 4,
        ResourceType.SHEEP: 4,
        ResourceType.FOREST: 4,
        ResourceType.DESERT: 1
    }

    RESOURCE_COUNTS = {
        ResourceType.ORE: 19,
        ResourceType.BRICK: 19,
        ResourceType.WHEAT: 19,
        ResourceType.SHEEP: 19,
        ResourceType.FOREST: 19
    }

    DEV_COUNTS = {
        DevType.KNIGHT: 14,
        DevType.VP: 5,
        DevType.MONOPOLY: 2,
        DevType.YEAR_OF_PLENTY: 2,
        DevType.ROAD_BUILDING: 2
    }

HEX_DECK = []
for resource, amount in HEX_COUNTS.items():
    HEX_DECK.extend([resource for _ in range(amount)])

NUM_HEXES = len(HEX_DECK)

RES_DECK = []
for resource, amount in RESOURCE_COUNTS.items():
    RES_DECK.extend([resource for _ in range(amount)])

NUM_RESOURCES = len(RES_DECK)

DEV_DECK = []
for dev_type, amount in DEV_COUNTS.items():
    DEV_DECK.extend([dev_type for _ in range(amount)])

NUM_DEVS = len(DEV_DECK)

# make sure that we have a token for each hex that is not a desert
assert NUM_HEXES - HEX_COUNTS.get(ResourceType.DESERT, 0) == len(TOKEN_ORDER)


class PurchasableType(Enum):
    SETTLEMENT = 1
    CITY = 2
    ROAD = 3
    DEV_CARD = 4

    def __str__(self):
        return self.name


BUILDABLES = [PurchasableType.SETTLEMENT,
              PurchasableType.CITY,
              PurchasableType.ROAD]

CardType = Union[DevType, ResourceType]

COSTS = {
    PurchasableType.DEV_CARD: Hand(ResourceType.ORE,
                                   ResourceType.SHEEP,
                                   ResourceType.WHEAT),

    PurchasableType.SETTLEMENT: Hand(ResourceType.WHEAT,
                                     ResourceType.SHEEP,
                                     ResourceType.FOREST,
                                     ResourceType.BRICK),

    PurchasableType.CITY: Hand(ResourceType.WHEAT,
                               ResourceType.WHEAT,
                               ResourceType.ORE,
                               ResourceType.ORE,
                               ResourceType.ORE),

    PurchasableType.ROAD: Hand(ResourceType.BRICK,
                               ResourceType.FOREST)
}
