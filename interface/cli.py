import os

class CLI:
    def __init__(self):
        self.game = None

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_header(self):
        print("=" * 50)
        print("          ФИЛОСОФСКИЙ БЛЕФ")
        print("=" * 50)

    def display_players_status(self, players):
        print("\nСостояние игроков:")
        for i, player in enumerate(players):
            status = "СОГЛАСЕН" if player.current_position == "agree" else "НЕ СОГЛАСЕН" if player.current_position == "disagree" else "НЕ ОПРЕДЕЛИЛСЯ"
            print(f"{i+1}. {player.name}: {player.chips} фишек [{status}]")

    def display_card(self, card, philosopher_name):
        print(f"\nФилософ: {philosopher_name}")
        print(f"Категория: {card.category.upper()}")
        print(f"Утверждение: {card.statement}")
        print("-" * 50)

    def get_user_position(self):
        while True:
            position = input("Ваша позиция (agree/disagree): ").strip().lower()
            if position in ['agree', 'disagree']:
                return position
            print("Пожалуйста, введите 'agree' или 'disagree'")

    def get_user_bet(self, max_chips):
        while True:
            try:
                bet = int(input(f"Ваша ставка (1-{max_chips}): "))
                if 1 <= bet <= max_chips:
                    return bet
                print(f"Ставка должна быть от 1 до {max_chips}")
            except ValueError:
                print("Пожалуйста, введите число")

    def get_user_question(self):
        return input("Ваш критический вопрос: ")

    def get_user_response(self):
        return input("Ваш ответ: ")

    def get_user_vote(self):
        while True:
            vote = input("Философ говорит правду? (truth/lie): ").strip().lower()
            if vote in ['truth', 'lie']:
                return vote
            print("Пожалуйста, введите 'truth' или 'lie'")

    def display_round_result(self, winner_names, winnings):
        print(f"\nПобедители раунда: {', '.join(winner_names)}")
        print(f"Выигрыш: {winnings} фишек каждому")

    def display_game_over(self, final_standings):
        self.clear_screen()
        self.display_header()
        print("\n🏆 ИГРА ЗАВЕРШЕНА! 🏆")
        print("\nИтоговые результаты:")
        for i, (name, chips) in enumerate(final_standings):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "   "
            print(f"{medal} {i+1}. {name}: {chips} фишек")

        print(f"\n🎉 Поздравляем победителя: {final_standings[0][0]}! 🎉")

    def pause(self):
        input("\nНажмите Enter для продолжения...")