#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полный тест механики единогласного несогласия
"""

from game.game_engine import Game
from game.player import Player, AIAgent
from ai.personalities import SkepticalPersonality, PedanticPersonality, PragmaticPersonality, SynthesizerPersonality

def test_unanimous_disagreement_flow():
    """Тестирует полный поток единогласного несогласия"""

    print("=== ТЕСТ МЕХАНИКИ ЕДИНОГЛАСНОГО НЕСОГЛАСИЯ ===")

    # Создаем игру
    game = Game()

    # Создаем игроков вручную для тестирования
    game.players = [
        Player("Тестовый_Человек"),
        AIAgent("Скептик", SkepticalPersonality()),
        AIAgent("Педант", PedanticPersonality()),
        AIAgent("Прагматик", PragmaticPersonality()),
        AIAgent("Синтезатор", SynthesizerPersonality())
    ]

    # Инициализируем состояние
    game.current_philosopher = 0
    game.round_state = {}

    # Выбираем спорное утверждение, которое все отвергнут
    from game.card import Card
    controversial_card = Card("Пытки допустимы для спасения невинных жизней", "ethics")

    print(f"Тестовое утверждение: '{controversial_card.statement}'")

    # Симулируем этап утверждения
    print("\n[СИМУЛЯЦИЯ] Философ выбирает позицию...")
    game.round_state['philosopher_position'] = 'disagree'
    game.round_state['statement'] = controversial_card.statement

    # Симулируем позиционирование (все disagree)
    print("\n[СИМУЛЯЦИЯ] Все игроки выбирают позицию...")
    positions = {}
    bets = {}

    for player in game.players:
        # Заставляем всех выбрать disagree
        positions[player.name] = 'disagree'
        player.current_position = 'disagree'
        bets[player.name] = 3  # Средняя ставка

    game.round_state['bets'] = bets

    print("Позиции:")
    for name, position in positions.items():
        print(f"  {name}: {position}")

    # Проверяем консенсус
    print("\n[ТЕСТИРОВАНИЕ] Проверка консенсуса...")
    consensus_result = game._check_consensus(positions)

    if consensus_result:
        print("[ОШИБКА] Консенсус вернул True - раунд завершился!")
        print("Это неправильно! При единогласном несогласии должно быть исправление.")
        return False
    else:
        print("[УСПЕХ] Консенсус вернул False - раунд продолжается")

    # Тестируем сократовский диалог с единогласным несогласием
    print("\n[ТЕСТИРОВАНИЕ] Запуск сократовского диалога...")

    try:
        # Симулируем вызов сократовского диалога
        # Этот метод должен обнаружить единогласное несогласие и запросить улучшение
        game._socratic_dialogue_phase(controversial_card, positions, depth=1)
        print("[УСПЕХ] Сократовский диалог обработал единогласное несогласие")
        return True

    except Exception as e:
        print(f"[ОШИБКА] Ошибка в сократовском диалоге: {e}")
        return False

def test_ai_statement_improvement():
    """Тестирует улучшение утверждений ИИ-философами"""

    print("\n=== ТЕСТ УЛУЧШЕНИЯ УТВЕРЖДЕНИЙ ИИ ===")

    game = Game()

    # Создаем ИИ-философов
    philosophers = [
        AIAgent("Скептик", SkepticalPersonality()),
        AIAgent("Педант", PedanticPersonality()),
        AIAgent("Прагматик", PragmaticPersonality()),
        AIAgent("Синтезатор", SynthesizerPersonality())
    ]

    original_statement = "Все религии являются ложными"

    print(f"Исходное спорное утверждение: '{original_statement}'")
    print("\nИИ-философы предлагают улучшения:")

    for philosopher in philosophers:
        try:
            improved = game._ai_improve_statement(philosopher, original_statement)
            print(f"  {philosopher.name}: '{improved}'")
        except Exception as e:
            print(f"  {philosopher.name}: [ОШИБКА] {e}")

if __name__ == "__main__":
    success = test_unanimous_disagreement_flow()
    test_ai_statement_improvement()

    if success:
        print("\n[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Механика единогласного несогласия работает корректно")
    else:
        print("\n[ERROR] ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        print("Требуется дополнительная отладка")