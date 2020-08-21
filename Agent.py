from enum import Enum
import Moves as Moves
from Hand import Hand
from typing import List
from random import choice
from Heuristics import *
import Player
import GameSession
from copy import deepcopy


# import tensorflow as tf
# from keras.models import Sequential
# from keras.layers import Dense
# from DQN import get_move_predictions


class AgentType(Enum):
    """Enum representing Agent types"""
    RANDOM = 0
    HUMAN = 1
    ONE_MOVE = 2
    PROBABILITY = 3
    MONTECARLO = 4
    DQN = 5
    OPTIMIZED = 6

    def __str__(self):
        return self.name


class Agent:
    """Class representing an AI agent that can choose a move based on a strategy / AI paradigm"""
    ID_GEN = 0

    def __init__(self, agent_type: AgentType):
        Agent.ID_GEN += 1
        self.__id = Agent.ID_GEN
        self.__type = agent_type

    def type(self) -> AgentType:
        """:returns the Enum type of this agent"""
        return self.__type

    def id(self) -> int:
        """:returns the unique id of this agent instance"""
        return self.__id

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        """:returns a chosen move from moves"""
        raise NotImplemented

    def __str__(self):
        return str(self.type())


class RandomAgent(Agent):
    """An agent that makes (uniform) random move choices"""

    def __init__(self):
        super().__init__(AgentType.RANDOM)

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession):
        # choose uniformly between move TYPES first, then uniformly between moves within that type #
        available_move_types = list(set([m.get_type() for m in moves]))
        move_type = choice(available_move_types)
        filtered_moves = [m for m in moves if m.get_type() == move_type]

        if move_type == Moves.MoveType.BUILD:  # from build moves choose uniformly from buildables
            available_build_types = list(set([m.builds() for m in filtered_moves]))
            build_type = choice(available_build_types)
            filtered_moves = [m for m in filtered_moves if m.builds() == build_type]

        elif move_type == Moves.MoveType.USE_DEV:  # same for dev cards
            available_dev_types = list(set([m.uses() for m in filtered_moves]))
            dev_type = choice(available_dev_types)
            filtered_moves = [m for m in filtered_moves if m.uses() == dev_type]

        return choice(filtered_moves)


class HumanAgent(Agent):
    """An agent that chooses via human input (stdin)"""

    def __init__(self, name='human'):
        super().__init__(AgentType.HUMAN)
        self.__name = name

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        inpt = input('Player {}, choose move by index (or n = nodes map, e = edges map, b = board, m = moves list):'
                     '\n{}\n'.format(player, '\n'.join('{:3} - {}'.format(i, m.info()) for i, m in enumerate(moves))))
        while True:
            if inpt == 'n':
                print(state.board().nodes_map())
            elif inpt == 'e':
                print(state.board().edges_map())
            elif inpt == 'b':
                print(state.board())
            elif inpt == 'm':
                print(*(m.info() for m in moves), sep='\n')
            else:
                idx = int(inpt)
                if not 0 <= idx < len(moves):
                    print('supply an integer int the range [0, {}] please'.format(len(moves) - 1))
                else:
                    move = moves[idx]
                    return move
            inpt = input('Player {}, choose move by index (or n = nodes map, e = edges map, b = board, m = moves list):'
                         '\n'.format(player))

    def __repr__(self):
        return self.__name


class OneMoveHeuristicAgent(Agent):
    """An agent that gets a heuristic, chooses a move that maximizes that heuristic value"""

    # Open the tree only one move forward and apply the given heuristic on it
    def __init__(self, heuristic):
        super().__init__(AgentType.ONE_MOVE)
        self.__h = heuristic
        self.__randy = RandomAgent()

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        move_values = []
        for move in moves:
            new_state = deepcopy(state)
            new_state.simulate_game(move)
            curr_p = move.player()
            for p in new_state.players():
                if p == move.player():
                    curr_p = p
            hval = self.__h.value(new_state, curr_p)
            move_values.append(hval)
            del new_state

        max_val = max(move_values)
        argmax_vals_indices = [i for i, val in enumerate(move_values) if val == max_val]
        moves = [moves[i] for i in argmax_vals_indices]
        move = self.__randy.choose(moves, player, state)
        return move


class ProbabilityAgent(Agent):
    """An agent that chooses a move that maximizes the probability heuristic"""

    def __init__(self):
        super().__init__(AgentType.PROBABILITY)
        self.__harry = OneMoveHeuristicAgent(Probability())

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        return self.__harry.choose(moves, player, state)


class OptimizedHeuristicAgent(Agent):
    """A heuristic agent that implements helper functions that score move types as well as states"""

    # using the one move heuristic method
    def __init__(self, heuristic):
        super().__init__(AgentType.OPTIMIZED)
        self.__h = heuristic
        self.__randy = RandomAgent()

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        h_val = 0
        move_values = []
        for move in moves:
            # improve choice of monopoly dev card before simulating new state:
            if isinstance(move, Moves.UseMonopolyDevMove):
                h_val += self.optimize_monopoly_choice(state, player, deepcopy(move))
            new_state = deepcopy(state)
            new_state.simulate_game(move)
            curr_p = move.player()
            for p in new_state.players():
                if p == move.player():
                    curr_p = p

            h_val = self.__h.value(new_state, curr_p)
            # improve trading abilities:
            if move.get_type() == Moves.MoveType.TRADE:
                h_val += self.optimized_trading_choice(new_state, curr_p, deepcopy(move)) / 2

            move_values.append(h_val)
            del new_state

        max_val = max(move_values)
        argmax_vals_indices = [i for i, val in enumerate(move_values) if val == max_val]
        moves = [moves[i] for i in argmax_vals_indices]
        move = self.__randy.choose(moves, player, state)
        return move

    @staticmethod
    def optimize_monopoly_choice(session: GameSession, player: Player, move: Moves):
        """
        finds the most common resource among all other players and calculates
        if it is the best choice for the player, considering the player's hand

        :return:
        """
        p = find_sim_player(session, player)
        score = 0
        all_res_from_players = Hand()
        # all resources from all players:
        [all_res_from_players.insert(other_player.resource_hand()) for other_player in session.players() if
         other_player != p]
        res_values_all_players = \
            all_res_from_players.map_resources_by_quantity()
        res_values_curr_player = p.resource_hand().map_resources_by_quantity()

        for res_type in res_values_all_players:
            res_values_all_players[res_type] -= res_values_curr_player[
                                                    res_type] / 2

        most_common_res = max(res_values_all_players,
                              key=res_values_all_players.get)

        if move.resource() == most_common_res:
            score += 0.5
        return score

    @staticmethod
    def optimized_trading_choice(session: GameSession, player: Player, move: Moves):
        """prefer trading resources for resources you can't get from dice"""
        p = find_sim_player(session, player)
        res_hand = p.resource_hand()
        score = 0
        if move.get_type() == Moves.MoveType.TRADE:
            __board = session.board()
            res_types_from_dice = __board.resources_player_can_get(player)
            gets_type = move.gets().get_cards_types().pop()
            num_instances_gets_type = res_hand.cards_of_type(gets_type)

            # if what you get from trading you can't achieve from dice:
            if gets_type not in res_types_from_dice:
                # raise score:
                score += 1 / (2 * num_instances_gets_type)
        return score


class MonteCarloAgent(Agent):
    """An agent that uses a limited depth variant of Monte Carlo (game) tree search with heavy playouts
    (heuristic based). Tree traversal ends with current player's End-of-Turn."""

    def __init__(self, heuristic, depth: int = 0, iters: int = 1):
        super().__init__(AgentType.MONTECARLO)
        self.__depth = depth
        self.__iterations = iters
        self.__h = heuristic
        self.__harry = OneMoveHeuristicAgent(heuristic)
        self.__randy = RandomAgent()
        self.__curr_depth = 2

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        for p in state.players():
            if p == player:
                player = p
                break

        self.__curr_depth -= 1
        max_moves = moves
        all_move_values = []
        move_expected_vals = []

        # simulate each move until end of my turn and add final state evaluation to move_expected_vals
        for move_idx, move in enumerate(max_moves):
            all_move_values.append([])
            for _i in range(self.__iterations):
                move_state = deepcopy(state)
                move_state.simulate_game(move)
                self.sim_me(move_state, player)
                for _d in range(self.__depth):
                    self.sim_me(move_state, player)
                    self.sim_opps(move_state, player)
                value_reached = self.__h.value(move_state, player)
                all_move_values[move_idx].append(value_reached)
                del move_state
            avg_move_val = sum(all_move_values[move_idx]) / self.__iterations
            move_expected_vals.append(avg_move_val)

        # generate list of all moves tied for best move #
        max_val = max(move_expected_vals)
        best_moves = []
        for m_i, m in enumerate(max_moves):
            if move_expected_vals[m_i] == max_val:
                best_moves.append(m)

        self.__curr_depth += 1
        if len(best_moves) == 1:  # shortcut to save time
            return best_moves[0]
        else:
            return self.__harry.choose(best_moves, player, state)

    def sim_me(self, session, my_player):
        while session.current_player() == my_player and session.possible_moves():
            session.simulate_game(self.__harry.choose(session.possible_moves(),
                                                      session.current_player(),
                                                      session))

    def sim_opps(self, session, my_player):
        while session.current_player() != my_player and session.possible_moves():
            move_played = self.__randy.choose(session.possible_moves(),
                                              session.current_player(),
                                              session)
            session.simulate_game(move_played)


class LiteMonteCarloAgent(Agent):
    """An agent that uses a limited depth variant of Monte Carlo (game) tree search with heavy playouts
    (heuristic based). Tree traversal ends with current player's End-of-Turn."""

    def __init__(self, heuristic, depth: int = 0, iters: int = 10):
        super().__init__(AgentType.MONTECARLO)
        self.__depth = depth
        self.__iterations = iters
        self.__h = heuristic
        self.__harry = OneMoveHeuristicAgent(heuristic)
        self.__randy = RandomAgent()
        self.__curr_depth = 2

        # for remembering good randomized paths
        self.__last_seen_turn = None
        self.__last_computed_hval = None
        self.__last_computed_move_path = None

    def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
        for p in state.players():
            if p == player:
                player = p
                break

        self.__curr_depth -= 1
        max_moves = moves
        all_move_values = []
        move_expected_vals = []
        move_max_vals = []

        curr_best_path = []
        curr_best_hval = 0

        # simulate each move until end of my turn and add final state evaluation to move_expected_vals
        for move_idx, move in enumerate(max_moves):
            all_move_values.append([])
            move_max = 0
            for _i in range(self.__iterations):
                move_state = deepcopy(state)
                move_state.simulate_game(move)
                path_taken = []
                for _d in range(1):
                    self.sim_me(move_state, player, path_taken)
                    self.sim_opps(move_state, player)
                    self.sim_me_lite(move_state, player)
                value_reached = self.__h.value(move_state, player)
                if value_reached > curr_best_hval:
                    curr_best_hval = value_reached
                    curr_best_path = path_taken
                if value_reached > move_max:
                    move_max = value_reached
                all_move_values[move_idx].append(value_reached)
                del move_state
            # avg_move_val = sum(all_move_values[move_idx]) / self.__iterations
            # move_expected_vals.append(avg_move_val)
            move_max_vals.append(move_max)

        # generate list of all moves tied for best move #
        # max_val = max(move_expected_vals)
        # print('curr best path', curr_best_path)
        max_val = curr_best_hval
        if self.__last_seen_turn == state.num_turns_played() and max_val < self.__last_computed_hval:
            if self.__last_computed_move_path:
                move_to_make = self.__last_computed_move_path[0]
                for m in moves:
                    # print('comparing')
                    # print(m.info())
                    # print(move_to_make.info())
                    if m == move_to_make:
                        # print('EQ')
                        self.__last_computed_move_path = self.__last_computed_move_path[1:]
                        return m
        # print('last seen', self.__last_seen_turn, 'curr turn', state.num_turns_played())
        self.__last_seen_turn = state.num_turns_played()
        self.__last_computed_hval = max_val
        self.__last_computed_move_path = curr_best_path

        best_moves = []
        for m_i, m in enumerate(max_moves):
            # if move_expected_vals[m_i] == max_val:
            if move_max_vals[m_i] == max_val:
                best_moves.append(m)

        self.__curr_depth += 1
        if len(best_moves) == 1:  # shortcut to save time
            return best_moves[0]
        else:
            return self.__harry.choose(best_moves, player, state)

    def sim_me(self, session, my_player, path_taken):
        while session.current_player() == my_player and session.possible_moves():
            move_played = self.__randy.choose(session.possible_moves(),
                                              session.current_player(),
                                              session)
            path_taken.append(move_played)
            session.simulate_game(move_played)

    def sim_me_lite(self, session, my_player):
        while session.current_player() == my_player and session.possible_moves():
            session.simulate_game(choice(session.possible_moves()))

    def sim_opps(self, session, my_player):
        while session.current_player() != my_player and session.possible_moves():
            # move_played = self.__randy.choose(session.possible_moves(),
            #                                   session.current_player(),
            #                                   session)
            session.simulate_game(choice(session.possible_sim_moves(my_player)))


# class DQNAgent(Agent):
#     """An agent trained with a Deep-Q Learning Neural Network"""
#     network = tf.keras.models.load_model("current_model")
#
#     def __init__(self):
#         super().__init__(AgentType.DQN)
#
#     def choose(self, moves: List[Moves.Move], player: Player, state: GameSession) -> Moves.Move:
#         move_preds = get_move_predictions(DQNAgent.network, moves, state)
#         chosen_move_index = move_preds[:, 0].argmax()
#         return moves[chosen_move_index]


def find_sim_player(session: GameSession, player: Player) -> Player:
    # find the player's turn for the current session simulation
    for sim_player in session.players():
        if sim_player.get_id() == player.get_id():
            return sim_player
