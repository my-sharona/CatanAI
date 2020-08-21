import GameSession
import Player
import GameConstants as Consts
import Dice
from copy import deepcopy
from itertools import combinations


class Heuristic:
    """
    a superior class, creates an Heuristic object
    """
    def __init__(self, normalization: float = 1):
        self.norm = normalization

    def _calc(self, session: GameSession, player: Player) -> float:
        raise NotImplemented

    def value(self, session: GameSession, player: Player) -> float:
        for p in session.players():
            if p == player:
                player = p
                break
        return self._calc(session, player) * self.norm


class VictoryPoints(Heuristic):
    """A Heuristic based on the number of victory Points"""

    def __init__(self, normalization: float = 1 / Consts.WINNING_VP):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return player.vp()


class Harbors(Heuristic):
    """A Heuristic based on the number of Harbors owned"""

    def __init__(self, normalization: float = 1 / len(Consts.HARBOR_NODES.values())):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return len(player.harbors())


class GameWon(Heuristic):
    """A Heuristic based on winner of the game"""
    INF = 100000

    def _calc(self, session: GameSession, player: Player) -> float:
        if session.winner() is not None:
            return GameWon.INF if session.winner() == player else -GameWon.INF
        return 0


class Roads(Heuristic):
    """A Heuristic based on the number of Harbors owned"""

    def __init__(self, normalization: float = 1 / Consts.MAX_ROADS_PER_PLAYER):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return player.num_roads()


class Settlements(Heuristic):
    """A Heuristic based on the number of settlements owned"""

    def __init__(self, normalization: float = 1 / Consts.MAX_SETTLEMENTS_PER_PLAYER):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return player.num_settlements()


class AvoidThrow(Heuristic):
    """A Heuristic based on avoiding large hands"""

    def __init__(self, normalization: float = 1 / (Consts.MAX_CARDS_IN_HAND + 1)):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        res_size = player.resource_hand().size()
        if res_size > Consts.MAX_CARDS_IN_HAND:
            return Consts.MAX_CARDS_IN_HAND - res_size
        return 0


class Cities(Heuristic):
    """A Heuristic based on avoiding large hands"""

    def __init__(self, normalization: float = 1 / Consts.MAX_CITIES_PER_PLAYER):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return player.num_cities()


class DevCards(Heuristic):
    """A Heuristic based on collecting and using development cards"""

    def __init__(self, normalization: float = 1 / (Consts.NUM_DEVS + 1)):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return player.dev_hand().size() + 2 * player.used_dev_hand().size()


class ResourceDiversity(Heuristic):
    """A Heuristic based on preferring diversified hands"""

    def __init__(self, normalization: float = 1 / len(Consts.YIELDING_RESOURCES)):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        num_types = len(set([card for card in player.resource_hand()]))
        return num_types


class BuildInGoodPlaces(Heuristic):
    """A Heuristic based on preferring building on higher probabilities"""

    def __init__(self, normalization: float = 1 / 227.5):  # 227.5 is the bound
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        board = session.board()
        tiles_types = set()
        num_tiles = 0
        tiles_prob = 0
        for node in player.settlement_nodes():
            for tile in board.get_adj_tile_ids_to_node(node):
                num_tiles += 1
                tiles_types.add(board.hexes()[tile].resource())
                tiles_prob += Dice.PROBABILITIES[board.hexes()[tile].token()]
        return num_tiles * len(tiles_types) * tiles_prob


class EnoughResources(Heuristic):
    """A Heuristic based on preferring hands that can buy many Purchasables"""

    def __init__(self, normalization: float = 1 / 3):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        hand = player.resource_hand()
        road_score = 0.5
        settle_score = 1
        city_score = 1.5
        dev_card_score = 1
        score = 0

        if hand.contains(Consts.COSTS[Consts.PurchasableType.ROAD]):
            score += road_score
        if hand.contains(Consts.COSTS[Consts.PurchasableType.SETTLEMENT]):
            score += settle_score
        if hand.contains(Consts.COSTS[Consts.PurchasableType.CITY]):
            score += city_score
        if hand.contains(Consts.COSTS[Consts.PurchasableType.DEV_CARD]):
            score += dev_card_score

        return score


class PreferResourcesPerStage(Heuristic):
    """A Heuristic that gives priority for having bricks and woods in the
    the early stages of the game and having sheep, ore and wheat in
    the advanced phase of the game."""

    def __init__(self, normalization: float = 1 / 150):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        # resources:
        __num_forest = player.resource_hand().cards_of_type(Consts.ResourceType.FOREST).size()
        __num_bricks = player.resource_hand().cards_of_type(Consts.ResourceType.BRICK).size()
        __num_sheep = player.resource_hand().cards_of_type(Consts.ResourceType.SHEEP).size()
        __num_wheat = player.resource_hand().cards_of_type(Consts.ResourceType.WHEAT).size()
        __num_ore = player.resource_hand().cards_of_type(Consts.ResourceType.ORE).size()

        # buildings:
        __num_roads = player.num_roads()
        __num_cities = player.num_cities()
        __num_settles = player.num_settlements()
        __num_buildings = __num_roads + __num_settles + __num_cities

        __calc_score = (100 * (0.8 * __num_forest +
                               1.2 * __num_bricks +
                               0.3 * __num_sheep +
                               0.3 * __num_wheat) /
                        (__num_buildings * (1 +
                                            0.75 * __num_sheep +
                                            0.75 * __num_wheat +
                                            1.5 * __num_ore)))
        return __calc_score


class Probability(Heuristic):
    """A Heuristic based on board probabilities and buildable placements"""

    def _calc(self, session: GameSession, player: Player) -> float:
        return sum((session.board().probability_score(player),
                    session.board().expectation_score(player),
                    session.potential_probability_score(player)))


class LongestRoad(Heuristic):
    """A Heuristic based on longest road length"""

    def __init__(self, normalization: float = 1 / Consts.MAX_ROADS_PER_PLAYER):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return session.board().road_len(player)


class OpponentScore(Heuristic):
    """A Heuristic based on max opponent score"""

    def __init__(self, normalization=1):
        super().__init__(normalization)
        self.vp = VictoryPoints()
        self.hand_size = HandSize()
        self.road = LongestRoad()

    def _calc(self, session: GameSession, player: Player) -> float:
        max_vp_player = max([p for p in session.players() if p != player], key=lambda p: p.vp())
        opp_score = (self.hand_size.value(session, max_vp_player) +
                     10 * self.vp.value(session, max_vp_player) +
                     1.5 * self.road.value(session, max_vp_player))
        return (1 / opp_score) if opp_score != 0 else 0


class CanBuy(Heuristic):
    """A Heuristic based on Purchasable buying power"""

    def __init__(self, normalization: float = 1 / 15):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        num_affordable = 0
        my_hand = player.resource_hand()
        contained = False
        for purchasable, cost in Consts.COSTS.items():
            if my_hand.contains(cost):
                contained = True
            if purchasable == Consts.PurchasableType.SETTLEMENT:
                reward = 1
            elif purchasable == Consts.PurchasableType.CITY:
                reward = 2
            else:
                reward = 0.5
            partial = reward / cost.size()
            my_hand_cards = [c for c in my_hand]
            for card in cost:
                if card in my_hand_cards:
                    num_affordable += partial
            cost_copy = deepcopy(cost)
            cost_copy.insert(cost)
            if my_hand.contains(cost_copy):
                num_affordable += 2 * reward

        # if contained:
        #     contained = False
        #     for purch1, purch2 in combinations(Consts.PurchasableType, 2):
        #         tot_cost = deepcopy(Consts.COSTS[purch1])
        #         tot_cost.insert(Consts.COSTS[purch2])
        #         if my_hand.contains(tot_cost):
        #             contained = True
        #             num_affordable += 2
        # if contained:
        #     for purch1, purch2, purch3 in combinations(Consts.PurchasableType, 3):
        #         tot_cost = deepcopy(Consts.COSTS[purch1])
        #         tot_cost.insert(Consts.COSTS[purch2])
        #         tot_cost.insert(Consts.COSTS[purch3])
        #         if my_hand.contains(tot_cost):
        #             num_affordable += 3
        return num_affordable


class HandSize(Heuristic):
    """A Heuristic based on preferring large hands up to threshold"""

    def __init__(self, normalization: float = 1 / Consts.MAX_CARDS_IN_HAND):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        return min(player.resource_hand_size(), Consts.MAX_CARDS_IN_HAND)


class HandDiversity(Heuristic):
    """A Heuristic based on preferring diverse hands"""

    def __init__(self, normalization: float = 1 / len(Consts.YIELDING_RESOURCES)):
        super().__init__(normalization)

    def _calc(self, session: GameSession, player: Player) -> float:
        num_unique_resources = 0
        for resource in Consts.ResourceType:
            if player.resource_hand().cards_of_type(resource).size() > 0:
                num_unique_resources += 1
        return num_unique_resources


class Everything(Heuristic):
    """A Heuristic based on multiple sub-heuristics"""
    def __init__(self, normalization=1, weights=(1, 30, 1.5, 1, 0.1, 0.1, 2.5, 1, 1)):
        super().__init__(normalization)
        self.heuristics = (Probability(),
                           VictoryPoints(),
                           LongestRoad(),
                           GameWon(),
                           HandSize(),
                           HandDiversity(),
                           DevCards(),
                           CanBuy(),
                           OpponentScore())
        self.weights = weights

    def _calc(self, session: GameSession, player: Player) -> float:
        return sum(h.value(session, player) * w for h, w in zip(self.heuristics, self.weights))


class Main(Heuristic):
    """A Heuristic based on multiple sub-heuristics"""
    VP_WEIGHT = 2  # victory points heuristic weight
    PREFER_RESOURCES_WEIGHT = 0.2
    HARBOURS_WEIGHT = 0.8
    DIVERSITY_WEIGHT = 0.5
    BUILD_IN_GOOD_PLACES_WEIGHT = 5
    ROADS_WEIGHT = 0.6
    SETTLES_WEIGHT = 0.7
    CITIES_WEIGHT = 2.5
    DEV_CARDS_WEIGHT = 2
    GAME_WON_WEIGHT = 1
    ENOUGH_RES_TO_BUY_WEIGHT = 1
    AVOID_THROW_WEIGHT = 0.01

    def __init__(self, normalization=1, weights=(VP_WEIGHT,
                                                 HARBOURS_WEIGHT,
                                                 PREFER_RESOURCES_WEIGHT,
                                                 ROADS_WEIGHT,
                                                 SETTLES_WEIGHT,
                                                 CITIES_WEIGHT,
                                                 DIVERSITY_WEIGHT,
                                                 BUILD_IN_GOOD_PLACES_WEIGHT,
                                                 DEV_CARDS_WEIGHT,
                                                 GAME_WON_WEIGHT,
                                                 ENOUGH_RES_TO_BUY_WEIGHT,
                                                 AVOID_THROW_WEIGHT)):
        super().__init__(normalization)
        self.heuristics = (VictoryPoints(),
                           Harbors(),
                           PreferResourcesPerStage(),
                           Roads(),
                           Settlements(),
                           Cities(),
                           ResourceDiversity(),
                           BuildInGoodPlaces(),
                           DevCards(),
                           GameWon(),
                           EnoughResources(),
                           AvoidThrow())
        self.weights = weights

    def _calc(self, session: GameSession, player: Player) -> float:
        return sum(h.value(session, player) * w for h, w in zip(self.heuristics, self.weights))


class BuilderCharacteristic(Main):
    BUILDER_WEIGHTS = (1, 0.01, 0.01, 1, 0.01, 1, 0.01, 1, 0.01, 1, 0.01, 0.01)

    def __init__(self, normalization=1, weights=BUILDER_WEIGHTS):
        super().__init__(normalization, weights)


class AmossComb1(Main):
    COMB1_WEIGHTS = (Main.VP_WEIGHT,
                     0.01,
                     0.01,
                     Main.ROADS_WEIGHT,
                     0.01,
                     Main.CITIES_WEIGHT,
                     0.01,
                     Main.BUILD_IN_GOOD_PLACES_WEIGHT,
                     Main.DEV_CARDS_WEIGHT,
                     Main.GAME_WON_WEIGHT,
                     0.01,
                     Main.AVOID_THROW_WEIGHT)

    def __init__(self, normalization=1, weights=COMB1_WEIGHTS):
        super().__init__(normalization, weights)


class AmossComb2(Main):
    COMB2_WEIGHTS = (Main.VP_WEIGHT,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     Main.BUILD_IN_GOOD_PLACES_WEIGHT,
                     Main.DEV_CARDS_WEIGHT,
                     Main.GAME_WON_WEIGHT,
                     0.01,
                     0.01)

    def __init__(self, normalization=1, weights=COMB2_WEIGHTS):
        super().__init__(normalization, weights)


class AmossComb3(Main):
    COMB3_WEIGHTS = (Main.VP_WEIGHT,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     Main.DIVERSITY_WEIGHT,
                     Main.BUILD_IN_GOOD_PLACES_WEIGHT,
                     0.01,
                     Main.GAME_WON_WEIGHT,
                     0.01,
                     Main.AVOID_THROW_WEIGHT)

    def __init__(self, normalization=1, weights=COMB3_WEIGHTS):
        super().__init__(normalization, weights)


class AmossComb4(Main):
    COMB4_WEIGHTS = (Main.VP_WEIGHT,
                     0.01,
                     Main.PREFER_RESOURCES_WEIGHT,
                     0.01,
                     0.01,
                     0.01,
                     0.01,
                     Main.BUILD_IN_GOOD_PLACES_WEIGHT,
                     Main.DEV_CARDS_WEIGHT,
                     Main.GAME_WON_WEIGHT,
                     0.01,
                     Main.AVOID_THROW_WEIGHT)

    def __init__(self, normalization=1, weights=COMB4_WEIGHTS):
        super().__init__(normalization, weights)


def find_sim_player(session: GameSession, player: Player) -> Player:
    # find the player's turn for the current session simulation
    for sim_player in session.players():
        if sim_player.get_id() == player.get_id():
            return sim_player
