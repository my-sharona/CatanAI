import GameSession
from typing import List
from random import sample
import Player
import Agent
import Heuristics
import argparse

DEFAULT_NUM_PLAYERS = 4
RANDOM_AGENT = 'random'
ONE_MOVE_AGENT = 'onemove'
HUMAN_AGENT = 'human'
PROBABILITY_AGENT = 'prob'
MONTECARLO_AGENT = 'monte'
GENETIC_AGENT = 'genetic'
# gen 19 #
GENETIC2_WEIGHTS = (0.77197979,  # probability      19.8%
                    0.8782323,   # VP               22.5%
                    0.07241402,  # Longest Road      1.9%
                    0.82772027,  # game won         21.2%
                    0.45152069,  # hand size        11.6%
                    0.17718227,  # hand diversity    4.5%
                    0.37266962,  # dev cards         9.5%
                    0.15663299,  # can buy           4.0%
                    0.19536229)  # opp score         5.0%

# gen 32 #
GENETIC1_WEIGHTS = (0.46428154,  # probability      11.3%
                    0.82164505,   # VP              20.0%
                    0.59430118,  # Longest Road     14.5%
                    0.33544462,  # game won          8.2%
                    0.18126786,  # hand size         4.4%
                    0.05332921,  # hand diversity    1.3%
                    0.94682948,  # dev cards        23.0%
                    0.26080832,  # can buy           6.3%
                    0.45609072)  # opp score        11.1%

AGENTS = {
    RANDOM_AGENT: Agent.RandomAgent(),
    ONE_MOVE_AGENT: Agent.OneMoveHeuristicAgent(Heuristics.AmossComb1()),
    HUMAN_AGENT: Agent.HumanAgent(),
    PROBABILITY_AGENT: Agent.ProbabilityAgent(),
    MONTECARLO_AGENT: Agent.MonteCarloAgent(Heuristics.Everything()),
    GENETIC_AGENT: Agent.MonteCarloAgent(Heuristics.Everything(weights=GENETIC2_WEIGHTS))
}
DEFAULT_AGENTS = [RANDOM_AGENT]
PLAYER_NAMES = ['Roy', 'Boaz', 'Oriane', 'Amoss']


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-log',
        metavar="LOG_NAME",
        help='The name of the log file - if not specified, no log file will be generated.'
    )
    parser.add_argument(
        '-agents',
        metavar="AGENT",
        nargs='+',
        choices=list(AGENTS.keys()),
        default=DEFAULT_AGENTS,
        help='Agents to use in the game (if # agents does not match # players, last agent will be re-used as necessary)'
    )
    parser.add_argument(
        '-num_players',
        type=int,
        default=DEFAULT_NUM_PLAYERS,
        help='Number of players to play this round of Catan'
    )
    return parser.parse_args()


def init_players(num_players: int, *agent_types: str) -> List[Player.Player]:
    players = []
    p_names = sample(PLAYER_NAMES, num_players)

    for p_idx in range(num_players):
        agent_type = agent_types[p_idx] if p_idx < len(agent_types) else agent_types[-1]
        agent = AGENTS[agent_type]
        players.append(Player.Player(agent, name=p_names[p_idx]))

    return players


def main(log: str = None, num_players: int = DEFAULT_NUM_PLAYERS, agents: List[str] = DEFAULT_AGENTS,
         **kwargs) -> None:
    players = init_players(num_players, *agents)
    catan_session = GameSession.GameSession(log, *players)
    catan_session.run_game()


if __name__ == '__main__':
    args = get_args()
    main(**vars(args))
    # monte = Agent.MonteCarloAgent(Heuristics.Everything())
    # litemonte = Agent.LiteMonteCarloAgent(Heuristics.Everything(weights=GENETIC2_WEIGHTS))
    # onemove = Agent.OneMoveHeuristicAgent(Heuristics.Everything())
    # p0 = Player.Player(onemove, name='MYSHARONA')
    # p1 = Player.Player(onemove, 'Opp1')
    # p2 = Player.Player(onemove, 'Opp2')
    # p3 = Player.Player(onemove, 'Opp3')
    # g = GameSession.GameSession(p0, p1, p2)
    # g.run_game()
    # print(g.players_luck())
