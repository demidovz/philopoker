import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.personalities import SkepticalPersonality, PedanticPersonality, PragmaticPersonality, SynthesizerPersonality
from game.player import AIAgent

class TestAIPersonalities(unittest.TestCase):
    def setUp(self):
        self.skeptic = SkepticalPersonality()
        self.pedant = PedanticPersonality()
        self.pragmatist = PragmaticPersonality()
        self.synthesizer = SynthesizerPersonality()

    def test_skeptical_personality(self):
        result = self.skeptic.evaluate_statement("Все люди всегда говорят правду")
        self.assertEqual(result[0], 'disagree')
        self.assertGreater(result[1], 0.5)

        result = self.skeptic.evaluate_statement("Большинство людей стремятся к добру")
        self.assertEqual(result[0], 'agree')
        self.assertLess(result[1], 0.5)

    def test_ai_agent_creation(self):
        agent = AIAgent("Тест", self.skeptic)
        self.assertEqual(agent.name, "Тест")
        self.assertEqual(agent.player_type, "ai")
        self.assertIsNotNone(agent.personality)

    def test_ai_agent_question_generation(self):
        agent = AIAgent("Тест", self.skeptic)
        question = agent.generate_question("Тестовое утверждение", {})
        self.assertIsInstance(question, str)
        self.assertGreater(len(question), 10)

if __name__ == '__main__':
    unittest.main()