#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование качества вопросов от ИИ
"""

from ai.openai_client import OpenAIClient
from ai.contradiction_checker import ContradictionChecker

def test_ai_question_generation():
    """Тестирует генерацию вопросов разными типами личности"""

    client = OpenAIClient()
    checker = ContradictionChecker()

    # Тестовые данные
    statement = "Красота объективна"
    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']

    # Контекст диалога для более реалистичного тестирования
    context = {
        'statement': statement,
        'dialogue_history': [
            {
                'depth': 1,
                'question': 'А как объяснить культурные различия в понимании красоты?',
                'response': 'Культурные различия касаются поверхностных проявлений, а основы красоты универсальны'
            }
        ]
    }

    print("=== ТЕСТ ГЕНЕРАЦИИ ВОПРОСОВ ===")
    print(f"Утверждение: '{statement}'")
    print(f"Предыдущий диалог:")
    for entry in context['dialogue_history']:
        print(f"  Q: {entry['question']}")
        print(f"  A: {entry['response']}")

    print("\n=== НОВЫЕ ВОПРОСЫ ОТ РАЗНЫХ ЛИЧНОСТЕЙ ===")

    for personality in personalities:
        print(f"\n{personality.upper()}:")
        try:
            question = client.generate_question(personality, statement, context)
            print(f"  Вопрос: {question}")

            # Проверим на противоречия (если есть ответ)
            if len(context['dialogue_history']) > 0:
                last_response = context['dialogue_history'][-1]['response']
                contradiction_analysis = checker.check_for_contradictions(
                    statement, last_response, context['dialogue_history'][:-1]
                )
                if contradiction_analysis['has_contradiction']:
                    print(f"  [ПРОТИВОРЕЧИЕ] {contradiction_analysis['explanation']}")
                    print(f"  [СЕРЬЕЗНОСТЬ] {contradiction_analysis['severity']}/10")

        except Exception as e:
            print(f"  [FALLBACK] Ошибка API: {e}")

    print("\n=== ТЕСТ ОЦЕНКИ УТВЕРЖДЕНИЯ ===")

    for personality in personalities:
        print(f"\n{personality.upper()}:")
        try:
            position, confidence, reasoning = client.evaluate_statement(personality, statement)
            print(f"  Позиция: {position}")
            print(f"  Уверенность: {confidence:.2f}")
            print(f"  Обоснование: {reasoning}")
        except Exception as e:
            print(f"  [FALLBACK] Ошибка API: {e}")

if __name__ == "__main__":
    test_ai_question_generation()