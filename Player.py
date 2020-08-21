from __future__ import annotations
from typing import Set, List, Tuple
import Buildable
import Hand
import Moves
import GameConstants as Consts
import GameSession
import Agent


class Player:
    """
    Class represents a player in the game,
    and holds the info of the current player
    """
    ID_GEN = 0

    def __init__(self, agent: Agent.Agent, name: str = None):
        self.__agent = agent
        self.__id = self.__gen_id()
        self.__name = self.__gen_name(name)
        self.__resources_hand = Hand.Hand()
        self.__devs_hand = Hand.Hand()
        self.__used_devs = Hand.Hand()
        self.__settlement_nodes = []
        self.__city_nodes = []
        self.__road_edges = []
        self.__has_longest_road = False
        self.__has_largest_army = False
        self.__longest_road_len = 0
        self.__harbors = set()

    def vp(self) -> int:
        """
        :return: current number of victory points
        """
        vp = 0
        if self.has_largest_army():
            vp += Consts.VP_LARGEST_ARMY
        if self.has_longest_road():
            vp += Consts.VP_LONGEST_ROAD
        vp += self.num_settlements() * Consts.VP_SETTLEMENT
        vp += self.num_cities() * Consts.VP_CITY
        vp += self.num_roads() * Consts.VP_ROAD  # just in case
        vp += len([dev_card for dev_card in self.__devs_hand if
                   dev_card == Consts.DevType.VP]) * Consts.VP_DEV_CARD
        return vp

    def used_dev_hand(self) -> Hand:
        """
        :return: Hand object, represents the development cards
        that has been used by the player
        """
        return self.__used_devs

    def agent(self) -> Agent.Agent:
        """"
        :return: the current heuristic the player is using
        """
        return self.__agent

    def remove_settlement(self, node: int) -> None:
        """
        removes a settlement from the player's settlements
        :param node: the hex number represents
         the node of the settlements to be removed
        :return: None
        """
        self.settlement_nodes().remove(node)

    def harbor_resources(self) -> List[Consts.ResourceType]:
        """
        :return: the resources types that can be traded by the player
        """
        resources = []
        yielding_nodes = self.city_nodes() + self.settlement_nodes()
        for resource, locations in Consts.HARBOR_NODES.items():
            if any(n in locations for n in yielding_nodes):
                resources.append(resource)
                continue
        return resources

    def settlement_nodes(self) -> List[int]:
        """
        :return: the nodes in which the player has settlements
        """
        return self.__settlement_nodes

    def city_nodes(self) -> List[int]:
        """
        :return: the nodes in which the player has cities

        """
        return self.__city_nodes

    def road_edges(self) -> List[int]:
        """
        :return: the edges in which the player has road
        """
        return self.__road_edges

    def get_id(self) -> int:
        """
        :return: this player's player id
        """
        return self.__id

    def has_longest_road(self) -> bool:
        """
        :return: True iff player currently has the longest road
        """
        return self.__has_longest_road

    def has_largest_army(self) -> bool:
        """
        :return: True iff player currently has the largest army
        """
        return self.__has_largest_army

    def resource_hand(self) -> Hand.Hand:
        """
        :return: the resources the player has currently in hand
        """
        return self.__resources_hand

    def dev_hand(self) -> Hand.Hand:
        """
        :return: the unused development cards the player has currently in hand
        """
        return self.__devs_hand

    def num_settlements(self) -> int:
        """
        :return: current number of settlements player has on the board (0-5)
        """
        num_settles = len(self.__settlement_nodes)
        assert 0 <= num_settles <= Consts.MAX_SETTLEMENTS_PER_PLAYER
        return num_settles

    def num_cities(self) -> int:
        """
        :return: current number of cities player has on the board (0-4)
        """
        num_cities = len(self.__city_nodes)
        assert 0 <= num_cities <= Consts.MAX_CITIES_PER_PLAYER
        return num_cities

    def harbors(self) -> List[Consts.ResourceType]:
        """
        :return: current number of harbor nodes player has on the board (0-9)
        """
        harbor_types = []
        for node in self.settlement_nodes() + self.city_nodes():
            for harbor_type, locations in Consts.HARBOR_NODES.items():
                if node in locations:
                    harbor_types.append(harbor_type)
                    break

        return harbor_types

    def num_roads(self) -> int:
        """
        :return: current number of roads player has on the board (0-15)
        """
        num_roads = len(self.__road_edges)
        assert 0 <= num_roads <= Consts.MAX_ROADS_PER_PLAYER
        return num_roads

    def army_size(self) -> int:
        """
        :return: number of knights played by player
        """
        return sum(1 for dev_card in self.__used_devs if
                   dev_card == Consts.DevType.KNIGHT)

    def resource_hand_size(self) -> int:
        """
        :return: number of resource cards player is holding
        """
        return len(self.__resources_hand)

    def dev_hand_size(self) -> int:
        """
        :return: number of development cards player is holding
        """
        return len(self.__devs_hand)

    def __gen_name(self, name: str) -> str:
        if name is None:
            return f'Player{self.get_id()}'
        return name

    @staticmethod
    def __gen_id() -> int:
        Player.ID_GEN += 1
        return Player.ID_GEN

    def info(self) -> str:
        """
        supplies important information about the current state of the player
        :return: None
        """
        return f'[PLAYER {self}] player_id = {self.get_id()}\n' \
               f'[PLAYER {self}] vp = {self.vp()}\n' \
               f'[PLAYER {self}] agent = {type(self.agent())}\n' \
               f'[PLAYER {self}] settlements = ' \
               f'{[hex(s) for s in self.__settlement_nodes]}\n' \
               f'[PLAYER {self}] cities = ' \
               f'{[hex(c) for c in self.__city_nodes]}\n' \
               f'[PLAYER {self}] roads = ' \
               f'{[hex(r) for r in self.__road_edges]}\n' \
               f'[PLAYER {self}] longest road = {self.__has_longest_road}\n' \
               f'[PLAYER {self}] largest army = {self.__has_largest_army}\n' \
               f'[PLAYER {self}] resources = {self.resource_hand()}\n' \
               f'[PLAYER {self}] devs = {self.__devs_hand}\n' \
               f'[PLAYER {self}] devs_used = {self.__used_devs}\n'

    # modifiers #
    def set_longest_road(self, val: bool) -> None:
        self.__has_longest_road = val

    def set_largest_army(self, val: bool) -> None:
        self.__has_largest_army = val

    def use_dev(self, dtype: Consts.DevType) -> None:
        """

        :param dtype: use a development card
        :return: None
        """
        if dtype not in self.__devs_hand:
            raise ValueError(
                f'player {self.get_id()} cannot use dev card {dtype}, no such '
                f'card in hand')
        else:
            used = Hand.Hand(dtype)
            self.__devs_hand.remove(used)
            self.__used_devs.insert(used)

    def receive_cards(self, cards: Hand.Hand) -> None:
        """
        adding a given Hand to the player's Hand
        :param cards: Hand object, the cards to be added to the player's Hand
        :return: None
        """
        res_cards = cards.resources()
        dev_cards = cards.devs()
        self.__resources_hand.insert(res_cards)
        self.__devs_hand.insert(dev_cards)

    def throw_cards(self, cards: Hand.Hand) -> None:
        """
        throwing cards out of the player's Hand
        :param cards: the cards to be thrown
        :return: None
        """
        self.__resources_hand.remove(cards)

    def add_buildable(self, buildable: Buildable.Buildable) -> None:
        """

        :param buildable:
        :return:
        """
        btype = buildable.type()
        if btype == Consts.PurchasableType.SETTLEMENT:
            buildable_coords = self.__settlement_nodes
        elif btype == Consts.PurchasableType.CITY:
            # self.__settlement_nodes.remove(buildable.coord())   # city
            # replaces existing settlement
            buildable_coords = self.__city_nodes
        else:
            buildable_coords = self.__road_edges
        buildable_coords.append(buildable.coord())

    # agent interface #
    def choose(self, moves: List[Moves.Move],
               state: GameSession.GameSession) -> Moves.Move:
        """new choosing interface, should be cleaner"""
        return self.__agent.choose(moves, self, state)

    def __eq__(self, other: Player) -> bool:
        if other is None:
            return False
        return self.get_id() == other.get_id()

    def __repr__(self) -> str:
        return self.__name

    def __hash__(self):
        return self.get_id()
