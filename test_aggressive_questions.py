#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование агрессивной генерации вопросов
"""

from ai.openai_client import OpenAIClient

def test_killer_questions():
    """Тестирует генерацию убийственных вопросов против философских утверждений"""

    client = OpenAIClient()

    # Тестовые утверждения из вашего лога
    test_statements = [
        "Время является иллюзией",
        "Красота объективна",
        "Свободная воля существует",
        "Все религии ложны",
        "Животные имеют права"
    ]

    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']

    print("=== ТЕСТ АГРЕССИВНОЙ ГЕНЕРАЦИИ ВОПРОСОВ ===")

    for statement in test_statements:
        print(f"\n[ЦЕЛЬ] Утверждение: '{statement}'")
        print("Вопросы-убийцы от критиков:")

        for personality in personalities:
            print(f"\n{personality.upper()}:")

            context = {
                'statement': statement,
                'dialogue_history': [],
                'current_statement': statement,
                'depth': 1
            }

            try:
                # Тестируем основной метод
                question = client.generate_question(personality, statement, context)
                print(f"  API: {question}")

                # Тестируем fallback
                fallback_question = client._fallback_question(personality, statement)
                print(f"  Fallback: {fallback_question}")

            except Exception as e:
                print(f"  [ERROR] {e}")
                fallback_question = client._fallback_question(personality, statement)
                print(f"  Fallback: {fallback_question}")

        print("-" * 60)

def test_specific_statement():
    """Специальный тест для утверждения 'Время является иллюзией'"""

    client = OpenAIClient()
    statement = "Время является иллюзией"

    print(f"\n=== СПЕЦИАЛЬНЫЙ ТЕСТ ДЛЯ '{statement}' ===")

    expected_contradictions = [
        "причинность требует времени",
        "старение - реальный процесс",
        "физические часы измеряют что-то реальное",
        "память подразумевает прошлое",
        "планирование требует будущего"
    ]

    print("Ожидаемые противоречия для проверки:")
    for contradiction in expected_contradictions:
        print(f"  - {contradiction}")

    print("\nВопросы от ИИ:")

    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']
    context = {
        'statement': statement,
        'dialogue_history': [],
        'current_statement': statement,
        'depth': 1
    }

    for personality in personalities:
        try:
            question = client.generate_question(personality, statement, context)
            print(f"  {personality}: {question}")

            # Проверяем, затрагивает ли вопрос хотя бы одно ожидаемое противоречие
            hits = [c for c in expected_contradictions if any(word in question.lower() for word in c.split())]
            if hits:
                print(f"    [+] Затрагивает: {hits}")
            else:
                print(f"    [-] Не затрагивает основные противоречия")

        except Exception as e:
            print(f"  {personality}: [ERROR] {e}")

if __name__ == "__main__":
    test_killer_questions()
    test_specific_statement()