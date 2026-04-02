#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправленной генерации вопросов в игре
"""

from game.player import AIAgent
from ai.personalities import SkepticalPersonality, PedanticPersonality, PragmaticPersonality, SynthesizerPersonality

def test_fixed_questions():
    """Тестирует исправленную генерацию вопросов через AIAgent"""

    print("=== ТЕСТ ИСПРАВЛЕННЫХ ВОПРОСОВ ===")

    # Создаем ИИ агентов как в игре
    agents = [
        AIAgent("Скептик", SkepticalPersonality()),
        AIAgent("Педант", PedanticPersonality()),
        AIAgent("Прагматик", PragmaticPersonality()),
        AIAgent("Синтезатор", SynthesizerPersonality())
    ]

    statement = "Из ложного можно вывести что угодно"

    print(f"Утверждение: '{statement}'")
    print("Игрок выбрал: AGREE")

    context = {
        'statement': statement,
        'dialogue_history': [],
        'current_statement': statement,
        'depth': 1
    }

    print("\nВопросы от ИИ агентов (как в игре):")

    for i, agent in enumerate(agents, 1):
        try:
            question = agent.generate_question(statement, context)
            print(f"  {i}. {agent.name}: {question}")

            # Проверяем качество
            if any(word in question.lower() for word in ['объясните', 'расскажите', 'опишите', 'как вы объясните противоположную']):
                print(f"     [!] ПЛОХО: Общий вопрос")
            elif any(word in question.lower() for word in ['ложного', 'логики', 'посылки', 'вывести', 'противоречие']):
                print(f"     [+] ХОРОШО: Специфичный для логики")
            else:
                print(f"     [?] СРЕДНЕ: Не общий, но не специфичный")

        except Exception as e:
            print(f"  {i}. {agent.name}: [ОШИБКА] {e}")

def test_personality_methods():
    """Проверяет, что у personality классов есть метод generate_question"""

    print("\n=== ПРОВЕРКА МЕТОДОВ PERSONALITY ===")

    personalities = [
        ("Скептик", SkepticalPersonality()),
        ("Педант", PedanticPersonality()),
        ("Прагматик", PragmaticPersonality()),
        ("Синтезатор", SynthesizerPersonality())
    ]

    for name, personality in personalities:
        has_method = hasattr(personality, 'generate_question')
        print(f"{name}: generate_question = {has_method}")

        if has_method:
            try:
                # Тестируем метод
                test_question = personality.generate_question("Тест", {})
                print(f"  Тестовый вопрос: {test_question}")
            except Exception as e:
                print(f"  Ошибка: {e}")

if __name__ == "__main__":
    test_personality_methods()
    test_fixed_questions()