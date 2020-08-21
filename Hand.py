from __future__ import annotations  # for Hand type hints inside Hand
from typing import Type, Union
import GameConstants as Consts
from collections import defaultdict
from random import choice


class Hand:
    """
    represents a bundle of resources (or one), and number of operations that
    can be made (adding cards, removing cards, etc.)
    """

    def __init__(self, *cards: Consts.CardType):
        self.__cards = defaultdict(int)
        for card in cards:
            self.__cards[card] += 1

    def insert(self, cards: Hand) -> None:
        """Add cards (as a hand object) to this hand"""
        for card in cards:
            self.__cards[card] += 1

    def remove(self, cards: Hand) -> None:
        """Remove cards (as a hand object) from this hand. Raises ValueError
        if not enough cards are present"""
        for card, amount in cards.__cards.items():
            num_in_hand = self.__cards[card]
            if num_in_hand < amount:
                raise ValueError(
                    f'{num_in_hand} {card} cards in hand, tried to remove '
                    f'{amount}')
            self.__cards[card] -= amount

    def remove_as_much(self, cards: Hand) -> Hand:
        """

        :param cards:
        :return:
        """
        removed = Hand()
        for card in cards:
            single_hand = Hand(card)
            if self.contains(single_hand):
                self.remove(single_hand)
                removed.insert(single_hand)
        return removed

    def remove_by_type(self, card_type: Consts.CardType) -> Hand:
        """

        :param card_type:
        :return:
        """
        num_type = self.__cards[card_type]
        hand_to_remove = Hand(*[card_type] * num_type)
        self.remove(hand_to_remove)
        return hand_to_remove

    def contains(self, hand: Hand) -> bool:
        """
        :return: True if the current cards bundle contains
        the given "Hand" object, else: False
        """
        for card, amount in hand.__cards.items():
            if self.__cards[card] < amount:
                return False
        return True

    def devs(self) -> Hand:
        """
        :return: development cards in hand
        """
        return self.cards_of_class(Consts.DevType)

    def resources(self) -> Hand:
        """
        :return: resource cards in hand
        """
        return self.cards_of_class(Consts.ResourceType)

    def size(self) -> int:
        """
        :return: the number of cards the "Hand" object holds
        """
        return sum(self.__cards.values())

    def cards_of_type(self, card: Consts.CardType) -> Hand:
        return Hand(*(c for c in self if card == c))

    def cards_of_class(self, ctype: Type[Consts.CardType]) -> Hand:
        """return iterator of cards in hand that correspond to class ctype (
        i.e. ctype == DevType)"""
        return Hand(*(card for card in self if isinstance(card, ctype)))

    def remove_random_card(self) -> Hand:
        """
        removes a random card from the hand
        :return: the removed card
        """
        deck = [card for card in self]
        if not deck:
            raise ValueError('cannot remove card, no cards left')
        to_remove = Hand(choice(deck))
        self.remove(to_remove)
        return to_remove

    def map_resources_by_quantity(self) -> dict:
        """
        maps the hand of the player to a dictionary:
        keys: resources, values: occurences
        :return:
        """
        return self.__cards


    def get_cards_types(self):
        """
        :return: the types of cards the current Hand has
        """
        return set(self.resources())

    def __iter__(self) -> Union[Consts.DevType, Consts.ResourceType]:
        """returns iterator that iterates over every card type in the hand"""
        for card, count in self.__cards.items():
            for _ in range(count):
                yield card

    def __str__(self) -> str:
        """a printable representation of the hand"""
        return f'{[str(card) for card in self]}'

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __eq__(self, other: Hand) -> bool:
        return other.contains(self) and self.contains(other)
