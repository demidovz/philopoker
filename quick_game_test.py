#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест игры с новыми вопросами
"""

import sys
from io import StringIO
from game.game_engine import Game
from game.card import Card

def simulate_user_input(inputs):
    """Симулирует пользовательский ввод"""
    input_iter = iter(inputs)
    original_input = __builtins__['input']

    def mock_input(prompt):
        try:
            response = next(input_iter)
            print(f"{prompt}{response}")
            return response
        except StopIteration:
            # Если кончились ответы, используем EOFError
            raise EOFError("No more input")

    __builtins__['input'] = mock_input
    return original_input

def quick_game_test():
    """Быстрый тест игры"""

    print("=== БЫСТРЫЙ ТЕСТ НОВЫХ ВОПРОСОВ ===")

    # Создаем игру
    game = Game()

    # Устанавливаем конкретную карточку для тестирования
    test_card = Card("Время является иллюзией", "metaphysics")
    game.cards = [test_card]

    # Симулируем пользовательский ввод
    user_inputs = [
        "agree",  # позиция по утверждению
        "5",      # ставка (максимальная уверенность)
        "1"       # выбор вопроса №1
    ]

    original_input = simulate_user_input(user_inputs)

    try:
        # Запускаем игру
        game.start_game()

    except EOFError:
        print("\n[ЗАВЕРШЕНО] Тест прерван - больше нет пользовательского ввода")
        print("Это нормально для автоматического тестирования")

    except Exception as e:
        print(f"\n[ОШИБКА] Неожиданная ошибка: {e}")

    finally:
        # Восстанавливаем оригинальный input
        __builtins__['input'] = original_input

def test_question_generation_only():
    """Тестирует только генерацию вопросов без полной игры"""

    print("\n=== ТЕСТ ТОЛЬКО ГЕНЕРАЦИИ ВОПРОСОВ ===")

    from ai.openai_client import OpenAIClient

    client = OpenAIClient()
    statement = "Время является иллюзией"

    print(f"Утверждение: '{statement}'")
    print("Игрок выбрал: AGREE (максимальная ставка)")
    print("\nВопросы от критиков:")

    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']

    context = {
        'statement': statement,
        'dialogue_history': [],
        'current_statement': statement,
        'depth': 1
    }

    for i, personality in enumerate(personalities, 1):
        try:
            question = client.generate_question(personality, statement, context)
            print(f"  {i}. {personality.title()}: {question}")
        except Exception as e:
            fallback = client._fallback_question(personality, statement)
            print(f"  {i}. {personality.title()}: {fallback} [FALLBACK]")

if __name__ == "__main__":
    # quick_game_test()  # Отключаем пока из-за проблем с input
    test_question_generation_only()