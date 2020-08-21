from typing import Tuple
from random import randint

PROBABILITIES = {
    0:  0,
    2:  1/36,
    3:  2/36,
    4:  3/36,
    5:  4/36,
    6:  5/36,
    7:  6/36,
    8:  5/36,
    9:  4/36,
    10: 3/36,
    11: 2/36,
    12: 1/36,
}


class Dice:
    """Class representing a fair pair of dice"""
    def __init__(self):
        self.__last_roll = self.roll()
        self.__sum = sum(self.__last_roll)

    def roll(self) -> Tuple[int, int]:
        """roll the dice, returns result"""
        self.__last_roll = randint(1, 6), randint(1, 6)
        self.__sum = sum(self.__last_roll)
        return self.__last_roll

    def get_last_roll(self) -> Tuple[int, int]:
        """:returns the last dice roll"""
        return self.__last_roll

    def sum(self) -> int:
        """:returns the sum of the last dice roll"""
        return self.__sum

    def info(self) -> str:
        """:returns an informative string about these dice"""
        return f'[DICE] current roll = {self.get_last_roll()}, sum = {self.sum()}'
