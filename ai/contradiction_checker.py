import json
from typing import List, Dict, Tuple, Optional
from .openai_client import OpenAIClient

class ContradictionChecker:
    """Система автоматической проверки логических противоречий"""

    def __init__(self):
        self.openai_client = OpenAIClient()

    def check_for_contradictions(self, original_statement: str, response: str, dialogue_history: List[Dict]) -> Dict:
        """
        Проверяет ответ на противоречия с изначальным утверждением и историей диалога

        Returns:
        {
            'has_contradiction': bool,
            'contradiction_type': str,
            'explanation': str,
            'severity': int (1-10)
        }
        """

        # Составляем контекст для ИИ
        context = self._build_context(original_statement, response, dialogue_history)

        # Запрашиваем анализ у GPT
        analysis = self._analyze_with_ai(context)

        if analysis:
            return analysis

        # Fallback - простая проверка ключевых слов
        return self._fallback_contradiction_check(original_statement, response)

    def _build_context(self, original_statement: str, response: str, dialogue_history: List[Dict]) -> str:
        """Строит контекст для анализа противоречий"""

        context_parts = [
            f"ИЗНАЧАЛЬНОЕ УТВЕРЖДЕНИЕ: {original_statement}",
            "",
            "ИСТОРИЯ ДИАЛОГА:"
        ]

        for i, entry in enumerate(dialogue_history):
            level = entry.get('depth', 1)
            question = entry.get('question', '')
            prev_response = entry.get('response', '')
            context_parts.append(f"  Уровень {level}:")
            context_parts.append(f"    Вопрос: {question}")
            context_parts.append(f"    Ответ: {prev_response}")
            context_parts.append("")

        context_parts.extend([
            f"НОВЫЙ ОТВЕТ: {response}",
            "",
            "ЗАДАЧА: Проверить на логические противоречия"
        ])

        return "\n".join(context_parts)

    def _analyze_with_ai(self, context: str) -> Optional[Dict]:
        """Анализирует противоречия с помощью GPT"""

        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по логике и философии. Твоя задача - найти логические противоречия в рассуждениях."
            },
            {
                "role": "user",
                "content": f"""{context}

Проанализируй, есть ли логические противоречия между изначальным утверждением и новым ответом.
Также проверь противоречия с предыдущими ответами в истории диалога.

Ответь в формате JSON:
{{
  "has_contradiction": true/false,
  "contradiction_type": "self_contradiction" | "statement_contradiction" | "logical_fallacy" | "none",
  "explanation": "краткое объяснение противоречия или 'противоречий не найдено'",
  "severity": число от 1 до 10 (где 10 = критическое противоречие)
}}

Типы противоречий:
- self_contradiction: противоречие с собственными предыдущими утверждениями
- statement_contradiction: противоречие с изначальным утверждением
- logical_fallacy: логическая ошибка в рассуждении"""
            }
        ]

        # Для анализа противоречий нужно больше токенов
        response = self._make_request_for_analysis(messages)
        if response:
            try:
                # Очищаем ответ от возможного мусора
                clean_response = response.strip()

                # Пытаемся починить обрезанный JSON
                if not clean_response.endswith('}'):
                    # Если JSON обрезан, пытаемся его завершить
                    clean_response = self._fix_truncated_json(clean_response)

                return json.loads(clean_response)

            except json.JSONDecodeError as e:
                print(f"[ERROR] Ошибка парсинга анализа противоречий: {response[:200]}...")
                print(f"[ERROR] Детали ошибки: {e}")

                # Пытаемся извлечь информацию из частичного JSON
                return self._parse_partial_json(response)

        return None

    def _fallback_contradiction_check(self, original_statement: str, response: str) -> Dict:
        """Простая проверка противоречий без ИИ"""

        # Простые признаки противоречий
        contradiction_indicators = [
            ("не все", "все"),
            ("никогда", "всегда"),
            ("невозможно", "возможно"),
            ("не может", "может"),
            ("отрицаю", "подтверждаю")
        ]

        original_lower = original_statement.lower()
        response_lower = response.lower()

        for negative, positive in contradiction_indicators:
            if negative in response_lower and positive in original_lower:
                return {
                    'has_contradiction': True,
                    'contradiction_type': 'statement_contradiction',
                    'explanation': f'Ответ содержит "{negative}", что противоречит изначальному утверждению',
                    'severity': 7
                }

        return {
            'has_contradiction': False,
            'contradiction_type': 'none',
            'explanation': 'Автоматическая проверка не выявила явных противоречий',
            'severity': 0
        }

    def format_contradiction_report(self, analysis: Dict) -> str:
        """Форматирует отчет о противоречиях для игроков"""

        if not analysis['has_contradiction']:
            return "[OK] Логических противоречий не обнаружено"

        severity = analysis['severity']
        if severity >= 8:
            icon = "[!]!"
            level = "КРИТИЧЕСКОЕ"
        elif severity >= 6:
            icon = "[!]"
            level = "СЕРЬЕЗНОЕ"
        else:
            icon = "[~]"
            level = "СЛАБОЕ"

        contradiction_types = {
            'self_contradiction': 'Противоречие с собственными утверждениями',
            'statement_contradiction': 'Противоречие с изначальным утверждением',
            'logical_fallacy': 'Логическая ошибка в рассуждении'
        }

        type_description = contradiction_types.get(
            analysis['contradiction_type'],
            'Неопределенное противоречие'
        )

        return f"{icon} {level} ПРОТИВОРЕЧИЕ ({severity}/10)\n" \
               f"Тип: {type_description}\n" \
               f"Объяснение: {analysis['explanation']}"

    def _fix_truncated_json(self, truncated_json: str) -> str:
        """Пытается починить обрезанный JSON"""
        try:
            # Ищем последнее поле и пытаемся его закрыть
            if '"explanation"' in truncated_json:
                # Если обрезалось поле explanation, закрываем его
                if not truncated_json.rstrip().endswith('"'):
                    truncated_json += '"'
                if not truncated_json.rstrip().endswith('}'):
                    truncated_json += '}'

            # Базовая попытка завершить JSON
            elif not truncated_json.rstrip().endswith('}'):
                truncated_json += '}'

            return truncated_json

        except Exception:
            # Если не получается починить, возвращаем как есть
            return truncated_json

    def _parse_partial_json(self, partial_response: str) -> Dict:
        """Извлекает информацию из частичного JSON"""
        try:
            # Пытаемся найти ключевые поля в тексте
            has_contradiction = True  # По умолчанию считаем что есть противоречие

            if '"has_contradiction": false' in partial_response:
                has_contradiction = False
            elif '"has_contradiction": true' in partial_response:
                has_contradiction = True

            # Ищем тип противоречия
            contradiction_type = "unknown"
            if '"contradiction_type": "self_contradiction"' in partial_response:
                contradiction_type = "self_contradiction"
            elif '"contradiction_type": "statement_contradiction"' in partial_response:
                contradiction_type = "statement_contradiction"
            elif '"contradiction_type": "logical_fallacy"' in partial_response:
                contradiction_type = "logical_fallacy"

            # Ищем severity
            severity = 5  # По умолчанию средняя серьезность
            import re
            severity_match = re.search(r'"severity":\s*(\d+)', partial_response)
            if severity_match:
                severity = int(severity_match.group(1))

            # Ищем объяснение
            explanation = "Автоматический анализ обнаружил противоречие (частичный ответ)"
            explanation_match = re.search(r'"explanation":\s*"([^"]*)', partial_response)
            if explanation_match:
                explanation = explanation_match.group(1) + "... [обрезано]"

            return {
                'has_contradiction': has_contradiction,
                'contradiction_type': contradiction_type,
                'explanation': explanation,
                'severity': severity
            }

        except Exception as e:
            print(f"[ERROR] Ошибка парсинга частичного JSON: {e}")
            # Возвращаем базовый результат
            return {
                'has_contradiction': True,
                'contradiction_type': 'unknown',
                'explanation': 'Не удалось обработать ответ системы анализа',
                'severity': 5
            }

    def _make_request_for_analysis(self, messages: list) -> Optional[str]:
        """Специальный запрос для анализа противоречий с увеличенным лимитом токенов"""
        if not self.openai_client.client:
            return None

        try:
            response = self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=messages,
                max_tokens=300,  # Увеличенный лимит для JSON ответа
                temperature=0.3,  # Более низкая температура для структурированного ответа
                timeout=15
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[ERROR] Ошибка запроса анализа противоречий: {e}")
            return None