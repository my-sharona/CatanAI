from __future__ import annotations
import hexgrid
import GameConstants as Consts
from random import shuffle
from typing import List, Dict
import HexTile
import Player
import Hand
import Buildable
from Dice import PROBABILITIES


class Board:
    COLORS = {
        'TEAL': '\033[96m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'BLUE': '\033[94m',
        'END': '\033[0m'
    }

    def __init__(self, *players: Player):
        self.__init_hexes()
        self.__players = players
        self.__nodes = dict()
        self.__edges = dict()
        self.__player_colors = list(Board.COLORS.values())
        self.__players = []

    def __init_hexes(self) -> None:
        deck = Consts.HEX_DECK.copy()
        shuffle(deck)
        # use id that is 1 less than the pic @ https://github.com/rosshamish/hexgrid/, 0-indexing.
        self.__hexes = []
        curr_token_id = 0
        robber_placed = False  # this is added for cases where multiple deserts exist, place robber in first only
        for hex_id in range(Consts.NUM_HEXES):
            resource = deck[hex_id]
            if resource == Consts.ResourceType.DESERT and not robber_placed:  # desert hex
                token = 0
                has_robber = True
                robber_placed = True
            else:
                token = Consts.TOKEN_ORDER[curr_token_id]
                has_robber = False
                curr_token_id += 1

            self.__hexes.append(HexTile.HexTile(hex_id, resource, token, has_robber))

    def hexes(self) -> List[HexTile.HexTile]:
        return self.__hexes

    def nodes(self) -> Dict[int, Buildable.Buildable]:
        return self.__nodes

    def edges(self) -> Dict[int, Buildable.Buildable]:
        return self.__edges

    def robber_hex(self) -> HexTile.HexTile:
        for hex_tile in self.hexes():
            if hex_tile.has_robber():
                return hex_tile

    def move_robber_to(self, hex_id: int) -> None:
        self.robber_hex().set_robber(False)
        self.hexes()[hex_id].set_robber(True)

    def resource_distributions_by_node(self, coord: int) -> Hand.Hand:
        return Hand.Hand(*(self.hexes()[h].resource() for h in self.get_adj_tile_ids_to_node(coord)
                           if self.hexes()[h].resource() in Consts.YIELDING_RESOURCES))

    def resources_player_can_get(self,player:Player.Player) -> Hand:
        """
        :param player: the given player to check
        :return: Hand, the potential cards the player can get from his nodes
        by rolling dice
        """
        yielding_nodes = player.city_nodes() + player.settlement_nodes()
        types = set()
        for node in yielding_nodes:
            node_types = self.resource_distributions_by_node(node).get_cards_types()
            for type in node_types.copy():
                types.add(node_types.pop())
        return types

    def resource_distributions(self, dice_sum: int) -> Dict[Player.Player, Hand.Hand]:
        dist = {}
        for hex_tile in self.hexes():
            if hex_tile.token() == dice_sum and not hex_tile.has_robber():  # hex that distributes
                adj_nodes = hexgrid.nodes_touching_tile(hex_tile.id() + 1)  # he uses 1 indexing
                for node in adj_nodes:
                    if self.nodes().get(node):  # node has buildable on it
                        player = self.nodes().get(node).player()  # belongs to player_id
                        if player not in dist:
                            dist[player] = Hand.Hand()
                        dist[player].insert(Hand.Hand(hex_tile.resource()))  # add hex's resource to distributed hand
        return dist

    @staticmethod
    def get_adj_nodes_to_node(location: int) -> List[int]:
        if location % 2 == 1:
            locs = [location - 0x11, location + 0x11, location + 0xf]
        else:
            locs = [location - 0x11, location + 0x11, location - 0xf]
        return [loc for loc in locs if loc in hexgrid.legal_node_coords()]

    @staticmethod
    def get_adj_edges_to_node(location: int) -> List[int]:
        if location % 2 == 1:
            locs = [location, location - 0x11, location - 0x1]
        else:
            locs = [location - 0x10, location - 0x11, location]
        return [loc for loc in locs if loc in hexgrid.legal_edge_coords()]

    @staticmethod
    def get_adj_tile_ids_to_node(location: int) -> List[int]:
        if location not in hexgrid.legal_node_coords():
            raise ValueError(f'tried to access node {location}')
        if location % 2 == 0:
            tile_coords = [location - 0x1, location + 0x1, location - 0x21]
        else:
            tile_coords = [location + 0x10, location - 0x10, location - 0x12]
        return [hexgrid.tile_id_from_coord(coord) - 1 for coord in tile_coords if coord in hexgrid.legal_tile_coords()]

    def build(self, buildable: Buildable.Buildable) -> None:
        player = buildable.player()
        if player not in self.__players:
            self.__players.append(player)
        coords = self.nodes()
        if buildable.type() == Consts.PurchasableType.ROAD:
            coords = self.edges()
        coords[buildable.coord()] = buildable

    def info(self) -> str:
        ret_val = ['\n[BOARD] Hexes']
        for h in self.hexes():
            ret_val.append(h.info())
        ret_val.append('\n[BOARD] Buildables')
        for n, buildable in self.nodes().items():
            ret_val.append(buildable.info())
        for n, buildable in self.edges().items():
            ret_val.append(buildable.info())
        return '\n'.join(ret_val)

    # def __dfs_roads_recursive(self, player, graph, stack, visited, path):
    #     max_path = len(path)
    #     while stack:
    #         curr = stack.pop()
    #         # print('stack popped', curr)
    #         visited.add(curr)
    #
    #         for neighbor in graph[curr]:
    #             if neighbor in self.nodes() and self.nodes().get(neighbor).player() != player:  # someone built here, streak ends
    #                 # print('neighbor', neighbor, 'in built opp')
    #                 continue
    #             if neighbor not in visited:
    #                 stack.append(neighbor)
    #                 path_len = self.__dfs_roads_recursive(player, graph, stack, visited, path + [neighbor])
    #                 if path_len > max_path:
    #                     max_path = path_len
    #     return max_path

    def dfs(self, player, last, visited, graph, node, path, max_len):
        if node not in visited:
            # print('curr node', node)
            # print('curr path', path)
            if node in self.nodes() and self.nodes().get(node).player().get_id() != player.get_id():
                # print('node has opp')
                return
            visited.add(node)
            # print('visited', visited)
            for neighbour in graph[node]:
                # print('neighbor', neighbour)
                if neighbour != last:
                    max_len[0] = max(max_len[0], len(path) + 1)
                else:
                    continue
                # print('max', max_len[0])
                self.dfs(player, node, visited, graph, neighbour, path + [neighbour], max_len)

    def __calc_road_len(self, player, graph):
        max_len = 0
        for start in graph:
            visited = set()
            path = []
            start_len = [0]
            self.dfs(player, None, visited, graph, start, path, start_len)
            if start_len[0] > max_len:
                max_len = start_len[0]
        return max_len

    def road_len(self, player: Player) -> int:
        graph = {}
        for edge in player.road_edges():
            node1, node2 = hexgrid.nodes_touching_edge(edge)
            if node1 not in graph:
                graph[node1] = set()
            if node2 not in graph:
                graph[node2] = set()
            graph[node1].add(node2)
            graph[node2].add(node1)
        # print(player)
        # for n, vals in graph.items():
        #     print(hex(n), [hex(v) for v in vals])
        # print('NODES')
        # for n, vals in self.nodes().items():
        #     print(hex(n), vals.player())

        return self.__calc_road_len(player, graph)

        # max_len = 0
        # for start in graph:
        #     curr_len = 0
        #     max_curr_len = 0
        #     visited = set()
        #     stack = [start]
        #     while stack:
        #         curr = stack.pop()
        #         curr_len += 1
        #         visited.add(curr)
        #         added = False
        #         for neighbor in graph[curr]:
        #             if self.nodes().get(neighbor) is not None and self.nodes().get(neighbor).player() != player:    # someone built here, streak ends
        #                 continue
        #             if neighbor not in visited:
        #                 stack.append(neighbor)
        #                 added = True
        #         if not added:
        #             curr_len -= 1
        #             if max_curr_len < curr_len:
        #                 max_curr_len = curr_len
        #     if max_len < max_curr_len:
        #         max_len = max_curr_len
        # return max_len
    def probability_score(self, player: Player, exclude_robber=False) -> float:
        """
        :return: player's probability of getting any resource/s in a given turn, based on settlements / cities
        """
        rolls = set()
        for loc in player.settlement_nodes() + player.city_nodes():
            for hex_tile in self.get_adj_tile_ids_to_node(loc):
                if exclude_robber or not self.hexes()[hex_tile].has_robber():
                    rolls.add(self.hexes()[hex_tile].token())

        prob = sum(PROBABILITIES.get(roll, 0) for roll in rolls)
        assert 0 <= prob <= 1
        return prob

    def expectation_score(self, player: Player) -> float:
        """
        :return: player's expected resource gain in a given turn, based on settlements / cities
        """
        rolls_amounts = []
        for settlement_loc in player.settlement_nodes():
            for hex_tile in self.get_adj_tile_ids_to_node(settlement_loc):
                rolls_amounts.append((self.hexes()[hex_tile].token(), Consts.NUM_RESOURCES_PER_SETTLEMENT))
        for city_loc in player.city_nodes():
            for hex_tile in self.get_adj_tile_ids_to_node(city_loc):
                rolls_amounts.append((self.hexes()[hex_tile].token(), Consts.NUM_RESOURCES_PER_CITY))
        expected = sum(PROBABILITIES.get(roll, 0) * num_resources for roll, num_resources in rolls_amounts)
        assert expected >= 0
        return expected

    def edges_map(self) -> str:
        def player_color(player):
            return self.__player_colors[self.__players.index(player)]

        def get_color(edge, is_edge=True):
            coords = self.edges() if is_edge else self.nodes()
            if coords.get(edge) is not None:
                return self.__player_colors[self.__players.index(coords.get(edge).player())]
            else:
                return Board.COLORS['END']

        def get_node_str(node):
            if self.nodes().get(node) is not None:
                if self.nodes().get(node).type() == Consts.PurchasableType.SETTLEMENT:
                    return 's'
                else:
                    return 'C'
            else:
                return ' '

        dh = {f'h{i}': str(h) for i, h in enumerate(self.hexes())}
        dht = {f'h{i}t': h.token() for i, h in enumerate(self.hexes())}
        x = 'x'
        dr = {f'r{hex(edge).split(x)[1]}': hex(edge).split(x)[1] for edge in hexgrid.legal_edge_coords()}
        legend = ' '.join('{}{}{}'.format(player_color(player), player, Board.COLORS['END'])
                          for player in self.__players)
        detc = {'e': Board.COLORS['END'], 'legend': legend}
        dn = {f'n{hex(node).split(x)[1]}': '{}{}{}'.format(get_color(node, is_edge=False), get_node_str(node),
                                                           Board.COLORS['END']) for node in hexgrid.legal_node_coords()}
        dy = {f'y{i}': 'R' if h.has_robber() else ' ' for i, h in enumerate(self.hexes())}
        d = dict()
        for other_dict in (dh, dht, dr, dn, dy, detc):
            for key, value in other_dict.items():
                d[key] = value

        return """
                                                        3:1
                                                       /   \\
                                                      {n27}{r27}_____{e}{n38}           
                                                   {r26}/{e}   {y0}   {r38}\\{e}         
                                  ORE __   {n25}{r25}_____{e}{n36}/{e}  {h0:^15}   \\{e}{n49}{r49}_____{e}{n5a}  __ SHEEP
                                      \\ {r24}/{e}     {y1} {r36}\\{e}   {h0t:^2}    {r48}/{e}   {y11}   {r5a}\\{e}  /
                                {n23}{r23}_____{e}{n34}/{e}  {h1:^15}   \\{e}{n47}{r47}_____{e}{n58}/{e} {h11:^15}    \\{e}{n6b}{r6b}_____{e}{n7c}
                             {r22}/{e}   {y2}   {r34}\\{e}   {h1t:^2}    {r46}/{e}   {y12}   {r58}\\{e}    {h11t:^2}   {r6a}/{e}   {y10}   {r7c}\\{e}
                             {n32}/{e} {h2:^15}    \\{e}{n45}{r45}_____{e}{n56}/{e}   {h12:^15}  \\{e}{n69}{r69}_____{e}{n7a}/{e}   {h10:^15}  \\{e}{n8d}
                            {r32}\\{e}   {h2t:^2}    {r44}/{e}   {y13}   {r56}\\{e}   {h12t:^2}    {r68}/{e}   {y17}   {r7a}\\{e}   {h10t:^2}    {r8c}/{e}
                   WHEAT __    \\{e}{n43}{r43}_____{e}{n54}/{e}   {h13:^15}  \\{e}{n67}{r67}_____{e}{n78}/{e}   {h17:^15}  \\{e}{n8b}{r8b}_____{e}{n9c}/{e} __ 3:1
                         \\   {r42}/{e}   {y3}   {r54}\\{e}   {h13t:^2}    {r66}/{e}   {y18}   {r78}\\{e}   {h17t:^2}    {r8a}/{e}   {y9}   {r9c}\\{e}  /
                             {n52}/{e} {h3:^15}    \\{e}{n65}{r65}_____{e}{n76}/{e}   {h18:^15}  \\{e}{n89}{r89}_____{e}{n9a}/{e}   {h9:^15}  \\{e}{nad}
                            {r52}\\{e}   {h3t:^2}    {r64}/{e}   {y14}   {r76}\\{e}   {h18t:^2}    {r88}/{e}   {y16}   {r9a}\\{e}   {h9t:^2}    {rac}/{e}
                               \\{e}{n63}{r63}_____{e}{n74}/{e}   {h14:^15}  \\{e}{n87}{r87}_____{e}{n98}/{e}   {h16:^15}  \\{e}{nab}{rab}_____{e}{nbc}/{e}
                             {r62}/{e}   {y4}   {r74}\\{e}   {h14t:^2}    {r86}/{e}   {y15}   {r98}\\{e}   {h16t:^2}    {raa}/{e}   {y8}   {rbc}\\{e}
                             {n72}/{e} {h4:^15}    \\{e}{n85}{r85}_____{e}{n96}/{e}   {h15:^15}  \\{e}{na9}{ra9}_____{e}{nba}/{e}   {h8:^15}  \\{e}{ncd}
                          / {r72}\\{e}   {h4t:^2}    {r84}/{e}   {y5}   {r96}\\{e}   {h15t:^2}    {ra8}/{e}   {y7}   {rba}\\{e}   {h8t:^2}    {rcc}/{e} \\
                     3:1 __    \\{e}{n83}{r83}_____{e}{n94}/{e} {h5:^15}    \\{e}{na7}{ra7}_____{e}{nb8}/{e}  {h7:^15}   \\{e}{ncb}{rcb}_____{e}{ndc}/{e} __ 3:1
                                       {r94}\\{e}   {h5t:^2}    {ra6}/{e}   {y6}   {rb8}\\{e}   {h7t:^2}    {rca}/{e}
                                          \\{e}{na5}{ra5}_____{e}{nb6}/{e}   {h6:^15}  \\{e}{nc9}{rc9}_____{e}{nda}/{e}
                                           |    / {rb6}\\{e}   {h6t:^2}    {rc8}/{e}   \\    |
                                          FOREST     \\{e}{nc7}{rc7}_____{e}{nd8}/{e}     BRICK

                             {legend}""".format(**d)

    def nodes_map(self) -> str:
        def player_color(player):
            return self.__player_colors[self.__players.index(player)]

        def get_color(edge, is_edge=True):
            coords = self.edges() if is_edge else self.nodes()
            if coords.get(edge) is not None:
                return self.__player_colors[self.__players.index(coords.get(edge).player())]
            else:
                return Board.COLORS['END']
        dh = {f'h{i}': str(h) for i, h in enumerate(self.hexes())}
        dht = {f'h{i}t': h.token() for i, h in enumerate(self.hexes())}
        x = 'x'
        dr = {f'r{hex(edge).split(x)[1]}': get_color(edge) for edge in hexgrid.legal_edge_coords()}
        legend = ' '.join('{}{}{}'.format(player_color(player), player, Board.COLORS['END'])
                          for player in self.__players)
        detc = {'e': Board.COLORS['END'], 'legend': legend}
        dn = {f'n{hex(node).split(x)[1]}': '{}{}{}'.format(get_color(node, is_edge=False), hex(node).split(x)[1],
                                                           Board.COLORS['END']) for node in hexgrid.legal_node_coords()}
        dy = {f'y{i}': 'R' if h.has_robber() else ' ' for i, h in enumerate(self.hexes())}
        d = dict()
        for other_dict in (dh, dht, dr, dn, dy, detc):
            for key, value in other_dict.items():
                d[key] = value
        return """
                                              3:1
                                             /   \\
                                           {n27}{r27}_____{e}{n38}           
                                          {r26}/{e}   {y0}     {r38}\\{e}         
                         ORE __ {n25}{r25}_____{e}{n36}{r26}/{e} {h0:^15}    {r38}\\{e}{n49}{r49}_____{e}{n5a} __ SHEEP
                            \\  {r24}/{e}    {y1}    {r36}\\{e}   {h0t:^2}      {r48}/{e}   {y11}     {r5a}\\{e}  /
                     {n23}{r23}_____{e}{n34}{r24}/{e}  {h1:^15}   {r36}\\{e}{n47}{r47}_____{e}{n58}{r48}/{e} {h11:^15}    {r5a}\\{e}{n6b}{r6b}_____{e}{n7c}
                    {r22}/{e}   {y2}     {r34}\\{e}   {h1t:^2}      {r46}/{e}   {y12}     {r58}\\{e}    {h11t:^2}     {r6a}/{e}   {y10}     {r7c}\\{e}
                 {n32}{r22}/{e}   {h2:^15}  {r34}\\{e}{n45}{r45}_____{e}{n56}{r46}/{e}   {h12:^15}  {r58}\\{e}{n69}{r69}_____{e}{n7a}{r6a}/{e}   {h10:^15}  {r7c}\\{e}{n8d}
                   {r32}\\{e}   {h2t:^2}      {r44}/{e}   {y13}     {r56}\\{e}   {h12t:^2}      {r68}/{e}   {y17}     {r7a}\\{e}   {h10t:^2}      {r8c}/{e}
           WHEAT __ {r32}\\{e}{n43}{r43}_____{e}{n54}{r44}/{e}   {h13:^15}  {r56}\\{e}{n67}{r67}_____{e}{n78}{r68}/{e}   {h17:^15}  {r7a}\\{e}{n8b}{r8b}_____{e}{n9c}{r8c}/{e} __ 3:1
                 \\  {r42}/{e}   {y3}     {r54}\\{e}   {h13t:^2}      {r66}/{e}   {y18}     {r78}\\{e}   {h17t:^2}      {r8a}/{e}   {y9}     {r9c}\\{e}  /
                 {n52}{r42}/{e} {h3:^15}    {r54}\\{e}{n65}{r65}_____{e}{n76}{r66}/{e}   {h18:^15}  {r78}\\{e}{n89}{r89}_____{e}{n9a}{r8a}/{e}   {h9:^15}  {r9c}\\{e}{nad}
                   {r52}\\{e}   {h3t:^2}      {r64}/{e}   {y14}     {r76}\\{e}   {h18t:^2}      {r88}/{e}   {y16}     {r9a}\\{e}   {h9t:^2}      {rac}/{e}
                    {r52}\\{e}{n63}{r63}_____{e}{n74}{r64}/{e}   {h14:^15}  {r76}\\{e}{n87}{r87}_____{e}{n98}{r88}/{e}   {h16:^15}  {r9a}\\{e}{nab}{rab}_____{e}{nbc}{rac}/{e}
                    {r62}/{e}   {y4}     {r74}\\{e}   {h14t:^2}      {r86}/{e}   {y15}     {r98}\\{e}   {h16t:^2}      {raa}/{e}   {y8}     {rbc}\\{e}
                 {n72}{r62}/{e} {h4:^15}    {r74}\\{e}{n85}{r85}_____{e}{n96}{r86}/{e}   {h15:^15}  {r98}\\{e}{na9}{ra9}_____{e}{nba}{raa}/{e}   {h8:^15}  {rbc}\\{e}{ncd}
                 / {r72}\\{e}   {h4t:^2}      {r84}/{e}   {y5}     {r96}\\{e}   {h15t:^2}      {ra8}/{e}   {y7}     {rba}\\{e}   {h8t:^2}      {rcc}/{e} \\
             3:1 __ {r72}\\{e}{n83}{r83}_____{e}{n94}{r84}/{e} {h5:^15}    {r96}\\{e}{na7}{ra7}_____{e}{nb8}{ra8}/{e}  {h7:^15}   {rba}\\{e}{ncb}{rcb}_____{e}{ndc}{rcc}/{e} __ 3:1
                              {r94}\\{e}   {h5t:^2}      {ra6}/{e}   {y6}     {rb8}\\{e}   {h7t:^2}      {rca}/{e}
                               {r94}\\{e}{na5}{ra5}_____{e}{nb6}{ra6}/{e}   {h6:^15}  {rb8}\\{e}{nc9}{rc9}_____{e}{nda}{rca}/{e}
                                  |    / {rb6}\\{e}   {h6t:^2}      {rc8}/{e} \\    |
                                  FOREST  {rb6}\\{e}{nc7}{rc7}_____{e}{nd8}{rc8}/{e}   BRICK

                     {legend}""".format(**d)

    def __str__(self) -> str:
        def player_color(player):
            return self.__player_colors[self.__players.index(player)]

        def get_color(edge, is_edge=True):
            coords = self.edges() if is_edge else self.nodes()
            if coords.get(edge) is not None:
                return self.__player_colors[self.__players.index(coords.get(edge).player())]
            else:
                return Board.COLORS['END']

        def get_node_str(node):
            if self.nodes().get(node) is not None:
                if self.nodes().get(node).type() == Consts.PurchasableType.SETTLEMENT:
                    return 's'
                else:
                    return 'C'
            else:
                return ' '

        dh = {f'h{i}': str(h) for i, h in enumerate(self.hexes())}
        dht = {f'h{i}t': h.token() for i, h in enumerate(self.hexes())}
        x = 'x'
        dr = {f'r{hex(edge).split(x)[1]}': get_color(edge) for edge in hexgrid.legal_edge_coords()}
        legend = ' '.join('{}{}{}'.format(player_color(player), player, Board.COLORS['END'])
                          for player in self.__players)
        detc = {'e': Board.COLORS['END'], 'legend': legend}
        dn = {f'n{hex(node).split(x)[1]}': '{}{}{}'.format(get_color(node, is_edge=False), get_node_str(node),
                                                           Board.COLORS['END']) for node in hexgrid.legal_node_coords()}
        dy = {f'y{i}': 'R' if h.has_robber() else ' ' for i, h in enumerate(self.hexes())}
        d = dict()
        for other_dict in (dh, dht, dr, dn, dy, detc):
            for key, value in other_dict.items():
                d[key] = value

        return """
                                  3:1
                                 /   \\
                                {n27}{r27}_____{e}{n38}           
                               {r26}/{e}   {y0}   {r38}\\{e}         
                ORE __ {n25}{r25}_____{e}{n36}{r26}/{e} {h0:^15}  {r38}\\{e}{n49}{r49}_____{e}{n5a} __ SHEEP
                   \\  {r24}/{e}   {y1}   {r36}\\{e}   {h0t:^2}    {r48}/{e}   {y11}   {r5a}\\{e}  /
              {n23}{r23}_____{e}{n34}{r24}/{e} {h1:^15}  {r36}\\{e}{n47}{r47}_____{e}{n58}{r48}/{e} {h11:^15}  {r5a}\\{e}{n6b}{r6b}_____{e}{n7c}
             {r22}/{e}   {y2}   {r34}\\{e}   {h1t:^2}    {r46}/{e}   {y12}   {r58}\\{e}   {h11t:^2}    {r6a}/{e}   {y10}   {r7c}\\{e}
           {n32}{r22}/{e} {h2:^15}  {r34}\\{e}{n45}{r45}_____{e}{n56}{r46}/{e} {h12:^15}  {r58}\\{e}{n69}{r69}_____{e}{n7a}{r6a}/{e} {h10:^15}  {r7c}\\{e}{n8d}
            {r32}\\{e}   {h2t:^2}    {r44}/{e}   {y13}   {r56}\\{e}   {h12t:^2}    {r68}/{e}   {y17}   {r7a}\\{e}   {h10t:^2}    {r8c}/{e}
    WHEAT __ {r32}\\{e}{n43}{r43}_____{e}{n54}{r44}/{e} {h13:^15}  {r56}\\{e}{n67}{r67}_____{e}{n78}{r68}/{e} {h17:^15}  {r7a}\\{e}{n8b}{r8b}_____{e}{n9c}{r8c}/{e} __ 3:1
          \\  {r42}/{e}   {y3}   {r54}\\{e}   {h13t:^2}    {r66}/{e}   {y18}   {r78}\\{e}   {h17t:^2}    {r8a}/{e}   {y9}   {r9c}\\{e}  /
           {n52}{r42}/{e} {h3:^15}  {r54}\\{e}{n65}{r65}_____{e}{n76}{r66}/{e} {h18:^15}  {r78}\\{e}{n89}{r89}_____{e}{n9a}{r8a}/{e} {h9:^15}  {r9c}\\{e}{nad}
            {r52}\\{e}   {h3t:^2}    {r64}/{e}   {y14}   {r76}\\{e}   {h18t:^2}    {r88}/{e}   {y16}   {r9a}\\{e}   {h9t:^2}    {rac}/{e}
             {r52}\\{e}{n63}{r63}_____{e}{n74}{r64}/{e} {h14:^15}  {r76}\\{e}{n87}{r87}_____{e}{n98}{r88}/{e}  {h16:^15} {r9a}\\{e}{nab}{rab}_____{e}{nbc}{rac}/{e}
             {r62}/{e}   {y4}   {r74}\\{e}   {h14t:^2}    {r86}/{e}   {y15}   {r98}\\{e}   {h16t:^2}    {raa}/{e}   {y8}   {rbc}\\{e}
           {n72}{r62}/{e} {h4:^15}  {r74}\\{e}{n85}{r85}_____{e}{n96}{r86}/{e} {h15:^15}  {r98}\\{e}{na9}{ra9}_____{e}{nba}{raa}/{e} {h8:^15}  {rbc}\\{e}{ncd}
          / {r72}\\{e}   {h4t:^2}    {r84}/{e}   {y5}   {r96}\\{e}   {h15t:^2}    {ra8}/{e}   {y7}   {rba}\\{e}   {h8t:^2}    {rcc}/{e} \\
      3:1 __ {r72}\\{e}{n83}{r83}_____{e}{n94}{r84}/{e} {h5:^15}  {r96}\\{e}{na7}{ra7}_____{e}{nb8}{ra8}/{e} {h7:^15}  {rba}\\{e}{ncb}{rcb}_____{e}{ndc}{rcc}/{e} __ 3:1
                     {r94}\\{e}   {h5t:^2}    {ra6}/{e}   {y6}   {rb8}\\{e}   {h7t:^2}    {rca}/{e}
                      {r94}\\{e}{na5}{ra5}_____{e}{nb6}{ra6}/{e} {h6:^15}  {rb8}\\{e}{nc9}{rc9}_____{e}{nda}{rca}/{e}
                       |    / {rb6}\\{e}   {h6t:^2}    {rc8}/{e} \\    |
                       FOREST  {rb6}\\{e}{nc7}{rc7}_____{e}{nd8}{rc8}/{e}   BRICK

             {legend}""".format(**d)
