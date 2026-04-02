import random
import json
from .card import Card
from .player import Player, AIAgent
from .game_state import GameState
from ai.personalities import SkepticalPersonality, PedanticPersonality, PragmaticPersonality, SynthesizerPersonality

class Game:
    def __init__(self):
        self.players = []
        self.current_round = 0
        self.current_philosopher = 0
        self.cards = []
        self.game_log = []
        self.round_state = {}
        self.game_state = GameState()
        self._load_cards()

    def _load_cards(self):
        cards_data = self._get_card_database()
        for category, statements in cards_data.items():
            for statement in statements:
                self.cards.append(Card(statement, category))
        random.shuffle(self.cards)

    def _get_card_database(self):
        return {
            'ethics': [
                "Ложь во спасение морально допустима",
                "Эвтаназия должна быть легализована",
                "Животные имеют права",
                "Пытки допустимы для спасения невинных жизней"
            ],
            'metaphysics': [
                "Свободная воля существует",
                "Время является иллюзией",
                "Сознание может существовать без мозга",
                "Реальность объективна"
            ],
            'epistemology': [
                "Знание возможно без опыта",
                "Истина относительна",
                "Наука дает нам знание о реальности",
                "Интуиция является источником знания"
            ],
            'logic': [
                "Противоречие может быть истинным",
                "Все утверждения либо истинны, либо ложны",
                "Из ложного можно вывести что угодно",
                "Корреляция не означает причинности"
            ],
            'aesthetics': [
                "Красота объективна",
                "Искусство должно служить обществу",
                "Любое творчество является искусством",
                "Эстетический опыт уникален"
            ]
        }

    def add_player(self, name, is_ai=False, personality_type=None):
        if is_ai and personality_type:
            personality_map = {
                'skeptic': SkepticalPersonality(),
                'pedant': PedanticPersonality(),
                'pragmatist': PragmaticPersonality(),
                'synthesizer': SynthesizerPersonality()
            }
            personality = personality_map.get(personality_type, SkepticalPersonality())
            player = AIAgent(name, personality)
        else:
            player = Player(name)
        self.players.append(player)

    def start_game(self):
        print("Добро пожаловать в Философский Блеф!")
        self._setup_players()

        for round_num in range(5):
            self.current_round = round_num + 1
            print(f"\n=== РАУНД {self.current_round} ===")
            self._play_round()

        self._determine_winner()

    def _setup_players(self):
        self.add_player("Игрок", is_ai=False)
        self.add_player("Скептик", is_ai=True, personality_type='skeptic')
        self.add_player("Педант", is_ai=True, personality_type='pedant')
        self.add_player("Прагматик", is_ai=True, personality_type='pragmatist')
        self.add_player("Синтезатор", is_ai=True, personality_type='synthesizer')

    def _play_round(self):
        if not self.cards:
            print("Карточки закончились!")
            return

        current_card = self.cards.pop(0)
        philosopher = self.players[self.current_philosopher]

        print(f"\nФилософ: {philosopher.name}")
        print(f"Утверждение: {current_card}")

        philosopher_position = self._statement_phase(current_card, philosopher)
        positions = self._positioning_phase(current_card)

        if self._check_consensus(positions):
            return

        self._socratic_dialogue_phase(current_card, positions, depth=1)
        self._final_voting(positions)
        self._resolve_round(positions)

        self.current_philosopher = (self.current_philosopher + 1) % len(self.players)

    def _statement_phase(self, card, philosopher):
        print(f"\n[ФАЗА] Утверждение:")
        print(f"Карточка: {card}")
        print(f"Философ: {philosopher.name}")

        if isinstance(philosopher, AIAgent):
            result = philosopher.evaluate_statement(card.statement)
            if len(result) == 3:
                position, confidence, reasoning = result
                print(f"{philosopher.name}: {position} (уверенность: {confidence:.2f})")
            else:
                position, confidence = result
                print(f"{philosopher.name}: {position} (уверенность: {confidence:.2f})")
        else:
            print(f"\n{philosopher.name}, ваша позиция по утверждению '{card.statement}':")
            position = input("Ваша позиция (agree/disagree): ").strip().lower()
            while position not in ['agree', 'disagree']:
                position = input("Введите 'agree' или 'disagree': ").strip().lower()

        self.round_state['philosopher_position'] = position
        self.round_state['statement'] = card.statement
        return position

    def _positioning_phase(self, card):
        print("\n[ФАЗА] Позиционирование:")
        print("Все делают ставки БЕЗ объяснений (сократовский метод)")

        positions = {}
        bets = {}
        total_pot = 0

        for player in self.players:
            # Для человека-философа используем уже выбранную позицию
            if player == self.players[self.current_philosopher] and not isinstance(player, AIAgent):
                position = self.round_state.get('philosopher_position', 'agree')
                print(f"\n{player.name} (философ): уже выбрал {position}")
            elif isinstance(player, AIAgent):
                position = player.decide_position(card.statement, self.round_state)
                print(f"{player.name}: {position}", end="")
            else:
                position = input(f"\n{player.name}, ваша позиция (agree/disagree): ").strip().lower()
                while position not in ['agree', 'disagree']:
                    position = input("Введите 'agree' или 'disagree': ").strip().lower()

            # Ставки для всех
            if isinstance(player, AIAgent):
                bet = min(random.randint(1, 5), player.chips)
                actual_bet = player.place_bet(bet)
                print(f", ставка {actual_bet} фишек")
            else:
                max_bet = min(5, player.chips)
                try:
                    bet = int(input(f"Ставка 1-{max_bet} (чем выше, тем увереннее): "))
                    bet = max(1, min(bet, max_bet))
                except ValueError:
                    bet = 1

                actual_bet = player.place_bet(bet)
                print(f"Поставили {actual_bet} фишек на {position}")

            player.current_position = position
            positions[player.name] = position
            bets[player.name] = actual_bet  # Используем actual_bet вместо chips_spent_this_round
            total_pot += actual_bet

        self.round_state['bets'] = bets
        print(f"\n[БАНК] {total_pot} фишек")
        return positions

    def _check_consensus(self, positions):
        agree_count = list(positions.values()).count('agree')
        disagree_count = list(positions.values()).count('disagree')

        if agree_count == len(self.players):
            print("\n[КОНСЕНСУС] Единогласное согласие! Все возвращают ставки.")
            self._return_all_bets()
            return True
        elif disagree_count == len(self.players):
            print("\n[КОНСЕНСУС] Единогласное несогласие!")
            print("Философ должен предложить исправленное утверждение для углубления...")
            return False  # НЕ завершаем раунд, продолжаем с исправленным утверждением

        print(f"\nМнения разделились: {agree_count} за, {disagree_count} против")
        return False

    def _socratic_dialogue_phase(self, card, positions, depth=1, current_statement=None):
        """Многоуровневый сократовский диалог с углублением"""

        if depth > 100:  # Максимум 100 уровней углубления
            print("[МАКС] Достигнут максимум углубления (100 уровней)")
            return

        statement = current_statement or card.statement
        agree_players = [p for p in self.players if p.current_position == 'agree']
        disagree_players = [p for p in self.players if p.current_position == 'disagree']

        # СПЕЦИАЛЬНЫЙ СЛУЧАЙ: Единогласное несогласие
        if len(agree_players) == 0 and depth == 1:
            print(f"\n[ИСПРАВЛЕНИЕ] Все против утверждения: '{statement}'")
            print("Философ должен предложить исправленное утверждение")

            # Философ предлагает исправленное утверждение
            philosopher = self.players[self.current_philosopher]
            if isinstance(philosopher, AIAgent):
                # ИИ-философ исправляет утверждение
                improved_statement = self._ai_improve_statement(philosopher, statement)
                print(f"[ФИЛОСОФ] {philosopher.name} предлагает: '{improved_statement}'")
            else:
                # Человек-философ исправляет утверждение
                try:
                    improved_statement = input(f"[ФИЛОСОФ] {philosopher.name}, предложите исправленное утверждение: ")
                except EOFError:
                    # Для тестового режима - используем fallback
                    print(f"[ТЕСТОВЫЙ РЕЖИМ] Автоматическое улучшение для {philosopher.name}")
                    improved_statement = f"В некоторых случаях {statement.lower()}"

            # Новое позиционирование по исправленному утверждению
            print(f"\n[ПОВТОРНОЕ ПОЗИЦИОНИРОВАНИЕ] по утверждению: '{improved_statement}'")
            new_positions = self._re_positioning_phase(improved_statement)

            # Обновляем позиции игроков
            for player in self.players:
                player.current_position = new_positions[player.name]

            # Продолжаем с новыми позициями
            agree_players = [p for p in self.players if p.current_position == 'agree']
            disagree_players = [p for p in self.players if p.current_position == 'disagree']
            statement = improved_statement

            # Сохраняем исправленное утверждение
            self.round_state['improved_statement'] = improved_statement

        # Определяем главного защитника (AGREE с максимальной ставкой)
        if agree_players:
            main_defender = max(agree_players, key=lambda p: self.round_state['bets'][p.name])
        else:
            main_defender = None

        print(f"\n[СОКРАТ] ДИАЛОГ (Уровень {depth}):")
        if depth == 1:
            print(f"[ОБСУЖДЕНИЕ] {statement}")
        else:
            print(f"[УГЛУБЛЕНИЕ] {statement}")

        print(f"[+] Согласные ({len(agree_players)}): {[p.name for p in agree_players]}")
        print(f"[?] Несогласные ({len(disagree_players)}): {[p.name for p in disagree_players]}")

        if main_defender:
            print(f"[ЗАЩИТНИК] Главный защитник: {main_defender.name} (ставка: {self.round_state['bets'][main_defender.name]})")

        if not disagree_players:
            print("[ЗАВЕРШЕНО] Нет критиков - диалог завершен")
            return

        if not main_defender:
            print("[ЗАВЕРШЕНО] Нет защитников - диалог завершен")
            return

        # ФАЗА 1: Сбор критических вопросов
        print(f"\n[ФАЗА 1] Сбор критических вопросов")
        collected_questions = []

        for i, questioner in enumerate(disagree_players):
            if isinstance(questioner, AIAgent):
                # Передаем богатый контекст для генерации вопроса
                question_context = {
                    'dialogue_history': self.round_state.get('dialogue_history', []),
                    'statement': self.round_state.get('statement', statement),
                    'current_statement': statement,
                    'depth': depth
                }
                question = questioner.generate_question(statement, question_context)
            else:
                question = input(f"{questioner.name}, ваш критический вопрос: ")

            collected_questions.append((i+1, questioner.name, question))
            print(f"[?] {i+1}. {questioner.name}: {question}")

        # ФАЗА 2: Выбор лучшего вопроса (человек выбирает)
        print(f"\n[ФАЗА 2] Выбор главного вопроса")

        if len(collected_questions) == 1:
            chosen_question = collected_questions[0]
            print(f"📌 Автоматически выбран единственный вопрос")
        else:
            while True:
                try:
                    choice = int(input(f"Выберите номер лучшего вопроса (1-{len(collected_questions)}): "))
                    if 1 <= choice <= len(collected_questions):
                        chosen_question = collected_questions[choice-1]
                        break
                    else:
                        print(f"Введите число от 1 до {len(collected_questions)}")
                except ValueError:
                    print("Введите число")

        question_num, questioner_name, question = chosen_question
        print(f"📌 Выбран вопрос #{question_num}: {question}")

        # ФАЗА 3: Ответ защитника
        print(f"\n[ФАЗА 3] Ответ защитника")
        if isinstance(main_defender, AIAgent):
            response = self._get_ai_response(main_defender, question, statement)
        else:
            response = input(f"[ОТВЕТ] {main_defender.name}, ваш ответ на вопрос: ")

        print(f"[ОТВЕТ] {main_defender.name}: {response}")

        # ФАЗА 4: Автоматическая проверка противоречий
        print(f"\n[ФАЗА 4] Проверка противоречий")
        contradiction_analysis = self._check_contradictions(statement, response)

        if contradiction_analysis['has_contradiction']:
            print(f"[!] ОБНАРУЖЕНО ПРОТИВОРЕЧИЕ!")
            print(contradiction_analysis['formatted_report'])

            # Сохраняем противоречие
            if 'contradictions' not in self.round_state:
                self.round_state['contradictions'] = []
            self.round_state['contradictions'].append(contradiction_analysis)
        else:
            print(f"[OK] Логических противоречий не обнаружено")

        # ФАЗА 5: Проверка желания углубиться
        print(f"\n🤔 ФАЗА 5: Желание углубиться")

        # Сохраняем историю диалога
        if 'dialogue_history' not in self.round_state:
            self.round_state['dialogue_history'] = []

        self.round_state['dialogue_history'].append({
            'depth': depth,
            'statement': statement,
            'question': question,
            'questioner': questioner_name,
            'response': response,
            'defender': main_defender.name
        })

        # Проверяем, хочет ли кто-то углубиться в ответ
        wants_to_deepen = self._check_deepening_desire(response, contradiction_analysis)

        if wants_to_deepen:
            print(f"\n[УГЛУБЛЕНИЕ] Углубляемся в ответ защитника...")
            # Рекурсивно углубляемся, используя ответ как новое утверждение
            self._socratic_dialogue_phase(card, positions, depth + 1, response)
        else:
            print(f"\n[OK] Диалог на уровне {depth} завершен")

    def _check_deepening_desire(self, response, contradiction_analysis):
        """Проверяет, хотят ли игроки углубиться в ответ"""

        # Если обнаружено серьезное противоречие, ИИ более склонен углубляться
        contradiction_bonus = 0
        if contradiction_analysis['has_contradiction']:
            severity = contradiction_analysis.get('severity', 0)
            contradiction_bonus = severity * 0.1  # +10% за каждый балл серьезности

        print(f"\nКто-то хочет оспорить этот ответ и углубиться?")

        for player in self.players:
            if isinstance(player, AIAgent):
                # Базовый шанс + бонус за противоречия
                base_chance = 0.25
                final_chance = min(0.8, base_chance + contradiction_bonus)

                wants_deepen = random.random() < final_chance

                if wants_deepen:
                    if contradiction_analysis['has_contradiction']:
                        print(f"[УГЛУБЛЕНИЕ] {player.name}: Вижу противоречие, хочу углубиться!")
                    else:
                        print(f"[УГЛУБЛЕНИЕ] {player.name}: Хочу углубиться в этот ответ")
                    return True
            else:
                wants_deepen = input(f"{player.name}, хотите оспорить ответ и углубиться? (да/нет): ").strip().lower()
                if wants_deepen in ['да', 'yes', 'y', 'д']:
                    print(f"[УГЛУБЛЕНИЕ] {player.name}: Хочет углубиться")
                    return True

        return False

    def _check_contradictions(self, statement, response):
        """Проверяет ответ на противоречия"""
        from ai.contradiction_checker import ContradictionChecker

        checker = ContradictionChecker()
        dialogue_history = self.round_state.get('dialogue_history', [])

        analysis = checker.check_for_contradictions(
            self.round_state.get('statement', statement),
            response,
            dialogue_history
        )

        # Добавляем форматированный отчет
        analysis['formatted_report'] = checker.format_contradiction_report(analysis)

        return analysis

    def _final_voting(self, positions):
        agree_players = [p for p in self.players if p.current_position == 'agree']
        disagree_players = [p for p in self.players if p.current_position == 'disagree']

        print("\n🗳️ ФИНАЛЬНОЕ ГОЛОСОВАНИЕ:")

        # Показываем краткую историю диалога
        if 'dialogue_history' in self.round_state and self.round_state['dialogue_history']:
            print("\n📖 Краткая история сократовского диалога:")
            for i, entry in enumerate(self.round_state['dialogue_history']):
                level = entry['depth']
                question = entry['question'][:50] + "..." if len(entry['question']) > 50 else entry['question']
                response = entry['response'][:50] + "..." if len(entry['response']) > 50 else entry['response']
                print(f"   {level}. Вопрос: {question}")
                print(f"   {level}. Ответ: {response}")

        main_defender = self.round_state.get('main_defender', 'защитник')
        print(f"\n[ГОЛОСОВАНИЕ] Главный вопрос: В итоге убедил ли {main_defender} своими ответами?")
        print("Учитывайте ВСЕ уровни диалога, не только первый!")

        defender_wins_votes = 0

        for player in self.players:
            if isinstance(player, AIAgent):
                # Создаем расширенный контекст для ИИ
                dialogue_context = {
                    'original_statement': self.round_state.get('statement', ''),
                    'dialogue_history': self.round_state.get('dialogue_history', []),
                    'contradictions': self.round_state.get('contradictions', [])
                }
                vote_result = self._get_ai_vote_with_context(player, dialogue_context)
                vote = 'yes' if vote_result else 'no'
            else:
                vote = input(f"{player.name}, убедил ли защитник в итоге? (yes/no): ").strip().lower()
                while vote not in ['yes', 'no']:
                    vote = input("Введите 'yes' или 'no': ").strip().lower()

            if vote == 'yes':
                defender_wins_votes += 1

            print(f"{player.name}: {'убедил' if vote == 'yes' else 'не убедил'}")

        defender_wins = defender_wins_votes > len(self.players) // 2
        self.round_state['defender_wins'] = defender_wins

        if defender_wins:
            print("\n[OK] Защитник убедительно отстоял позицию через все уровни!")
            print("🏆 Победители: игроки 'AGREE'")
            return True
        else:
            print("\n[ПОБЕДА] Критики успешно подорвали изначальную позицию!")
            print("🏆 Победители: игроки 'DISAGREE'")
            return False

    def _resolve_round(self, positions):
        agree_players = [p for p in self.players if p.current_position == 'agree']
        disagree_players = [p for p in self.players if p.current_position == 'disagree']

        defender_wins = self.round_state.get('defender_wins', False)
        winners = agree_players if defender_wins else disagree_players

        total_pot = sum(p.chips_spent_this_round for p in self.players)

        if winners:
            winnings_per_player = total_pot // len(winners)
            winner_names = [w.name for w in winners]

            print(f"\n[РАСПРЕДЕЛЕНИЕ] Банк ({total_pot} фишек):")
            for winner in winners:
                winner.chips += winnings_per_player
                print(f"[+] {winner.name} получает {winnings_per_player} фишек")

            # Показываем итоговые балансы
            print(f"\n[БАЛАНСЫ] После раунда:")
            for player in self.players:
                print(f"   {player.name}: {player.chips} фишек")

        self._reset_round_state()

    def _return_all_bets(self):
        for player in self.players:
            player.chips += player.chips_spent_this_round
            player.chips_spent_this_round = 0

    def _reset_round_state(self):
        for player in self.players:
            player.chips_spent_this_round = 0
            player.current_position = None
        self.round_state = {}

    def _determine_winner(self):
        print("\n=== ИГРА ЗАВЕРШЕНА ===")
        sorted_players = sorted(self.players, key=lambda p: p.chips, reverse=True)

        print("Итоговые результаты:")
        for i, player in enumerate(sorted_players):
            print(f"{i+1}. {player.name}: {player.chips} фишек")

        winner = sorted_players[0]
        print(f"\nПобедитель: {winner.name} с {winner.chips} фишками!")

    def _get_ai_reasoning(self, agent, statement, position):
        """Получение обоснования от нейросетевого ИИ"""
        if hasattr(agent.personality, 'evaluate_statement'):
            try:
                _, _, reasoning = agent.personality.evaluate_statement(statement)
                return reasoning
            except Exception as e:
                print(f"[ERROR] Ошибка получения обоснования: {e}")

        # Fallback
        reasons = {
            'agree': "Согласен с утверждением",
            'disagree': "Не согласен с утверждением"
        }
        return reasons.get(position, "Без комментариев")

    def _get_ai_response(self, agent, question, statement):
        """Получение ответа от нейросетевого ИИ"""
        if hasattr(agent.personality, 'generate_response'):
            try:
                return agent.personality.generate_response(question, statement)
            except Exception as e:
                print(f"[ERROR] Ошибка получения ответа: {e}")

        # Fallback
        return "Это требует дополнительного анализа"

    def _get_ai_argument(self, agent, statement, position):
        """Получение аргумента от нейросетевого ИИ"""
        if hasattr(agent.personality, 'generate_argument'):
            try:
                return agent.personality.generate_argument(statement, position)
            except Exception as e:
                print(f"[ERROR] Ошибка получения аргумента: {e}")

        # Fallback
        arguments = {
            'agree': "Моя позиция основана на логическом анализе",
            'disagree': "Вижу серьезные противоречия в утверждении"
        }
        return arguments.get(position, "Нет комментариев")

    def _get_ai_vote_with_context(self, agent, dialogue_context):
        """Получение финального голоса от нейросетевого ИИ с полным контекстом"""
        if hasattr(agent.personality, 'make_final_vote'):
            try:
                result = agent.personality.make_final_vote(dialogue_context)
                return result
            except Exception as e:
                print(f"[ERROR] Ошибка получения голоса от {agent.name}: {e}")

        # Fallback с учетом противоречий
        contradictions = dialogue_context.get('contradictions', [])
        if contradictions:
            serious_contradictions = [c for c in contradictions if c.get('severity', 0) >= 7]
            if serious_contradictions:
                return False  # Серьезные противоречия = голос против

        import random
        return random.choice([True, False])

    def _get_ai_vote(self, agent, round_state):
        """Старый метод для обратной совместимости"""
        dialogue_context = {
            'original_statement': round_state.get('statement', ''),
            'dialogue_history': round_state.get('dialogue_history', []),
            'contradictions': round_state.get('contradictions', [])
        }
        result = self._get_ai_vote_with_context(agent, dialogue_context)
        return 'yes' if result else 'no'

    def _create_discussion_summary(self):
        """Создание краткого резюме дискуссии для ИИ"""
        discussion = self.round_state.get('discussion', [])
        if not discussion:
            return "Дискуссия была краткой"

        summary_parts = []
        for q_name, question, r_name, response in discussion:
            summary_parts.append(f"{q_name} спросил: {question[:50]}...")
            summary_parts.append(f"{r_name} ответил: {response[:50]}...")

        return " ".join(summary_parts[:200])  # Ограничиваем длину

    def log_action(self, action, player_name, details=None):
        self.game_state.log_action(action, player_name, details)

    def _ai_improve_statement(self, philosopher, original_statement):
        """ИИ-философ улучшает утверждение на основе критики"""
        if hasattr(philosopher.personality, 'improve_statement'):
            try:
                return philosopher.personality.improve_statement(original_statement)
            except Exception as e:
                print(f"[ERROR] Ошибка улучшения утверждения: {e}")

        # Fallback - простое смягчение утверждения
        soften_phrases = [
            f"В большинстве случаев {original_statement.lower()}",
            f"При определенных условиях {original_statement.lower()}",
            f"Можно утверждать, что {original_statement.lower()}",
            f"Частично верно, что {original_statement.lower()}"
        ]
        import random
        return random.choice(soften_phrases)

    def _re_positioning_phase(self, improved_statement):
        """Повторное позиционирование по исправленному утверждению"""
        print(f"Все игроки заново определяют позицию по утверждению: '{improved_statement}'")

        new_positions = {}

        for player in self.players:
            if isinstance(player, AIAgent):
                # ИИ переоценивает утверждение
                result = player.evaluate_statement(improved_statement)
                if len(result) == 3:
                    position, confidence, reasoning = result
                    print(f"{player.name}: {position} (уверенность: {confidence:.2f})")
                    print(f"  Обоснование: {reasoning}")
                else:
                    position, confidence = result
                    print(f"{player.name}: {position} (уверенность: {confidence:.2f})")
            else:
                # Человек заново выбирает позицию
                print(f"\n{player.name}, ваша позиция по исправленному утверждению:")
                print(f"'{improved_statement}'")
                try:
                    position = input("Ваша позиция (agree/disagree): ").strip().lower()
                    while position not in ['agree', 'disagree']:
                        position = input("Введите 'agree' или 'disagree': ").strip().lower()
                except EOFError:
                    # Для тестового режима - случайная позиция
                    print(f"[ТЕСТОВЫЙ РЕЖИМ] Автоматическая позиция для {player.name}")
                    import random
                    position = random.choice(['agree', 'disagree'])

            new_positions[player.name] = position

        return new_positions