from .openai_client import OpenAIClient
import random

class NeuralPersonality:
    """Базовый класс для ИИ-личностей на основе нейросетей"""

    def __init__(self, personality_type: str):
        self.personality_type = personality_type
        self.openai_client = OpenAIClient()

    def evaluate_statement(self, statement):
        """Оценка утверждения через нейросеть"""
        try:
            position, confidence, reasoning = self.openai_client.evaluate_statement(
                self.personality_type, statement
            )
            return position, confidence, reasoning
        except Exception as e:
            print(f"🔥 Ошибка в evaluate_statement: {e}")
            return self._fallback_evaluate(statement)

    def generate_question(self, statement, context):
        """Генерация вопроса через нейросеть"""
        try:
            return self.openai_client.generate_question(
                self.personality_type, statement, context
            )
        except Exception as e:
            print(f"🔥 Ошибка в generate_question: {e}")
            return self._fallback_question(statement)

    def generate_argument(self, statement, position):
        """Генерация аргумента через нейросеть"""
        try:
            return self.openai_client.generate_argument(
                self.personality_type, statement, position
            )
        except Exception as e:
            print(f"🔥 Ошибка в generate_argument: {e}")
            return self._fallback_argument(position)

    def generate_response(self, question, statement):
        """Ответ на вопрос через нейросеть"""
        try:
            return self.openai_client.generate_response(
                self.personality_type, question, statement
            )
        except Exception as e:
            print(f"[ERROR] Ошибка в generate_response: {e}")
            return self._fallback_response()

    def make_final_vote(self, dialogue_context):
        """Финальное голосование через нейросеть"""
        try:
            return self.openai_client.make_final_vote(
                self.personality_type, dialogue_context
            )
        except Exception as e:
            print(f"[ERROR] Ошибка в make_final_vote: {e}")
            return random.choice([True, False])

    def _fallback_evaluate(self, statement):
        """Fallback логика если ИИ недоступен"""
        return 'agree', 0.5, 'Нейросеть недоступна'

    def _fallback_question(self, statement):
        return "Можете ли вы привести примеры?"

    def _fallback_argument(self, position):
        return f"Моя позиция основана на логическом анализе"

    def _fallback_response(self):
        return "Это требует дополнительного обдумывания"

    def improve_statement(self, original_statement):
        """Улучшение утверждения через нейросеть"""
        try:
            return self.openai_client.improve_statement(
                self.personality_type, original_statement
            )
        except Exception as e:
            print(f"[ERROR] Ошибка в improve_statement: {e}")
            return self._fallback_improve_statement(original_statement)

    def _fallback_improve_statement(self, original_statement):
        """Fallback улучшение утверждения"""
        return f"В некоторых случаях {original_statement.lower()}"

class SkepticalPersonality(NeuralPersonality):
    """🤔 Философ-скептик с использованием нейросети"""

    def __init__(self):
        super().__init__('skeptic')

class PedanticPersonality(NeuralPersonality):
    """📚 Философ-педант с использованием нейросети"""

    def __init__(self):
        super().__init__('pedant')

class PragmaticPersonality(NeuralPersonality):
    """🛠️ Философ-прагматик с использованием нейросети"""

    def __init__(self):
        super().__init__('pragmatist')

class SynthesizerPersonality(NeuralPersonality):
    """🔄 Философ-синтезатор с использованием нейросети"""

    def __init__(self):
        super().__init__('synthesizer')

# Backward compatibility - старые методы для тестов
class CompatibilityMixin:
    def evaluate_statement_simple(self, statement):
        """Старый интерфейс для обратной совместимости"""
        position, confidence, _ = self.evaluate_statement(statement)
        return position, confidence

# Применяем совместимость ко всем классам
for cls in [SkepticalPersonality, PedanticPersonality, PragmaticPersonality, SynthesizerPersonality]:
    cls.__bases__ = cls.__bases__ + (CompatibilityMixin,)