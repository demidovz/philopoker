#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка вопросов для логического утверждения
"""

from ai.openai_client import OpenAIClient

def debug_logical_statement():
    """Отладка для утверждения 'Из ложного можно вывести что угодно'"""

    client = OpenAIClient()
    statement = "Из ложного можно вывести что угодно"

    print("=== ОТЛАДКА ЛОГИЧЕСКОГО УТВЕРЖДЕНИЯ ===")
    print(f"Утверждение: '{statement}'")
    print("Игрок выбрал: AGREE")
    print("\nОжидаемые острые атаки:")
    print("- Скептик: 'Если из лжи выводится правда, то как отличить истину?'")
    print("- Педант: 'Это принцип взрыва в логике - где формальное доказательство?'")
    print("- Прагматик: 'Как практически использовать выводы из ложных посылок?'")
    print("- Синтезатор: 'Может ли из частично ложного следовать частично истинное?'")

    print("\n=== ФАКТИЧЕСКИЕ ВОПРОСЫ ОТ ИИ ===")

    personalities = ['skeptic', 'pedant', 'pragmatist', 'synthesizer']

    context = {
        'statement': statement,
        'dialogue_history': [],
        'current_statement': statement,
        'depth': 1
    }

    for personality in personalities:
        print(f"\n{personality.upper()}:")

        try:
            # Пробуем основной метод
            question = client.generate_question(personality, statement, context)
            print(f"  API: {question}")

            # Проверяем качество
            if any(word in question.lower() for word in ['объясните', 'расскажите', 'опишите', 'как вы']):
                print(f"  [!] ПЛОХО: Общий вопрос")
            else:
                print(f"  [+] ХОРОШО: Конкретный вопрос")

        except Exception as e:
            print(f"  API ERROR: {e}")

            # Пробуем fallback
            fallback = client._fallback_question(personality, statement)
            print(f"  FALLBACK: {fallback}")

            if any(word in fallback.lower() for word in ['объясните', 'расскажите', 'опишите', 'как вы']):
                print(f"  [!] ПЛОХО: Общий fallback")
            else:
                print(f"  [+] ХОРОШО: Конкретный fallback")

def test_api_connectivity():
    """Проверяет доступность OpenAI API"""

    print("\n=== ТЕСТ ПОДКЛЮЧЕНИЯ К API ===")

    client = OpenAIClient()

    if client.client is None:
        print("[!] ПРОБЛЕМА: OpenAI client не инициализирован")
        print("    Проверьте OPENAI_API_KEY в переменных окружения")
        return False

    try:
        # Простой тест API
        test_messages = [
            {"role": "user", "content": "Ответь одним словом: 'тест'"}
        ]

        response = client._make_request(test_messages)

        if response:
            print(f"[+] API РАБОТАЕТ: {response}")
            return True
        else:
            print("[!] API НЕ ОТВЕЧАЕТ")
            return False

    except Exception as e:
        print(f"[!] ОШИБКА API: {e}")
        return False

if __name__ == "__main__":
    api_works = test_api_connectivity()
    debug_logical_statement()

    if not api_works:
        print("\n=== ДИАГНОЗ ===")
        print("Проблема: OpenAI API недоступен")
        print("Решение: Настройте OPENAI_API_KEY или проверьте интернет-соединение")
        print("Сейчас используются fallback вопросы, которые общие и плохие")