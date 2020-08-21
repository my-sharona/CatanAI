from __future__ import annotations
from typing import Generator, Union, List
from itertools import combinations
from enum import Enum
from copy import deepcopy
import GameConstants as Consts
import Board
import Dice
import Player
import Hand
import Moves
import Buildable
import hexgrid

DEBUG = False


class GamePhase(Enum):  # used for self reference when agent wants to continue simulation from point left off
    START = 0
    PRE_GAME_SETTLEMENT = 1
    PRE_GAME_ROAD = 2
    ROBBER_THROW = 3
    ROBBER_PLACE = 4
    MAKE_MOVE = 5
    GAME_OVER = 6


class GameSession:
    """Class representing a Catan game instance, handles game flow, rule adherence, and logic of the game."""
    def __init__(self, *players: Player.Player):
        assert Consts.MIN_PLAYERS <= len(players) <= Consts.MAX_PLAYERS

        # winning stats
        self.__winning_player = None

        # game board & dice #
        self.__board = Board.Board()
        self.__dice = Dice.Dice()

        # players #
        self.__turn_order = self.__init_turn_order(*players)
        self.__num_players = len(self.__turn_order)
        self.__player_colors = ()
        self.__player_vp_histories = {str(p): [] for p in self.players()}

        # resources deck #
        self.__res_deck = Hand.Hand(*Consts.RES_DECK)

        # development cards deck #
        self.__dev_deck = Hand.Hand(*Consts.DEV_DECK)

        # phase misc #
        self.__dev_cards_bought_this_turn = Hand.Hand()
        self.__curr_turn_idx = 0
        self.__num_turns_played = 0
        self.__phase = GamePhase.START
        self.__curr_player_sim = self.__turn_order[0]
        self.__pre_game_round = 1
        self.__pre_game_settlement_node = None
        self.__throw_player = None
        self.__throw_player_hand_size = None
        self.__vp_earned_this_phase = 0
        self.__possible_moves_this_phase = []
        self.__dev_used_this_turn = False
        self.__yields = {p: 0 for p in self.players()}
        self.__prob_turn_history = {p: [(0, 0)] for p in self.players()}

    def run_game(self) -> None:
        """Initiates the main game loop, returns when game ends."""
        self.__run_pre_game()

        for curr_player in self.__turn_generator(self.__num_players):
            self.__dev_used_this_turn = False
            self.__vp_earned_this_phase = 0
            self.__curr_player_sim = curr_player
            self.__dev_cards_bought_this_turn = Hand.Hand()  # to know if player can use a dev card
            if self.__num_turns_played % 10 == 0:
                dprint(self.__num_turns_played, self.__curr_player_sim, 'playing...')
            dprint(*('{} = {}  '.format(p, p.vp()) for p in self.players()))

            self.__dice.roll()
            print('\n\n' + '*' * 100)
            print('*' * 45, 'NEXT TURN {:>3}'.format(self.__num_turns_played), '*' * 40)
            print('*' * 100 + '\n')
            print(f'[RUN GAME] Rolling dice... {self.__dice.sum()} rolled')
            if self.__dice.sum() == Consts.ROBBER_DICE_VALUE:  # robber activated
                dprint('[RUN GAME] Robber Activated! Checking for oversized hands...')

                # remove cards from oversized hands
                self.__phase = GamePhase.ROBBER_THROW
                for player in self.players():
                    player_hand_size = player.resource_hand_size()
                    if player_hand_size > Consts.MAX_CARDS_IN_HAND:
                        self.__throw_player = player
                        self.__throw_player_hand_size = player_hand_size - (player_hand_size // 2)
                        for _ in range(player_hand_size // 2):
                            self.__possible_moves_this_phase = self.__get_possible_throw_moves(player)
                            throw_move = player.choose(self.__possible_moves_this_phase, deepcopy(self))
                            cards_thrown = throw_move.throws()
                            dprint(f'[RUN GAME] player {player} had too many cards ({player_hand_size}), '
                                   f'he threw {cards_thrown}')
                            player.throw_cards(cards_thrown)
                            self.__res_deck.insert(cards_thrown)

                # move robber
                self.__phase = GamePhase.ROBBER_PLACE
                self.__possible_moves_this_phase = self.__get_possible_knight_moves(curr_player, robber=True)
                knight_move = curr_player.choose(self.__possible_moves_this_phase, deepcopy(self))

                assert isinstance(knight_move, Moves.UseKnightDevMove)
                robber_hex = knight_move.hex_id()
                opp = knight_move.take_from()
                self.__robber_protocol(curr_player, robber_hex, opp)

            else:  # not robber
                # distribute resources
                dprint(f'[RUN GAME] distributing resources...')
                dist = self.__board.resource_distributions(self.__dice.sum())
                for player, hand in dist.items():
                    self.__yields[player] += 1
                    removed = self.__res_deck.remove_as_much(hand)
                    player.receive_cards(removed)
                    dprint(f'[RUN GAME] player {player} received {removed}, '
                           f'now has {player.resource_hand()}')

            # query player for move #
            self.__phase = GamePhase.MAKE_MOVE
            self.__possible_moves_this_phase = self.__get_possible_moves(curr_player)
            moves_available = self.__possible_moves_this_phase
            dprint(f'[RUN GAME] player {curr_player} can play:\n')
            dprint('\n'.join(m.info() for m in moves_available) + '\n')
            move_to_play = curr_player.choose(moves_available, deepcopy(self))

            print(f'[RUN GAME] player {curr_player} is playing: {move_to_play.info()}')

            vp_before = curr_player.vp()
            self.__apply_move(move_to_play)
            vp_after = curr_player.vp()
            self.__vp_earned_this_phase = vp_after - vp_before

            while move_to_play.get_type() != Moves.MoveType.PASS:
                self.__possible_moves_this_phase = self.__get_possible_moves(curr_player)
                moves_available = self.__possible_moves_this_phase
                dprint(f'[RUN GAME] player {curr_player} can play:\n')
                dprint('\n'.join(m.info() for m in moves_available) + '\n')
                move_to_play = curr_player.choose(moves_available, deepcopy(self))
                print(f'[RUN GAME] player {curr_player} is playing: {move_to_play.info()}')

                vp_before = curr_player.vp()
                self.__apply_move(move_to_play)
                vp_after = curr_player.vp()
                self.__vp_earned_this_phase = vp_after - vp_before

            print(self.board())
            print(self.status_table())
            self.__update_vp_histories()
            if self.is_game_over():
                self.__phase = GamePhase.GAME_OVER
                self.__possible_moves_this_phase = []
                print(f'\n\n\nGAME OVER - {curr_player} won!!!')
                print("Game Ended After", self.__num_turns_played, "Turns")
                break

    def largest_army_player(self) -> Union[Player.Player, None]:
        """:returns player holding the largest army, None if no player currently holds it"""
        for p in self.players():
            if p.has_largest_army():
                return p

    def largest_army_size(self) -> int:
        """:returns the size of the currently largest army in the game"""
        return max(p.army_size() for p in self.players())

    def longest_road_player(self) -> Union[Player.Player, None]:
        """:returns player holding the Longest Road, None if no player currently holds it"""
        for p in self.players():
            if p.has_longest_road():
                return p

    def longest_road_length(self) -> int:
        """:returns the length of the currently longest road in the game"""
        return max(self.board().road_len(p) for p in self.players())

    def board(self) -> Board.Board:
        """:returns the game's board instance"""
        return self.__board

    def players(self) -> List[Player]:
        """:returns a list of the player instances in the game, in turn order"""
        return self.__turn_order

    def winner(self) -> Union[Player, None]:
        """if the game ended, :returns the player that won the game, None otherwise"""
        if self.is_game_over():
            return max([p for p in self.players()], key=lambda p: p.vp())

    def is_game_over(self) -> bool:
        """:returns True iff a player has reached the winning VP amount"""
        return any(player.vp() >= Consts.WINNING_VP for player in self.players())

    def num_turns_played(self) -> int:
        """:returns the number of turns played so far"""
        return self.__num_turns_played

    def vp_history(self):
        """:returns a {player: history} dictionary that maps players to lists of their VP per turn"""
        return self.__player_vp_histories

    def current_player(self) -> Player.Player:
        """:returns the player whose turn it is"""
        return self.__curr_player_sim

    def vp_earned_this_phase(self) -> int:
        """:returns the number of VP earned in the current game phase (choice making phase)"""
        return self.__vp_earned_this_phase

    def simulate_game(self, move_to_play: Moves.Move = None) -> List[Moves.Move]:
        """simulates a move to play, returns list of valid moves to play next"""
        if self.__phase == GamePhase.START:
            return self.__start_sim()

        if self.__phase == GamePhase.PRE_GAME_SETTLEMENT:
            assert isinstance(move_to_play, Moves.BuildMove)
            return self.__pre_game_settlement_sim(move_to_play)

        elif self.__phase == GamePhase.PRE_GAME_ROAD:
            assert isinstance(move_to_play, Moves.BuildMove)
            return self.__pre_game_road_sim(move_to_play)

        elif self.__phase == GamePhase.ROBBER_THROW:
            assert isinstance(move_to_play, Moves.ThrowMove)
            return self.__robber_throw_sim(move_to_play)

        elif self.__phase == GamePhase.ROBBER_PLACE:
            assert isinstance(move_to_play, Moves.UseKnightDevMove)
            return self.__robber_place_sim(move_to_play)

        elif self.__phase == GamePhase.MAKE_MOVE:
            return self.__make_move_sim(move_to_play)

        elif self.__phase == GamePhase.GAME_OVER:
            self.__possible_moves_this_phase = []
            return self.__possible_moves_this_phase

    def simulate_move(self, move: Moves.Move) -> GameSession:
        """legacy version of simulate_game that simulates without resuming the game flow"""
        state = deepcopy(self)
        for p in state.players():
            if p.get_id() == move.player().get_id():
                new_player_obj = p
                new_move = deepcopy(move)
                new_move.set_player(new_player_obj)
                state.__apply_move(new_move, printout=False, mock=True)
                return state

        else:
            print('ERROR didnt find new player obj in deepcopy')

    def possible_moves(self) -> List[Moves.Move]:
        """:returns list of possible moves to currently play"""
        return self.__possible_moves_this_phase

    def possible_sim_moves(self, simulating_player):
        if self.__curr_player_sim == simulating_player:
            return self.possible_moves()

        return [m for m in self.possible_moves() if not isinstance(m, Moves.UseDevMove) or (
            isinstance(m, Moves.UseKnightDevMove) and m.robber_activated())]

    def potential_probability_score(self, player: Player) -> float:
        """a scoring function that evaluates the potential probability value of a player's locality on the board"""
        def get_player_nodes(p):
            all_nodes = []
            for edge in p.road_edges():
                all_nodes.extend(hexgrid.nodes_touching_edge(edge))
            return all_nodes

        def get_almost_buildable_nodes(p):
            player_nodes = get_player_nodes(p)
            adj_to_player_nodes = set()
            for player_node in player_nodes:
                for adj_node in self.board().get_adj_nodes_to_node(player_node):
                    if self.__is_distant_node(adj_node) and adj_node not in player_nodes:
                        adj_to_player_nodes.add(adj_node)
            return list(adj_to_player_nodes)

        prob_score = 0
        buildable_nodes = self.__buildable_nodes(player)

        almost_buildable_nodes = get_almost_buildable_nodes(player)
        almost_buildable_coeff = 0.3
        buildable_coeff = 0.6
        hex_ids = []
        for node in buildable_nodes:
            hex_ids.extend(self.board().get_adj_tile_ids_to_node(node))
        for token in [self.board().hexes()[h_id].token() for h_id in hex_ids]:
            if token > 0:
                prob_score += buildable_coeff * Dice.PROBABILITIES[token]

        hex_ids = []
        for node in almost_buildable_nodes:
            hex_ids.extend(self.board().get_adj_tile_ids_to_node(node))
        for token in [self.board().hexes()[h_id].token() for h_id in hex_ids]:
            if token > 0:
                prob_score += almost_buildable_coeff * Dice.PROBABILITIES[token]

        return prob_score

    def players_luck(self):
        luck = []
        for p in self.players():
            hist = self.__prob_turn_history[p]
            hist.append((self.board().probability_score(p, exclude_robber=True), self.num_turns_played()))
            expected_yields = 0
            last_prob, last_turn = hist[0]
            for prob, turn in hist[1:]:
                expected_yields += (turn - last_turn) * last_prob
                last_turn = turn
                last_prob = prob
            actual_yields = self.__yields[p]
            print(p, 'actual yields', actual_yields)
            print(hist)
            print('calculated expected yields', expected_yields, '--> luck =', actual_yields / expected_yields)
            luck.append(actual_yields / expected_yields)

        return [(p, l) for p, l in zip(self.players(), luck)]

    def status_table(self) -> str:
        """:returns an informative string in tabular form of the current state of the game"""
        table = [['Player'] + [player for player in self.players()],
                 ['VP'] + [player.vp() for player in self.players()],
                 ['Agent'] + [str(player.agent()) for player in self.players()],
                 ['Road Len'] + [str(self.board().road_len(player)) for player in self.players()],
                 ['Longest Road'] + ['X' if player.has_longest_road() else '' for player in self.players()],
                 ['Largest Army'] + ['X' if player.has_largest_army() else '' for player in self.players()]]

        player_harbors = [p.harbors() for p in self.players()]
        max_harbors = max(len(harbors) for harbors in player_harbors)
        for harbor_idx in range(max_harbors):
            table.append(
                (['Harbors'] if harbor_idx == 0 else ['']) + [
                    (player_harbors[player_idx][harbor_idx] if harbor_idx < len(player_harbors[player_idx])
                     else '') for player_idx in range(len(self.players()))])

        max_cities = max(1, max(p.num_cities() for p in self.players()))
        for city_idx in range(max_cities):
            table.append(
                (['Cities'] if city_idx == 0 else ['']) + [
                    (hex(player.city_nodes()[city_idx]) if city_idx < len(player.city_nodes())
                     else '') for player in self.players()])

        max_settles = max(1, max(p.num_settlements() for p in self.players()))
        for settle_idx in range(max_settles):
            table.append(
                (['Settlements'] if settle_idx == 0 else ['']) + [
                    (hex(player.settlement_nodes()[settle_idx]) if settle_idx < len(player.settlement_nodes())
                     else '') for player in self.players()])

        max_roads = max(1, max(p.num_roads() for p in self.players()))
        for road_idx in range(max_roads):
            table.append(
                (['Roads'] if road_idx == 0 else ['']) + [
                    (hex(player.road_edges()[road_idx]) if road_idx < len(player.road_edges())
                     else '') for player in self.players()])

        max_res = max(1, max(p.resource_hand_size() for p in self.players()))
        for res_idx in range(max_res):
            table.append(
                (['Resources'] if res_idx == 0 else ['']) + [
                    ([card for card in player.resource_hand()][res_idx] if res_idx < player.resource_hand_size()
                     else '') for player in self.players()])

        max_res = max(1, max(p.dev_hand_size() for p in self.players()))
        for res_idx in range(max_res):
            table.append(
                (['Devs'] if res_idx == 0 else ['']) + [
                    ([card for card in player.dev_hand()][res_idx] if res_idx < player.dev_hand_size()
                     else '') for player in self.players()])

        max_res = max(1, max(p.used_dev_hand().size() for p in self.players()))
        for res_idx in range(max_res):
            table.append(
                (['Devs Used'] if res_idx == 0 else ['']) + [
                    ([card for card in player.used_dev_hand()][res_idx] if res_idx < player.used_dev_hand().size()
                     else '') for player in self.players()])
        max_widths = [0 for _ in table[0]]
        for line in table:
            for i in range(len(line)):
                max_widths[i] = max(len(str(line[i])), max_widths[i])

        sep = '|' + '-' * (sum(max_widths) + 3 * (len(max_widths) - 1) + 2) + '|'
        string_table = '\n' + sep + '\n| {:{}} |'.format('Status Table', len(sep) - 4) + \
                       '\n| {:{}} |'.format(f'{self.__num_turns_played} Turns Played', len(sep) - 4) + '\n'
        for line in table:
            if line[0]:
                string_table += sep + '\n'
            string_table += '| ' + ' | '.join(
                '{:{}}'.format(str(e), max_widths[i]) for i, e in enumerate(line)) + ' |\n'

        string_table += sep + '\n'

        return string_table

    def __init_turn_order(self, *players: Player.Player) -> List[Player.Player]:
        print('[CATAN] Catan game started, players rolling dice to establish turn order')
        rolls = []
        for player in players:
            if player is None:
                continue
            print(f'[CATAN] agent {player} rolled {self.__dice.roll()} = {self.__dice.sum()}')
            rolls.append((self.__dice.sum(), player))

        rolls.sort(key=lambda x: x[0], reverse=True)  # from highest sum to lowest
        print('[CATAN] turn order will be:\n' + '\n'.join(f'Player.Player {player}' for roll, player in rolls))
        return [player for roll, player in rolls]

    def __restore(self, saved_self: GameSession) -> None:
        self.__board = saved_self.__board
        self.__dice = saved_self.__dice
        self.__turn_order = saved_self.__turn_order
        self.__res_deck = saved_self.__res_deck
        self.__dev_deck = saved_self.__dev_deck
        self.__num_players = saved_self.__num_players

    def __turn_generator(self, num_players: int) -> Generator[Player.Player]:
        while True:
            self.__num_turns_played += 1
            yield self.players()[self.__curr_turn_idx]
            self.__curr_turn_idx = (self.__curr_turn_idx + 1) % num_players

    def __run_pre_game(self) -> None:
        print('[CATAN] Pre-Game started')
        print(self.board())
        for _round in (1, 2):
            self.__pre_game_round = _round
            turn_gen = ((player for player in self.players())  # 0, 1, 2, 3
                        if _round == 1 else
                        (player for player in reversed(self.players())))  # 3, 2, 1, 0
            for curr_player in turn_gen:
                self.__curr_player_sim = curr_player
                # get player's choice of settlement
                self.__phase = GamePhase.PRE_GAME_SETTLEMENT
                self.__possible_moves_this_phase = self.__get_possible_build_settlement_moves(curr_player,
                                                                                              pre_game=True)
                build_settlement_move = curr_player.choose(self.__possible_moves_this_phase, deepcopy(self))

                # add new settlement to game
                settlement_node = build_settlement_move.at()

                if settlement_node not in hexgrid.legal_node_coords():
                    print(build_settlement_move.info())
                    print('is in possible moves?', build_settlement_move in self.__possible_moves_this_phase)
                    print(*(m.info() for m in self.__possible_moves_this_phase))

                self.__pre_game_settlement_node = settlement_node
                settlement = Buildable.Buildable(curr_player, settlement_node, Consts.PurchasableType.SETTLEMENT)
                curr_player.add_buildable(settlement)
                self.__board.build(settlement)

                dprint(self.board())

                # get player's choice of road
                self.__phase = GamePhase.PRE_GAME_ROAD
                adj_edges = self.board().get_adj_edges_to_node(build_settlement_move.at())
                self.__possible_moves_this_phase = [
                    Moves.BuildMove(curr_player, Consts.PurchasableType.ROAD, edge, free=True)
                    for edge in adj_edges]
                possible_road_moves = self.__possible_moves_this_phase
                build_adj_road_move = curr_player.choose(possible_road_moves, deepcopy(self))

                # add new road to game
                road_edge = build_adj_road_move.at()
                road = Buildable.Buildable(curr_player, road_edge, Consts.PurchasableType.ROAD)
                curr_player.add_buildable(road)
                self.__board.build(road)

                print(f'[PRE GAME] player {curr_player} placed settlement at {hex(settlement_node)}, '
                       f'road at {hex(road_edge)}')

                if _round == 2:  # second round, yield resources from settlement
                    starting_resources = self.__board.resource_distributions_by_node(settlement_node)
                    self.__res_deck.remove(starting_resources)
                    curr_player.receive_cards(starting_resources)
                    dprint(f'[PRE GAME] player {curr_player} received {starting_resources} '
                           f'for his 2nd settlement at {hex(settlement_node)}')

                print(self.board())
                dprint(self.status_table())
        for p in self.players():
            self.__prob_turn_history[p].append((self.board().probability_score(p, exclude_robber=True), 0))

    def __robber_protocol(self, curr_player: Player.Player, robber_hex_id: int, opp: Player.Player,
                          printout=True) -> None:
        self.__board.move_robber_to(robber_hex_id)
        if printout:
            dprint(f'[ROBBER PROTOCOL] player {curr_player} placed robber at hex id {robber_hex_id}')

        # get all players adj to hex with robber
        possible_players = set()
        for node in hexgrid.nodes_touching_tile(robber_hex_id + 1):
            if node in self.__board.nodes():
                opp = self.__board.nodes().get(node).player()
                if opp != curr_player:
                    possible_players.add(opp)

        if printout:
            dprint(f'[ROBBER PROTOCOL] opponent players adjacent to hex: {possible_players}')

        # choose victim
        if opp is not None:

            if printout:
                dprint(f'[ROBBER PROTOCOL] stealing from player {opp}')

            # take card from player
            opp_hand = opp.resource_hand()
            if opp_hand.size():
                removed_card = opp_hand.remove_random_card()
                curr_player.receive_cards(removed_card)
                if printout:
                    dprint(f'[ROBBER PROTOCOL] player {curr_player} took {removed_card} from player {opp}')
            elif printout:
                dprint(f'[ROBBER PROTOCOL] player {curr_player} cannot take card from from player {opp}, '
                       f'hand is empty')
        elif printout:
            dprint(f'[ROBBER PROTOCOL] no players adjacent to hex {robber_hex_id}')

    def __apply_move(self, move: Moves.Move, printout=True, mock=False) -> None:
        if move.get_type() == Moves.MoveType.PASS:
            return

        player = move.player()
        for p in self.players():
            if p == move.player():
                player = p

        # saved_state = deepcopy(self)
        try:
            if isinstance(move, Moves.ThrowMove):
                card = move.throws()
                self.__res_deck.insert(card)
                player.resource_hand().remove(card)

            if isinstance(move, Moves.BuyDevMove):
                dev_cost = Consts.COSTS.get(Consts.PurchasableType.DEV_CARD)
                player.throw_cards(dev_cost)
                self.__res_deck.insert(dev_cost)
                # if mock use random card from orig deck minus all used cards
                if mock:
                    temp_deck = Hand.Hand(*Consts.DEV_DECK)
                    for p in self.players():
                        used = p.used_dev_hand()
                        temp_deck.remove(used)
                    card = temp_deck.remove_random_card()
                    del temp_deck
                else:
                    card = self.__dev_deck.remove_random_card()
                player.receive_cards(card)
                self.__dev_cards_bought_this_turn.insert(card)
                if printout:
                    dprint(f'[APPLY MOVE] player {player} bought dev card, got {card}')

            elif isinstance(move, Moves.BuildMove):
                if move.builds() == Consts.PurchasableType.CITY:
                    settlement_node_to_delete = move.at()
                    del self.board().nodes()[settlement_node_to_delete]
                    player.remove_settlement(settlement_node_to_delete)

                buildable_cost = Consts.COSTS.get(move.builds()) if not move.is_free() else Hand.Hand()
                player.throw_cards(buildable_cost)
                self.__res_deck.insert(buildable_cost)

                buildable = Buildable.Buildable(player, move.at(), move.builds())
                player.add_buildable(buildable)
                self.__board.build(buildable)
                if printout:
                    dprint(f'[APPLY MOVE] player {player} built {move.builds()} at {move.at()}')

                # update longest road player
                if buildable.type() == Consts.PurchasableType.ROAD:
                    new_road_len = self.board().road_len(player)
                    longest_road_player = self.longest_road_player()
                    if longest_road_player is not None:
                        longest_road_len = self.board().road_len(longest_road_player)
                        if longest_road_player != player:
                            if new_road_len > longest_road_len:
                                longest_road_player.set_longest_road(False)
                                player.set_longest_road(True)
                    elif new_road_len >= Consts.MIN_LONGEST_ROAD_SIZE:
                        player.set_longest_road(True)

                last_p_coeff = self.__prob_turn_history[player][-1][0]
                curr_p_coeff = self.board().probability_score(player, exclude_robber=True)
                if curr_p_coeff != last_p_coeff:
                    self.__prob_turn_history[player].append((curr_p_coeff, self.num_turns_played()))

            elif isinstance(move, Moves.UseDevMove):
                dev_used = move.uses()
                if isinstance(move, Moves.UseKnightDevMove) and move.robber_activated():
                    pass
                else:
                    if self.__dev_used_this_turn:
                        print('ERROR, used dev more than once in a turn')
                        exit()
                    player.use_dev(dev_used)  # remove the card
                    self.__dev_used_this_turn = True
                if printout:
                    dprint(f'[APPLY MOVE] player {player} used {dev_used} dev card')

                if isinstance(move, Moves.UseKnightDevMove):
                    # update largest army
                    new_army_size = player.army_size()
                    largest_army_player = self.largest_army_player()
                    if largest_army_player is not None:
                        largest_army_size = largest_army_player.army_size()
                        if largest_army_player != player:
                            if new_army_size > largest_army_size:
                                largest_army_player.set_largest_army(False)
                                player.set_largest_army(True)
                    elif new_army_size >= Consts.MIN_LARGEST_ARMY_SIZE:
                        player.set_largest_army(True)

                    hex_id = move.hex_id()
                    opp = move.take_from()
                    self.__robber_protocol(player, hex_id, opp, printout=printout)

                elif isinstance(move, Moves.UseMonopolyDevMove):
                    hand_gained = Hand.Hand()
                    resource_type = move.resource()
                    if printout:
                        dprint(f'[APPLY MOVE] player {player} chose {resource_type} as monopoly resource')

                    for opp in self.players():
                        if opp != player:
                            cards = opp.resource_hand().remove_by_type(resource_type)
                            dprint(f'[APPLY MOVE] opponent {opp} gave {cards}')
                            hand_gained.insert(cards)

                    player.receive_cards(hand_gained)

                    if printout:
                        dprint(f'[APPLY MOVE] player {player} gained {hand_gained.size()} {resource_type}')

                elif isinstance(move, Moves.UseRoadBuildingDevMove):
                    for _ in range(Consts.ROAD_BUILDING_NUM_ROADS):
                        self.__possible_moves_this_phase = self.__get_possible_build_road_moves(player, free=True)
                        possible_road_moves = self.__possible_moves_this_phase
                        if not possible_road_moves:
                            break

                        road_move = player.choose(possible_road_moves, deepcopy(self))

                        assert isinstance(road_move, Moves.BuildMove)
                        road = Buildable.Buildable(player, road_move.at(), Consts.PurchasableType.ROAD)
                        self.__board.build(road)
                        player.add_buildable(road)
                        dprint(f'[APPLY MOVE] player {player} built road at {road_move.at()}')

                        # update longest road player
                        new_road_len = self.board().road_len(player)
                        longest_road_player = self.longest_road_player()
                        if longest_road_player is not None:
                            longest_road_len = self.board().road_len(longest_road_player)
                            if longest_road_player != player:
                                if new_road_len > longest_road_len:
                                    longest_road_player.set_longest_road(False)
                                    player.set_longest_road(True)
                        elif new_road_len >= Consts.MIN_LONGEST_ROAD_SIZE:
                            player.set_longest_road(True)

                elif isinstance(move, Moves.UseYopDevMove):
                    resources = move.resources()
                    self.__res_deck.remove(resources)
                    player.receive_cards(resources)
                    if printout:
                        dprint(f'[APPLY MOVE] player {player} chose {resources} as YOP resources')

            elif isinstance(move, Moves.TradeMove):
                cards_received = move.gets()
                player.receive_cards(cards_received)
                self.__res_deck.remove(cards_received)

                cards_given = move.gives()
                player.throw_cards(cards_given)
                self.__res_deck.insert(cards_given)

                if printout:
                    dprint(f'[APPLY MOVE] player {player} traded {cards_given} for {cards_received}')

        except ValueError as e:
            dprint(f'player {player} tried to do move {move.get_type().name}, got error: \n{e}')
            # if DEBUG:
            exit()
            # self.__restore(saved_state)
            # del saved_state

    @staticmethod
    def __can_purchase(player: Player.Player, item: Consts.PurchasableType) -> bool:
        players_hand = player.resource_hand()
        item_cost = Consts.COSTS.get(item)
        retval = players_hand.contains(item_cost)
        return retval

    @staticmethod
    def __has_remaining_settlements(player: Player.Player) -> bool:
        return player.num_settlements() < Consts.MAX_SETTLEMENTS_PER_PLAYER

    @staticmethod
    def __has_remaining_cities(player: Player.Player) -> bool:
        return player.num_cities() < Consts.MAX_CITIES_PER_PLAYER

    @staticmethod
    def __has_remaining_roads(player: Player.Player) -> bool:
        return player.num_roads() < Consts.MAX_ROADS_PER_PLAYER

    @staticmethod
    def __has_general_harbor(player: Player.Player) -> bool:
        return Consts.ResourceType.ANY in player.harbor_resources()

    @staticmethod
    def __homogeneous_hands_of_size(player: Player.Player, sz: int) -> List[Hand.Hand]:
        hands = []
        players_hand = player.resource_hand()
        for resource in Consts.ResourceType:
            homogeneous_hand = Hand.Hand(*(resource for _ in range(sz)))
            if players_hand.contains(homogeneous_hand):
                hands.append(homogeneous_hand)
        return hands

    @staticmethod
    def __get_possible_throw_moves(player: Player.Player) -> List[Moves.ThrowMove]:
        players_cards = list(set([card for card in player.resource_hand() if card in Consts.YIELDING_RESOURCES]))
        throw_moves = [Moves.ThrowMove(player, Hand.Hand(card)) for card in players_cards]
        return throw_moves

    def __get_possible_knight_moves(self, player: Player.Player, robber: bool = False) -> List[Moves.UseKnightDevMove]:
        moves = []
        dev_type = Consts.DevType.KNIGHT
        if robber or player.dev_hand().contains(Hand.Hand(dev_type)):  # if has it
            # if wasnt bought this turn or had at least 1 more from before this turn
            if robber or (dev_type not in self.__dev_cards_bought_this_turn or
                          player.dev_hand().cards_of_type(dev_type).size() >
                          self.__dev_cards_bought_this_turn.cards_of_type(dev_type).size()):
                robber_hex = self.board().robber_hex()
                for hex_tile in self.board().hexes():  # get hex, cant place at same place or back at desert
                    if hex_tile is not robber_hex and hex_tile.resource() != Consts.ResourceType.DESERT:
                        opponents_on_hex = []  # finding opponents with buildables around hex
                        for node in hex_tile.nodes():  # get node around hex that is occupied
                            if self.board().nodes().get(node) is not None:
                                opp = self.board().nodes().get(node).player()
                                if opp != player and opp not in opponents_on_hex:  # if its not occupied by you...
                                    opponents_on_hex.append(opp)  # then its an opponent
                        if opponents_on_hex:
                            for opp in opponents_on_hex:
                                moves.append(
                                    Moves.UseKnightDevMove(player, hex_tile.id(), opp, robber_activated=robber))
                        else:  # no opponents, make move without opp id
                            moves.append(Moves.UseKnightDevMove(player, hex_tile.id(), None, robber_activated=robber))
        return moves

    def __get_possible_build_road_moves(self, player: Player.Player, free: bool = False) -> List[Moves.BuildMove]:
        moves = []
        if self.__has_remaining_roads(player):
            moves = [Moves.BuildMove(player, Consts.PurchasableType.ROAD, edge, free=free)
                     for edge in self.__buildable_edges(player)]
        return moves

    def __get_possible_build_settlement_moves(self, player: Player.Player,
                                              pre_game: bool = False) -> List[Moves.BuildMove]:
        moves = [Moves.BuildMove(player, Consts.PurchasableType.SETTLEMENT, node, free=pre_game)
                 for node in self.__buildable_nodes(player, pre_game)]
        return moves

    def __get_possible_moves(self, player: Player.Player) -> List[Moves.Move]:

        # PASS TURN #
        moves = [Moves.Move(player, Moves.MoveType.PASS)]

        # BUY #
        # Buy Dev Move Legality
        if (self.__can_purchase(player, Consts.PurchasableType.DEV_CARD) and
                self.__dev_deck.size() > 0):
            moves.append(Moves.BuyDevMove(player))

        # USE #
        # Use Dev Card Legality
        if not self.__dev_used_this_turn:
            for dev_type in Consts.DevType:  # get dev card type
                if dev_type == Consts.DevType.VP:   # not usable
                    continue
                if player.dev_hand().contains(Hand.Hand(dev_type)):  # if has it
                    # if wasnt bought this turn or had at least 1 more from before this turn
                    if (dev_type not in self.__dev_cards_bought_this_turn or
                            player.dev_hand().cards_of_type(dev_type).size() >
                            self.__dev_cards_bought_this_turn.cards_of_type(dev_type).size()):
                        if dev_type == Consts.DevType.MONOPOLY:
                            for resource in Consts.YIELDING_RESOURCES:
                                moves.append(Moves.UseMonopolyDevMove(player, resource))
                        elif dev_type == Consts.DevType.YEAR_OF_PLENTY:
                            for resource_comb in combinations(Consts.YIELDING_RESOURCES, Consts.YOP_NUM_RESOURCES):
                                moves.append(Moves.UseYopDevMove(player, *resource_comb))
                        elif dev_type == Consts.DevType.ROAD_BUILDING:
                            moves.append(Moves.UseRoadBuildingDevMove(player))
                        elif dev_type == Consts.DevType.KNIGHT:
                            robber_hex = self.board().robber_hex()
                            for hex_tile in self.board().hexes():
                                if hex_tile is not robber_hex and hex_tile.resource() != Consts.ResourceType.DESERT:
                                    opponents_on_hex = set()
                                    for node in hex_tile.nodes():
                                        if self.board().nodes().get(node) is not None:
                                            opp = self.board().nodes().get(node).player()
                                            if opp != player:
                                                opponents_on_hex.add(opp)
                                    if opponents_on_hex:
                                        for opp in opponents_on_hex:
                                            moves.append(Moves.UseKnightDevMove(player, hex_tile.id(), opp))
                                    else:
                                        moves.append(Moves.UseKnightDevMove(player, hex_tile.id(), None))

                        elif dev_type == Consts.DevType.VP:
                            moves.append(Moves.UseDevMove(player, dev_type))

        # BUILD #
        # Build settlement legality
        if (self.__can_purchase(player, Consts.PurchasableType.SETTLEMENT) and
                self.__has_remaining_settlements(player)):
            for node in self.__buildable_nodes(player):
                moves.append(Moves.BuildMove(player, Consts.PurchasableType.SETTLEMENT, node))

        # build city legality
        if (self.__can_purchase(player, Consts.PurchasableType.CITY) and
                self.__has_remaining_cities(player)):
            for settlement_node in player.settlement_nodes():
                moves.append(Moves.BuildMove(player, Consts.PurchasableType.CITY, settlement_node))

        # build road legality
        if (self.__can_purchase(player, Consts.PurchasableType.ROAD) and
                self.__has_remaining_roads(player)):
            for edge_id in self.__buildable_edges(player):
                moves.append(Moves.BuildMove(player, Consts.PurchasableType.ROAD, edge_id))

        # TRADE #
        # trade legality with deck
        for homogeneous_hand in self.__homogeneous_hands_of_size(player, Consts.DECK_TRADE_RATIO):
            for available_resource in self.__available_resources():
                if [card for card in homogeneous_hand][0] != available_resource:
                    moves.append(Moves.TradeMove(player, homogeneous_hand, Hand.Hand(available_resource)))

        # trade legality with general harbor
        if self.__has_general_harbor(player):
            for homogeneous_hand in self.__homogeneous_hands_of_size(player, Consts.GENERAL_HARBOR_TRADE_RATIO):
                for available_resource in self.__available_resources():
                    moves.append(Moves.TradeMove(player, homogeneous_hand, Hand.Hand(available_resource)))

        # trade legality with resource harbor
        for resource in player.harbor_resources():
            cards_out = Hand.Hand(*[resource for _ in range(Consts.RESOURCE_HARBOR_TRADE_RATIO)])
            if player.resource_hand().contains(cards_out):
                for available_resource in self.__available_resources():
                    moves.append(Moves.TradeMove(player, cards_out, Hand.Hand(available_resource)))

        return moves

    def __buildable_nodes(self, player: Player.Player, pre_game: bool = False) -> List[int]:
        player_nodes = set()
        if pre_game:
            return [node for node in hexgrid.legal_node_coords() if self.__is_distant_node(node)]
        else:
            for edge_id in player.road_edges():
                for node in hexgrid.nodes_touching_edge(edge_id):
                    if self.board().nodes().get(node) is None:
                        player_nodes.add(node)
            return [node for node in player_nodes if self.__is_distant_node(node)]

    def __buildable_edges(self, player: Player.Player) -> List[int]:
        player_nodes = set()
        for road_edge in player.road_edges():
            for node in hexgrid.nodes_touching_edge(road_edge):
                player_nodes.add(node)

        adj_edges = set()
        for node in player_nodes:
            for edge_id in self.board().get_adj_edges_to_node(node):
                adj_edges.add(edge_id)

        for existing_edge in player.road_edges():
            if existing_edge in adj_edges:
                adj_edges.remove(existing_edge)

        to_remove = []
        for edge in adj_edges:
            if edge not in hexgrid.legal_edge_coords() or self.board().edges().get(edge) is not None:
                to_remove.append(edge)

        for edge in to_remove:
            adj_edges.remove(edge)

        return list(adj_edges)

    def __is_distant_node(self, node_id: int) -> bool:
        adj_nodes = self.__board.get_adj_nodes_to_node(node_id) + [node_id]
        return all(self.__board.nodes().get(adj) is None for adj in adj_nodes)

    def __available_resources(self) -> List[Consts.ResourceType]:
        available = []
        for resource in Consts.ResourceType:
            if self.__res_deck.contains(Hand.Hand(resource)):
                available.append(resource)
        return available

    def __update_vp_histories(self) -> None:
        for p in self.players():
            self.__player_vp_histories[str(p)].append(p.vp())

    # simulation helpers #
    def __start_sim(self) -> List[Moves.BuildMove]:
        _round = self.__pre_game_round
        curr_player = self.__curr_player_sim
        self.__phase = GamePhase.PRE_GAME_SETTLEMENT
        self.__possible_moves_this_phase = self.__get_possible_build_settlement_moves(curr_player, pre_game=True)
        return self.__possible_moves_this_phase

    def __pre_game_settlement_sim(self, move_to_play: Moves.BuildMove) -> List[Moves.Move]:
        # add new settlement to game
        curr_player = self.__curr_player_sim
        build_settlement_move = move_to_play
        settlement_node = build_settlement_move.at()
        self.__pre_game_settlement_node = settlement_node
        settlement = Buildable.Buildable(curr_player, settlement_node, Consts.PurchasableType.SETTLEMENT)
        curr_player.add_buildable(settlement)
        self.__board.build(settlement)

        dprint(self.board())

        # get player's choice of road
        self.__phase = GamePhase.PRE_GAME_ROAD
        adj_edges = self.board().get_adj_edges_to_node(build_settlement_move.at())
        possible_road_moves = [Moves.BuildMove(curr_player, Consts.PurchasableType.ROAD, edge, free=True)
                               for edge in adj_edges]
        self.__possible_moves_this_phase = possible_road_moves
        return self.__possible_moves_this_phase

    def __pre_game_road_sim(self, move_to_play: Moves.BuildMove) -> List[Moves.Move]:
        build_adj_road_move = move_to_play
        curr_player = self.__curr_player_sim
        _round = self.__pre_game_round
        settlement_node = self.__pre_game_settlement_node

        # add new road to game
        road_edge = build_adj_road_move.at()
        road = Buildable.Buildable(curr_player, road_edge, Consts.PurchasableType.ROAD)
        curr_player.add_buildable(road)
        self.__board.build(road)

        if _round == 2:  # second round, yield resources from settlement
            starting_resources = self.__board.resource_distributions_by_node(settlement_node)
            self.__res_deck.remove(starting_resources)
            curr_player.receive_cards(starting_resources)

        # new - update round and player
        if _round == 1:
            next_player_idx = (self.players().index(curr_player) + 1) % len(self.players())
            if next_player_idx == 0:  # round ended
                self.__pre_game_round = 2
                self.__curr_player_sim = self.players()[-1]
            else:
                self.__curr_player_sim = self.players()[next_player_idx]
        else:  # round 2
            next_player_idx = (self.players().index(curr_player) - 1) % len(self.players())
            if next_player_idx == len(self.players()) - 1:  # 2nd round ended
                self.__curr_player_sim = self.players()[0]
                # start main game
                return self.__main_game_sim()
            else:
                self.__curr_player_sim = self.players()[next_player_idx]

        self.__phase = GamePhase.PRE_GAME_SETTLEMENT
        settlement_moves = self.__get_possible_build_settlement_moves(self.__curr_player_sim, pre_game=True)
        self.__possible_moves_this_phase = settlement_moves
        return self.__possible_moves_this_phase

    def __main_game_sim(self) -> List[Moves.Move]:
        curr_player = self.__curr_player_sim
        self.__dev_used_this_turn = False
        self.__dev_cards_bought_this_turn = Hand.Hand()  # to know if player can use a dev card

        self.__dice.roll()
        dprint('\n\n' + '*' * 100)
        dprint('*' * 45, 'SIM NEXT TURN', '*' * 44)
        dprint('*' * 100 + '\n')

        dprint(f'[RUN GAME] Rolling dice... {self.__dice.sum()} rolled')
        if self.__dice.sum() == Consts.ROBBER_DICE_VALUE:  # robber activated
            dprint('[RUN GAME] Robber Activated! Checking for oversized hands...')

            # remove cards from oversized hands
            self.__phase = GamePhase.ROBBER_THROW
            for player in self.players():
                player_hand_size = player.resource_hand_size()
                if player_hand_size > Consts.MAX_CARDS_IN_HAND:
                    self.__throw_player = player
                    self.__throw_player_hand_size = player_hand_size - (player_hand_size // 2)
                    self.__possible_moves_this_phase = self.__get_possible_throw_moves(player)
                    return self.__possible_moves_this_phase

        else:  # not robber
            # distribute resources
            dprint(f'[RUN GAME] distributing resources...')
            dist = self.__board.resource_distributions(self.__dice.sum())
            for player, hand in dist.items():
                removed = self.__res_deck.remove_as_much(hand)
                player.receive_cards(removed)
                dprint(f'[RUN GAME] player {player} received {removed}, '
                       f'now has {player.resource_hand()}')

        # query player for move #
        self.__phase = GamePhase.MAKE_MOVE
        moves_available = self.__get_possible_moves(curr_player)
        dprint(f'[RUN GAME] player {curr_player} can play:\n')
        dprint('\n'.join(m.info() for m in moves_available) + '\n')
        self.__possible_moves_this_phase = moves_available
        return self.__possible_moves_this_phase

    def __robber_throw_sim(self, move_to_play: Moves.ThrowMove) -> List[Moves.Move]:
        player = self.__throw_player
        throw_move = move_to_play

        cards_thrown = throw_move.throws()
        player.throw_cards(cards_thrown)
        self.__res_deck.insert(cards_thrown)
        if player.resource_hand().size() > self.__throw_player_hand_size:
            self.__possible_moves_this_phase = self.__get_possible_throw_moves(player)
            return self.__possible_moves_this_phase
        else:
            next_player_idx = self.players().index(player) + 1
            while next_player_idx < len(self.players()):
                next_player = self.players()[next_player_idx]
                next_player_hand_size = next_player.resource_hand().size()
                if next_player_hand_size > Consts.MAX_CARDS_IN_HAND:
                    self.__throw_player = next_player
                    self.__throw_player_hand_size = next_player_hand_size - (next_player_hand_size // 2)
                    self.__possible_moves_this_phase = self.__get_possible_throw_moves(self.__throw_player)
                    return self.__possible_moves_this_phase
                else:
                    next_player_idx += 1

        # move robber
        self.__phase = GamePhase.ROBBER_PLACE
        knight_moves = self.__get_possible_knight_moves(self.__curr_player_sim, robber=True)
        self.__possible_moves_this_phase = knight_moves
        return self.__possible_moves_this_phase

    def __robber_place_sim(self, move: Moves.UseKnightDevMove) -> List[Moves.Move]:
        knight_move = move
        curr_player = self.__curr_player_sim

        robber_hex = knight_move.hex_id()
        opp = knight_move.take_from()
        self.__robber_protocol(curr_player, robber_hex, opp, printout=False)

        # query player for move #
        self.__phase = GamePhase.MAKE_MOVE
        moves_available = self.__get_possible_moves(curr_player)
        self.__possible_moves_this_phase = moves_available
        return self.__possible_moves_this_phase

    def __make_move_sim(self, move_to_play: Moves.Move) -> List[Moves.Move]:
        curr_player = self.__curr_player_sim

        vp_before = curr_player.vp()
        self.__apply_move(move_to_play, mock=True)
        vp_after = curr_player.vp()
        self.__vp_earned_this_phase = vp_after - vp_before

        if move_to_play.get_type() != Moves.MoveType.PASS:
            moves_available = self.__get_possible_moves(curr_player)
            self.__possible_moves_this_phase = moves_available
            return self.__possible_moves_this_phase

        elif self.is_game_over():
            self.__phase = GamePhase.GAME_OVER
            dprint(f'\n\n\nGAME OVER - player {curr_player} won!!!')
            self.__possible_moves_this_phase = []
            return self.__possible_moves_this_phase
        else:  # continue to next player
            next_player_idx = (self.players().index(curr_player) + 1) % len(self.players())
            self.__curr_player_sim = self.players()[next_player_idx]
            return self.__main_game_sim()


def dprint(*args, **kwargs):
    """a debug printer"""
    if DEBUG:
        print(*args, **kwargs)
