import numpy as np
from geneticalgorithm import geneticalgorithm as ga
from Heuristics import *
import GameSession
import Player
import Agent

"""This module trains an agent using the Everything Heuristic via Genetic Algorithm"""


def objective_function(weights):
    h = Everything(weights=tuple(weights))
    val = 0
    a = Agent.OneMoveHeuristicAgent(h)
    a2 = Agent.OneMoveHeuristicAgent(Everything())
    for i in range(2):
        p1 = Player.Player(a, 'Roy')
        p2 = Player.Player(a2, 'Boaz')
        p3 = Player.Player(a2, 'Amoss')
        session = GameSession.GameSession(None, p1, p2, p3)
        session.run_game()
        val += p1.vp() - p2.vp() - p3.vp()
    return -val


if __name__ == '__main__':
    varbound = np.array([[0, 1]] * 9)
    model = ga(function=objective_function, dimension=9, variable_type='real', variable_boundaries=varbound,
               function_timeout=6000)
    model.run()
