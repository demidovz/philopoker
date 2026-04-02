import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game.game_engine import Game
from game.player import Player, AIAgent
from game.card import Card
from ai.personalities import SkepticalPersonality

class TestGame(unittest.TestCase):
    def setUp(self):
        self.game = Game()

    def test_game_initialization(self):
        self.assertEqual(self.game.current_round, 0)
        self.assertEqual(self.game.current_philosopher, 0)
        self.assertIsInstance(self.game.cards, list)
        self.assertGreater(len(self.game.cards), 0)

    def test_add_human_player(self):
        initial_count = len(self.game.players)
        self.game.add_player("Тестовый игрок")
        self.assertEqual(len(self.game.players), initial_count + 1)
        self.assertEqual(self.game.players[-1].name, "Тестовый игрок")
        self.assertEqual(self.game.players[-1].player_type, "human")

    def test_add_ai_player(self):
        initial_count = len(self.game.players)
        self.game.add_player("ИИ игрок", is_ai=True, personality_type='skeptic')
        self.assertEqual(len(self.game.players), initial_count + 1)
        self.assertIsInstance(self.game.players[-1], AIAgent)
        self.assertEqual(self.game.players[-1].name, "ИИ игрок")

    def test_card_loading(self):
        self.assertGreater(len(self.game.cards), 15)
        first_card = self.game.cards[0]
        self.assertIsInstance(first_card, Card)
        self.assertIn(first_card.category, ['ethics', 'metaphysics', 'epistemology', 'logic', 'aesthetics'])

if __name__ == '__main__':
    unittest.main()