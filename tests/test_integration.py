import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game.game_engine import Game
from game.player import Player
from game.card import Card

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.add_player("Человек")
        self.game.add_player("ИИ1", is_ai=True, personality_type='skeptic')
        self.game.add_player("ИИ2", is_ai=True, personality_type='pedant')

    def test_full_game_setup(self):
        self.assertEqual(len(self.game.players), 3)
        self.assertTrue(any(p.player_type == "human" for p in self.game.players))
        self.assertTrue(any(p.player_type == "ai" for p in self.game.players))

    def test_player_betting(self):
        player = self.game.players[0]
        initial_chips = player.chips
        bet_amount = player.place_bet(5)

        self.assertEqual(bet_amount, 5)
        self.assertEqual(player.chips, initial_chips - 5)
        self.assertEqual(player.chips_spent_this_round, 5)

    def test_card_system(self):
        initial_card_count = len(self.game.cards)
        card = self.game.cards[0]

        self.assertIsInstance(card, Card)
        self.assertIsInstance(card.statement, str)
        self.assertIn(card.category, ['ethics', 'metaphysics', 'epistemology', 'logic', 'aesthetics'])

    def test_game_logging(self):
        initial_log_count = len(self.game.game_state.game_log)
        self.game.log_action("test_action", "test_player", {"test": "data"})

        self.assertEqual(len(self.game.game_state.game_log), initial_log_count + 1)
        last_log = self.game.game_state.game_log[-1]
        self.assertEqual(last_log['action'], 'test_action')
        self.assertEqual(last_log['player'], 'test_player')

if __name__ == '__main__':
    unittest.main()