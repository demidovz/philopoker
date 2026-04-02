#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправленной системы детекции противоречий
"""

from ai.contradiction_checker import ContradictionChecker

def test_contradiction_detection():
    """Тестирует исправленную детекцию противоречий"""

    print("=== ТЕСТ ДЕТЕКЦИИ ПРОТИВОРЕЧИЙ ===")

    checker = ContradictionChecker()

    # Тестовые случаи с противоречиями
    test_cases = [
        {
            "name": "Явное противоречие",
            "original": "Знание возможно без опыта",
            "response": "Знание невозможно без опыта - опыт основа всего",
            "history": []
        },
        {
            "name": "Логическое противоречие",
            "original": "Время является иллюзией",
            "response": "Да, но мы стареем во времени, что доказывает его реальность",
            "history": []
        },
        {
            "name": "Отсутствие противоречия",
            "original": "Красота объективна",
            "response": "Красота имеет объективные основы в математических пропорциях",
            "history": []
        }
    ]

    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        print(f"Исходное: '{case['original']}'")
        print(f"Ответ: '{case['response']}'")

        try:
            analysis = checker.check_for_contradictions(
                case['original'],
                case['response'],
                case['history']
            )

            print(f"Результат:")
            print(f"  Есть противоречие: {analysis['has_contradiction']}")
            print(f"  Тип: {analysis['contradiction_type']}")
            print(f"  Серьезность: {analysis['severity']}/10")
            print(f"  Объяснение: {analysis['explanation']}")

            # Тестируем форматирование
            formatted = checker.format_contradiction_report(analysis)
            print(f"Отформатированный отчет:")
            print(f"  {formatted}")

        except Exception as e:
            print(f"[ERROR] Ошибка анализа: {e}")

def test_partial_json_parsing():
    """Тестирует парсинг частичного JSON"""

    print("\n=== ТЕСТ ПАРСИНГА ЧАСТИЧНОГО JSON ===")

    checker = ContradictionChecker()

    # Примеры обрезанного JSON из лога
    truncated_examples = [
        '''{
  "has_contradiction": true,
  "contradiction_type": "self_contradiction",
  "explanation": "Новый ответ утверждает, что определение формируется в результате сократовского диалога и снижения противоречий. Однако, на уровне 8 было сказано, что если утверждение выдерживает проверки методом Сократа, то оно истинное. Это создает противоречие, так как метод Сократа не может однозначно определ''',

        '''{
  "has_contradiction": false,
  "contradiction_type": "none",
  "explanation": "Ответ логически последов''',

        '''{
  "has_contradiction": true,
  "severity": 9'''
    ]

    for i, truncated in enumerate(truncated_examples, 1):
        print(f"\nПример {i}:")
        print(f"Обрезанный JSON: {truncated[:100]}...")

        try:
            result = checker._parse_partial_json(truncated)
            print(f"Результат парсинга:")
            print(f"  Противоречие: {result['has_contradiction']}")
            print(f"  Тип: {result['contradiction_type']}")
            print(f"  Серьезность: {result['severity']}")
            print(f"  Объяснение: {result['explanation'][:100]}...")

        except Exception as e:
            print(f"[ERROR] Ошибка парсинга: {e}")

if __name__ == "__main__":
    test_contradiction_detection()
    test_partial_json_parsing()