import json
from datetime import datetime

class GameState:
    def __init__(self):
        self.current_round = 0
        self.current_philosopher = 0
        self.round_state = {}
        self.game_log = []

    def log_action(self, action, player_name, details=None):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'round': self.current_round,
            'action': action,
            'player': player_name,
            'details': details or {}
        }
        self.game_log.append(log_entry)

    def save_game(self, filename):
        game_data = {
            'current_round': self.current_round,
            'current_philosopher': self.current_philosopher,
            'game_log': self.game_log,
            'timestamp': datetime.now().isoformat()
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, ensure_ascii=False, indent=2)

    def load_game(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        self.current_round = game_data['current_round']
        self.current_philosopher = game_data['current_philosopher']
        self.game_log = game_data['game_log']