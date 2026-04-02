import os
import json
import time
from typing import Tuple, Dict, Any, Optional
from dotenv import load_dotenv
import openai

load_dotenv()

class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('AI_MODEL', 'nvidia/nemotron-3-super-120b-a12b:free')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '150'))
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        self.use_fallback = os.getenv('USE_FALLBACK', 'true').lower() == 'true'
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    'HTTP-Referer': os.getenv('OPENROUTER_HTTP_REFERER', 'https://localhost'),
                    'X-Title': os.getenv('OPENROUTER_X_TITLE', 'Philosophical Poker'),
                },
            )
        else:
            print("[WARNING] OPENROUTER_API_KEY не найден. Будет использоваться fallback логика.")
            self.client = None

    def _make_request(self, messages: list, max_retries: int = 3) -> Optional[str]:
        """Выполняет запрос к OpenAI API с повторными попытками"""
        if not self.client:
            return None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=15
                )
                return response.choices[0].message.content.strip()

            except openai.RateLimitError:
                wait_time = 2 ** attempt
                print(f"[WAIT] Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)

            except openai.APIError as e:
                print(f"[ERROR] OpenAI API error: {e}")
                break

            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                break

        return None

    def evaluate_statement(self, personality_type: str, statement: str) -> Tuple[str, float]:
        """ИИ оценивает философское утверждение согласно типу личности"""

        personality_prompts = {
            'skeptic': "Ты философ-скептик. Ты критически относишься к утверждениям, особенно категоричным. Ищешь противоречия и слабые места.",
            'pedant': "Ты философ-педант. Ты ценишь точность определений, логическую строгость и академическую корректность.",
            'pragmatist': "Ты философ-прагматик. Ты оцениваешь утверждения с точки зрения практической пользы и реальных последствий.",
            'synthesizer': "Ты философ-синтезатор. Ты стремишься найти компромиссы, общие точки и объединяющие элементы в разных позициях."
        }

        system_prompt = personality_prompts.get(personality_type, personality_prompts['skeptic'])

        messages = [
            {"role": "system", "content": f"{system_prompt} Отвечай кратко и структурированно."},
            {"role": "user", "content": f"""Оцени философское утверждение: "{statement}"

Ответь в формате JSON:
{{
  "position": "agree" или "disagree",
  "confidence": число от 0.1 до 1.0,
  "reasoning": "краткое обоснование в 1-2 предложения"
}}"""}
        ]

        response = self._make_request(messages)
        if response:
            try:
                result = json.loads(response)
                position = result.get('position', 'agree')
                confidence = float(result.get('confidence', 0.5))
                reasoning = result.get('reasoning', 'Без комментариев')

                return position, confidence, reasoning
            except (json.JSONDecodeError, ValueError, KeyError):
                print(f"[ERROR] Не удалось распарсить ответ ИИ: {response}")

        # Fallback
        return self._fallback_evaluate(personality_type, statement)

    def generate_question(self, personality_type: str, statement: str, context: Dict) -> str:
        """ИИ генерирует критический вопрос на основе глубокого анализа"""

        # Строим богатый контекст для ИИ
        dialogue_history = context.get('dialogue_history', [])
        original_statement = context.get('statement', statement)
        current_depth = len(dialogue_history) + 1

        # Анализируем предыдущие вопросы чтобы не повторяться
        previous_questions = []
        for entry in dialogue_history:
            if entry.get('question'):
                previous_questions.append(entry['question'])

        personality_descriptions = {
            'skeptic': """Ты БЕСПОЩАДНЫЙ философ-скептик. Твоя задача - НАЙТИ ПРОТИВОРЕЧИЕ и разгромить утверждение.

            СТРАТЕГИИ АТАКИ:
            - Ищи эмпирические противоречия ("Если X верно, почему мы наблюдаем Y?")
            - Найди логические дыры ("Если это так, то почему не происходит Z?")
            - Требуй доказательств ("Где научные данные, подтверждающие это?")
            - Указывай на исключения ("А как насчет случаев, когда это не работает?")

            ТВОЯ ЦЕЛЬ: Заставить защитника противоречить самому себе или признать слабость позиции.""",

            'pedant': """Ты ДОТОШНЫЙ философ-академик. Твоя задача - найти ТЕРМИНОЛОГИЧЕСКИЕ и МЕТОДОЛОГИЧЕСКИЕ противоречия.

            СТРАТЕГИИ АТАКИ:
            - Требуй точных определений ("Что ИМЕННО вы понимаете под 'иллюзией'?")
            - Ищи логические ошибки ("Это ошибка категории/причины-следствия")
            - Указывай на отсутствие ссылок ("Кто из философов это доказал?")
            - Находи противоречия в самой формулировке

            ТВОЯ ЦЕЛЬ: Показать, что утверждение академически некорректно.""",

            'pragmatist': """Ты ПРАКТИЧНЫЙ философ-прагматик. Твоя задача - найти ПРАКТИЧЕСКИЕ противоречия и нелепости.

            СТРАТЕГИИ АТАКИ:
            - Требуй практических примеров ("Как это работает в реальной жизни?")
            - Ищи абсурдные последствия ("Если время иллюзия, почему стареем?")
            - Указывай на бесполезность ("Какая практическая польза от этого знания?")
            - Находи противоречия с повседневным опытом

            ТВОЯ ЦЕЛЬ: Показать практическую несостоятельность утверждения.""",

            'synthesizer': """Ты ПРОНИЦАТЕЛЬНЫЙ философ-синтезатор. Твоя задача - найти СКРЫТЫЕ противоречия через альтернативные интерпретации.

            СТРАТЕГИИ АТАКИ:
            - Предлагай альтернативы ("А что если это наоборот?")
            - Ищи исключения ("В каких случаях это НЕ работает?")
            - Указывай на односторонность ("Почему игнорируете другую сторону?")
            - Находи противоречия между крайними позициями

            ТВОЯ ЦЕЛЬ: Показать неполноту или односторонность утверждения."""
        }

        personality_desc = personality_descriptions.get(personality_type, personality_descriptions['skeptic'])

        # Формируем контекст предыдущих вопросов
        context_text = ""
        if previous_questions:
            context_text = f"\n\nУже заданные вопросы (НЕ повторяй их):\n" + "\n".join([f"- {q}" for q in previous_questions])

        messages = [
            {"role": "system", "content": personality_desc},
            {"role": "user", "content": f"""УТВЕРЖДЕНИЕ ДЛЯ АТАКИ: "{statement}"

ТВОЯ МИССИЯ: Найти ЛОГИЧЕСКОЕ ПРОТИВОРЕЧИЕ или СЛАБОЕ МЕСТО и разгромить это утверждение одним убийственным вопросом.

АНАЛИЗИРУЙ:
1. Какие скрытые предположения делает это утверждение?
2. С чем это утверждение противоречит в реальном мире?
3. Какие абсурдные следствия из него вытекают?
4. Где здесь логическая дыра или ошибка в рассуждении?

Контекст:
- Уровень атаки: {current_depth}
- Изначальная мишень: "{original_statement}"
{context_text}

ПРИМЕРЫ УБИЙСТВЕННЫХ ВОПРОСОВ:
- Скептик про "время - иллюзия": "Если время иллюзия, почему причина всегда предшествует следствию?"
- Педант про "красота объективна": "Как измерить объективную красоту без субъективного наблюдателя?"
- Прагматик про "знание без опыта": "Как слепорожденный узнает что такое 'красный' без опыта?"
- Синтезатор про "все относительно": "Если все относительно, то и ваше утверждение относительно?"

ЗАПРЕЩЕНО:
- Общие вопросы ("можете привести пример?")
- Просьбы объяснить ("как вы это понимаете?")
- Мягкие уточнения

ЗАДАЙ ОДИН БЕСПОЩАДНЫЙ ВОПРОС (максимум 15 слов):"""}
        ]

        response = self._make_request(messages)
        if response:
            # Очищаем ответ от лишнего
            clean_response = response.strip().strip('"').strip("'")
            if not clean_response.endswith('?'):
                clean_response += '?'
            return clean_response

        # Fallback
        return self._fallback_question(personality_type, statement)

    def generate_argument(self, personality_type: str, statement: str, position: str) -> str:
        """ИИ генерирует убеждающий аргумент"""

        messages = [
            {"role": "system", "content": f"Ты философ, который должен убедить оппонентов в своей правоте."},
            {"role": "user", "content": f"""Утверждение: "{statement}"
Твоя позиция: {position}

Приведи ОДИН сильный аргумент в защиту своей позиции (максимум 25 слов). Будь убедительным и конкретным."""}
        ]

        response = self._make_request(messages)
        if response:
            return response

        # Fallback
        return self._fallback_argument(personality_type, position)

    def generate_response(self, personality_type: str, question: str, statement: str) -> str:
        """ИИ отвечает на критический вопрос"""

        messages = [
            {"role": "system", "content": f"Ты философ, отвечающий на критический вопрос. Будь убедительным но кратким."},
            {"role": "user", "content": f"""Исходное утверждение: "{statement}"
Вопрос к тебе: "{question}"

Дай краткий убедительный ответ (максимум 15 слов)."""}
        ]

        response = self._make_request(messages)
        if response:
            return response

        # Fallback
        return self._fallback_response(question)

    def make_final_vote(self, personality_type: str, dialogue_context: Dict) -> bool:
        """ИИ голосует по итогам дискуссии с учетом контекста и противоречий"""

        # Извлекаем информацию из контекста
        original_statement = dialogue_context.get('original_statement', '')
        dialogue_history = dialogue_context.get('dialogue_history', [])
        contradictions = dialogue_context.get('contradictions', [])

        # Строим развернутый контекст
        context_parts = [
            f"ИЗНАЧАЛЬНОЕ УТВЕРЖДЕНИЕ: {original_statement}",
            "",
            "ПОЛНАЯ ИСТОРИЯ ДИАЛОГА:"
        ]

        for entry in dialogue_history:
            level = entry.get('depth', 1)
            question = entry.get('question', '')
            response = entry.get('response', '')
            context_parts.extend([
                f"Уровень {level}:",
                f"  Вопрос: {question}",
                f"  Ответ защитника: {response}",
                ""
            ])

        if contradictions:
            context_parts.extend([
                "ОБНАРУЖЕННЫЕ ПРОТИВОРЕЧИЯ:",
                *[f"- {c['explanation']} (серьезность: {c['severity']}/10)" for c in contradictions],
                ""
            ])

        personality_instructions = {
            'skeptic': "Как скептик, ты особенно чувствителен к логическим противоречиям и слабым аргументам.",
            'pedant': "Как педант, ты требуешь логической последовательности и точности в формулировках.",
            'pragmatist': "Как прагматик, ты оцениваешь, насколько аргументы работают в реальности.",
            'synthesizer': "Как синтезатор, ты стремишься к справедливой оценке всех позиций."
        }

        personality_instruction = personality_instructions.get(personality_type, "Ты беспристрастный судья.")

        context_text = "\n".join(context_parts)

        messages = [
            {"role": "system", "content": f"{personality_instruction} Твоя задача - честно оценить качество защиты позиции."},
            {"role": "user", "content": f"""{context_text}

ВОПРОС ДЛЯ ГОЛОСОВАНИЯ: Убедил ли защитник в итоге своими ответами?

КРИТЕРИИ ОЦЕНКИ:
1. Логическая последовательность (нет противоречий)
2. Качество ответов на вопросы
3. Соответствие изначальному утверждению
4. Честность и признание ограничений

ВАЖНО: Если есть серьезные противоречия (7+ баллов), это должно сильно повлиять на оценку.

Ответь только 'yes' (убедил) или 'no' (не убедил)."""}
        ]

        response = self._make_request(messages)
        if response:
            return response.lower().strip() in ['yes', 'да', 'убедил']

        # Fallback с учетом противоречий
        if contradictions:
            serious_contradictions = [c for c in contradictions if c.get('severity', 0) >= 7]
            if serious_contradictions:
                return False  # Серьезные противоречия = автоматическое поражение

        import random
        return random.choice([True, False])

    # Fallback методы (если API недоступен)
    def _fallback_evaluate(self, personality_type: str, statement: str) -> Tuple[str, float, str]:
        import random

        fallbacks = {
            'skeptic': ('disagree', 0.7, 'Скептически отношусь к категоричным утверждениям'),
            'pedant': ('agree', 0.6, 'Требуется больше точности в формулировке'),
            'pragmatist': ('agree', 0.5, 'Есть практическая ценность'),
            'synthesizer': ('agree', 0.4, 'Можно найти компромиссное решение')
        }

        position, conf, reason = fallbacks.get(personality_type, fallbacks['skeptic'])
        confidence = conf + random.uniform(-0.2, 0.2)
        return position, max(0.1, min(1.0, confidence)), reason

    def _fallback_question(self, personality_type: str, statement: str) -> str:
        # Агрессивные fallback вопросы, ищущие противоречия
        contradiction_questions = {
            'skeptic': [
                f"Где доказательства, что '{statement.lower()}' не просто предрассудок?",
                f"Почему мы должны верить в '{statement.lower()}' без научных данных?",
                f"А если '{statement.lower()}' ложно, что тогда?"
            ],
            'pedant': [
                f"Как точно определить '{statement.split()[0].lower()}' в этом контексте?",
                f"Кто из философов доказал, что '{statement.lower()}'?",
                f"Где академические источники подтверждающие '{statement.lower()}'?"
            ],
            'pragmatist': [
                f"Какая практическая польза от веры что '{statement.lower()}'?",
                f"Как '{statement.lower()}' помогает в реальной жизни?",
                f"Что изменится в мире если '{statement.lower()}' ложно?"
            ],
            'synthesizer': [
                f"А что если '{statement.lower()}' верно только частично?",
                f"Может ли '{statement.lower()}' и противоположное быть одновременно верными?",
                f"Где граница применимости утверждения '{statement.lower()}'?"
            ]
        }
        import random
        return random.choice(contradiction_questions.get(personality_type, contradiction_questions['skeptic']))

    def _fallback_argument(self, personality_type: str, position: str) -> str:
        arguments = {
            'agree': ["История подтверждает эту точку зрения", "Логика указывает именно на это"],
            'disagree': ["Есть серьезные противоречия", "Практика показывает обратное"]
        }
        import random
        return random.choice(arguments.get(position, arguments['agree']))

    def _fallback_response(self, question: str) -> str:
        responses = [
            "Это сложный вопрос, требующий глубокого анализа",
            "Мой опыт подсказывает иное решение",
            "Стоит рассмотреть альтернативные подходы"
        ]
        import random
        return random.choice(responses)

    def improve_statement(self, personality_type: str, original_statement: str) -> str:
        """ИИ улучшает утверждение после единогласного несогласия"""

        personality_approaches = {
            'skeptic': "Как скептик, ты делаешь утверждение менее категоричным и добавляешь оговорки.",
            'pedant': "Как педант, ты уточняешь определения и делаешь утверждение более академически корректным.",
            'pragmatist': "Как прагматик, ты фокусируешься на практической применимости утверждения.",
            'synthesizer': "Как синтезатор, ты пытаешься найти компромиссную формулировку, учитывающую разные позиции."
        }

        approach = personality_approaches.get(personality_type, "Ты улучшаешь утверждение, делая его более сбалансированным.")

        messages = [
            {"role": "system", "content": f"{approach} Твоя задача - исправить утверждение так, чтобы оно стало более приемлемым."},
            {"role": "user", "content": f"""Все игроки единогласно отвергли утверждение: "{original_statement}"

Предложи ИСПРАВЛЕННУЮ версию этого утверждения, которая:
1. Сохраняет основную идею
2. Становится менее спорной
3. Учитывает возможные возражения
4. Максимум 15 слов

Ответь только исправленным утверждением, без дополнительных комментариев."""}
        ]

        response = self._make_request(messages)
        if response:
            # Очищаем ответ от лишнего
            clean_response = response.strip().strip('"').strip("'")
            return clean_response

        # Fallback
        return self._fallback_improve_statement(original_statement)

    def _fallback_improve_statement(self, original_statement: str) -> str:
        """Простое улучшение утверждения без ИИ"""
        soften_phrases = [
            f"В большинстве случаев {original_statement.lower()}",
            f"При определенных условиях {original_statement.lower()}",
            f"Можно утверждать, что {original_statement.lower()}",
            f"Часто {original_statement.lower()}",
            f"В некоторых ситуациях {original_statement.lower()}"
        ]
        import random
        return random.choice(soften_phrases)
