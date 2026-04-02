class Player:
    def __init__(self, name, player_type="human"):
        self.name = name
        self.chips = 30
        self.player_type = player_type
        self.current_position = None
        self.chips_spent_this_round = 0

    def place_bet(self, amount):
        if amount > self.chips:
            amount = self.chips
        self.chips -= amount
        self.chips_spent_this_round += amount
        return amount

    def vote(self, position):
        self.current_position = position

    def ask_question(self, question):
        return question

    def formulate_response(self, question):
        return f"Ответ игрока {self.name} на вопрос: {question}"


import random

class AIAgent(Player):
    def __init__(self, name, personality_type):
        super().__init__(name, 'ai')
        self.personality = personality_type
        self.strategy = self.load_strategy()

    def load_strategy(self):
        return {"risk_tolerance": 0.5, "bluff_frequency": 0.3}

    def evaluate_statement(self, statement):
        return self.personality.evaluate_statement(statement)

    def generate_question(self, statement, context):
        # Делегируем вопрос в personality класс, который использует ИИ
        if hasattr(self.personality, 'generate_question'):
            return self.personality.generate_question(statement, context)

        # Fallback только если personality не поддерживает generate_question
        questions = [
            f"Можете ли вы привести пример из жизни, подтверждающий '{statement}'?",
            f"Как вы объясните противоположную точку зрения по поводу '{statement}'?",
            f"В каких случаях '{statement}' может быть неверным?"
        ]
        return random.choice(questions)

    def decide_position(self, statement, round_context):
        result = self.evaluate_statement(statement)
        if len(result) == 3:
            position, confidence, reasoning = result
        else:
            position, confidence = result
        return position

    def calculate_risk(self, current_chips, potential_loss):
        return min(1.0, potential_loss / max(current_chips, 1))