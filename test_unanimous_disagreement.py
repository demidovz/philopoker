#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование механики единогласного несогласия
"""

from ai.openai_client import OpenAIClient

def test_statement_improvement():
    """Тестирует улучшение утверждений разными типами личности"""

    client = OpenAIClient()

    # Тестовые спорные утверждения
    controversial_statements = [
        "Пытки допустимы для спасения невинных жизней",
        "Все религии ложны",
        "Демократия - худшая форма правления",
        "Животные не имеют прав",
        "Искусство должно служить государству"
    ]

    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']

    print("=== ТЕСТ УЛУЧШЕНИЯ СПОРНЫХ УТВЕРЖДЕНИЙ ===")

    for statement in controversial_statements:
        print(f"\n[СПОРНОЕ] УТВЕРЖДЕНИЕ: '{statement}'")
        print("Все игроки единогласно против! Философы предлагают исправления:")

        for personality in personalities:
            print(f"\n{personality.upper()}:")
            try:
                improved = client.improve_statement(personality, statement)
                print(f"  Исправленное: '{improved}'")

                # Также проверим оценку нового утверждения
                position, confidence, reasoning = client.evaluate_statement(personality, improved)
                print(f"  Новая позиция: {position} (уверенность: {confidence:.2f})")
                print(f"  Причина: {reasoning}")

            except Exception as e:
                print(f"  [FALLBACK] Ошибка API: {e}")

        print("-" * 60)

def test_fallback_improvement():
    """Тестирует fallback логику улучшения утверждений"""
    print("\n=== ТЕСТ FALLBACK УЛУЧШЕНИЯ ===")

    statements = [
        "Все люди равны",
        "Наука объясняет все",
        "Любовь вечна"
    ]

    client = OpenAIClient()

    for statement in statements:
        print(f"\nИсходное: '{statement}'")
        improved = client._fallback_improve_statement(statement)
        print(f"Fallback: '{improved}'")

if __name__ == "__main__":
    test_statement_improvement()
    test_fallback_improvement()