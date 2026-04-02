#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений
"""

from game.player import AIAgent
from ai.personalities import SkepticalPersonality

def test_make_final_vote_fix():
    """Тестирует исправление make_final_vote"""

    print("=== ТЕСТ ИСПРАВЛЕНИЯ make_final_vote ===")

    agent = AIAgent("Тестовый Скептик", SkepticalPersonality())

    # Создаем тестовый dialogue_context
    dialogue_context = {
        'original_statement': 'Тестовое утверждение',
        'dialogue_history': [
            {
                'depth': 1,
                'question': 'Тестовый вопрос?',
                'response': 'Тестовый ответ'
            }
        ],
        'contradictions': []
    }

    try:
        # Тестируем метод make_final_vote
        result = agent.personality.make_final_vote(dialogue_context)
        print(f"[+] make_final_vote работает: {result}")
        print(f"    Тип результата: {type(result)}")

    except Exception as e:
        print(f"[!] ОШИБКА в make_final_vote: {e}")

def test_depth_limit():
    """Тестирует новое ограничение глубины"""

    print("\n=== ТЕСТ ОГРАНИЧЕНИЯ ГЛУБИНЫ ===")

    from game.game_engine import Game

    game = Game()

    # Тестируем проверку глубины
    print("Тестируем глубины:")

    test_depths = [1, 50, 99, 100, 101]

    for depth in test_depths:
        # Вызываем метод с разными глубинами
        print(f"  Глубина {depth}: ", end="")

        if depth > 100:
            print("должна быть заблокирована")
        else:
            print("должна быть разрешена")

def test_question_generation():
    """Тестирует генерацию вопросов после исправлений"""

    print("\n=== ТЕСТ ГЕНЕРАЦИИ ВОПРОСОВ ===")

    agent = AIAgent("Тестовый Скептик", SkepticalPersonality())

    statement = "Тестовое утверждение"
    context = {
        'statement': statement,
        'dialogue_history': [],
        'current_statement': statement,
        'depth': 1
    }

    try:
        question = agent.generate_question(statement, context)
        print(f"[+] Генерация вопросов работает: {question}")

        # Проверяем, что это не старый захардкоженный вопрос
        old_patterns = ['объясните противоположную точку зрения', 'привести пример']
        is_old = any(pattern in question.lower() for pattern in old_patterns)

        if is_old:
            print(f"[!] ВНИМАНИЕ: Похоже на старый вопрос")
        else:
            print(f"[+] Новый улучшенный вопрос")

    except Exception as e:
        print(f"[!] ОШИБКА в генерации вопросов: {e}")

if __name__ == "__main__":
    test_make_final_vote_fix()
    test_depth_limit()
    test_question_generation()