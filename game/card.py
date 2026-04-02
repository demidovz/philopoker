class Card:
    def __init__(self, statement, category, difficulty=1):
        self.statement = statement
        self.category = category
        self.difficulty = difficulty
        self.usage_count = 0

    def __str__(self):
        return f"[{self.category.upper()}] {self.statement}"