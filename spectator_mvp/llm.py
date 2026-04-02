from __future__ import annotations

import json
import ipaddress
import os
import random
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from openai import OpenAI

from .config import PRICE_HINTS
from .models import AgentProfile


OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost")
OPENROUTER_TITLE = os.getenv("OPENROUTER_X_TITLE", "Philosophical Poker")


@dataclass
class UsageSnapshot:
    calls: int = 0
    prompt_chars: int = 0
    completion_chars: int = 0

    def register(self, prompt: str, completion: str) -> None:
        self.calls += 1
        self.prompt_chars += len(prompt)
        self.completion_chars += len(completion)

    def estimated_cost_usd(self, model: str) -> float | None:
        prices = PRICE_HINTS.get(model)
        if not prices:
            return None
        input_tokens = self.prompt_chars / 4.0
        output_tokens = self.completion_chars / 4.0
        return (
            input_tokens / 1_000_000 * prices["input_per_1m"]
            + output_tokens / 1_000_000 * prices["output_per_1m"]
        )


class BaseBackend:
    def __init__(self) -> None:
        self.usage = UsageSnapshot()
        self.backend_name = "base"

    def json_completion(
        self,
        agent: AgentProfile,
        instruction: str,
        payload: dict[str, Any],
        max_tokens: int = 160,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "backend": self.backend_name}

    def child_summary(self, initial_claim: str, final_claim: str) -> str:
        return _fallback_child_summary(final_claim)

    def balance_info(self) -> dict[str, Any]:
        return {"available_usd": None, "source": "unavailable"}


class OpenRouterBackend(BaseBackend):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        *,
        allow_fallback_to_mock: bool = False,
    ) -> None:
        super().__init__()
        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": OPENROUTER_TITLE,
            },
        )
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.backend_name = "openrouter"
        self._balance_cache: dict[str, Any] | None = None
        self.allow_fallback_to_mock = allow_fallback_to_mock
        self._fallback_backend: BaseBackend | None = None
        self._fallback_reason: str | None = None

    def _task_limits(self, task: str, max_tokens: int) -> tuple[int, int, int]:
        if _is_nano_model(self.model):
            completion_attempts = 2
            transport_attempts = 2
            limited_tokens = min(max_tokens, 120 if task == "vote" else 100)
            return completion_attempts, transport_attempts, limited_tokens
        return 3, 3, max_tokens

    def _request_json_text(self, system: str, prompt: str, max_tokens: int) -> str:
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": self.temperature,
        }
        last_error: Exception | None = None
        for use_json_format in (True, False):
            try:
                response = self.client.chat.completions.create(
                    **request,
                    **({"response_format": {"type": "json_object"}} if use_json_format else {}),
                )
                return _chat_completion_text(response)
            except Exception as exc:
                last_error = exc
                if use_json_format and _should_retry_without_json_mode(str(exc)):
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("OpenRouter completion failed without an explicit error")

    def json_completion(
        self,
        agent: AgentProfile,
        instruction: str,
        payload: dict[str, Any],
        max_tokens: int = 160,
    ) -> dict[str, Any]:
        if self._fallback_backend is not None:
            return self._fallback_backend.json_completion(
                agent, instruction, payload, max_tokens=max_tokens
            )

        prompt = json.dumps(payload, ensure_ascii=False)
        task = str(payload.get("task", ""))
        schema = _schema_for_task(task)
        required_fields = schema["schema"]["required"]
        allow_empty_fields = set(schema.get("allow_empty_fields", []))
        role_hint = _role_hint(agent.name, task)

        system = (
            "Ты игрок философской настольной игры.\n"
            f"Имя: {agent.name}\n"
            f"Роль: {agent.role}\n"
            f"Миссия: {agent.mission}\n"
            f"Стиль: {agent.style}\n"
            f"Тактика роли: {role_hint}\n"
            "Ты участвуешь в сократической проверке тезиса.\n"
            "Не болтай общими словами и не повторяй соседние ходы.\n"
            "Говори по-русски.\n"
            f"{instruction}\n"
            "Все обязательные поля должны быть осмысленно заполнены.\n"
            "Верни только JSON по схеме."
        )

        completion_attempts, transport_attempts, current_max_tokens = self._task_limits(task, max_tokens)
        parsed: dict[str, Any] = {}

        for _ in range(completion_attempts):
            for transport_attempt in range(transport_attempts):
                try:
                    text = self._request_json_text(system, prompt, current_max_tokens)
                    break
                except Exception as exc:
                    if self.allow_fallback_to_mock and _should_fallback_to_mock(str(exc)):
                        self._enable_mock_fallback(str(exc))
                        return self._fallback_backend.json_completion(
                            agent, instruction, payload, max_tokens=max_tokens
                        )
                    if transport_attempt == transport_attempts - 1:
                        raise
                    time.sleep(1.0 * (transport_attempt + 1))

            self.usage.register(prompt, text)
            try:
                parsed = _parse_json(text)
            except json.JSONDecodeError:
                prompt = json.dumps(
                    {
                        "retry": True,
                        "reason": "Previous output was invalid JSON. Return one complete JSON object.",
                        "original_payload": payload,
                    },
                    ensure_ascii=False,
                )
                current_max_tokens = max(current_max_tokens, 140 if _is_nano_model(self.model) else 220)
                continue

            if _has_required_content(parsed, required_fields, allow_empty_fields):
                return parsed

            prompt = json.dumps(
                {
                    "retry": True,
                    "reason": "One or more required fields were empty. Fill all required fields with concrete content.",
                    "original_payload": payload,
                },
                ensure_ascii=False,
            )
            current_max_tokens = max(current_max_tokens, 140 if _is_nano_model(self.model) else 220)

        return _fallback_payload_for_task(task, payload, parsed)

    def healthcheck(self) -> dict[str, Any]:
        if self._fallback_backend is not None:
            return {
                "ok": True,
                "backend": self._fallback_backend.backend_name,
                "model": self.model,
                "warning": _mock_fallback_warning(self._fallback_reason or "unknown error"),
            }
        try:
            for attempt in range(3):
                try:
                    text = self._request_json_text("Верни только JSON.", '{"ping":"pong"}', 16)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(1.5 * (attempt + 1))
            self.usage.register('{"ping":"pong"}', text)
            return {"ok": True, "backend": self.backend_name, "model": self.model}
        except Exception as exc:
            if self.allow_fallback_to_mock and _should_fallback_to_mock(str(exc)):
                self._enable_mock_fallback(str(exc))
                return {
                    "ok": True,
                    "backend": self._fallback_backend.backend_name,
                    "model": self.model,
                    "warning": _mock_fallback_warning(str(exc)),
                }
            return {
                "ok": False,
                "backend": self.backend_name,
                "model": self.model,
                "error": str(exc),
                "diagnostics": _collect_openrouter_diagnostics(self.api_key),
            }

    def child_summary(self, initial_claim: str, final_claim: str) -> str:
        if self._fallback_backend is not None:
            return self._fallback_backend.child_summary(initial_claim, final_claim)

        prompt = json.dumps(
            {
                "initial_claim": initial_claim,
                "final_claim": final_claim,
                "task": "child_summary",
            },
            ensure_ascii=False,
        )
        system = (
            "Ты переводишь философский итог спора для ребенка 10 лет.\n"
            "Объясни простыми словами, очень коротко, без терминологической тяжести.\n"
            "Не копируй взрослый тезис буквально.\n"
            "Верни только JSON по схеме."
        )
        schema = {
            "name": "child_summary_payload",
            "schema": {
                "type": "object",
                "properties": {"child_summary": {"type": "string"}},
                "required": ["child_summary"],
                "additionalProperties": False,
            },
        }

        for transport_attempt in range(3):
            try:
                text = self._request_json_text(system, prompt, 90)
                self.usage.register(prompt, text)
                parsed = _parse_json(text)
                summary = str(parsed.get("child_summary", "")).strip()
                if summary:
                    return summary
            except Exception:
                if transport_attempt == 2:
                    break
                time.sleep(1.5 * (transport_attempt + 1))

        return _fallback_child_summary(final_claim)

    def balance_info(self) -> dict[str, Any]:
        if self._balance_cache is not None:
            return self._balance_cache

        manual = os.getenv("OPENROUTER_BALANCE_USD", "").strip() or os.getenv("OPENAI_BALANCE_USD", "").strip()
        if manual:
            try:
                value = float(manual.replace(",", "."))
                self._balance_cache = {"available_usd": value, "source": "env"}
                return self._balance_cache
            except ValueError:
                self._balance_cache = {
                    "available_usd": None,
                    "source": "env",
                    "error": "OPENROUTER_BALANCE_USD имеет неверный формат",
                }
                return self._balance_cache

        if self._fallback_backend is not None:
            self._balance_cache = {
                "available_usd": None,
                "source": "mock_fallback",
                "error": self._fallback_reason or "OpenRouter unavailable",
            }
            return self._balance_cache

        self._balance_cache = _fetch_openrouter_balance()
        return self._balance_cache

    def _enable_mock_fallback(self, reason: str) -> None:
        if self._fallback_backend is None:
            fallback = MockBackend()
            fallback.usage = self.usage
            self._fallback_backend = fallback
        self._fallback_reason = reason


class MockBackend(BaseBackend):
    def __init__(self, seed: int = 7) -> None:
        super().__init__()
        self.random = random.Random(seed)
        self.backend_name = "mock"

    def json_completion(
        self,
        agent: AgentProfile,
        instruction: str,
        payload: dict[str, Any],
        max_tokens: int = 160,
    ) -> dict[str, Any]:
        claim = str(payload.get("claim", ""))
        summary = str(payload.get("history", "")).lower()
        prompt = json.dumps(payload, ensure_ascii=False)
        kind = payload.get("task")

        if kind == "position":
            if agent.name == "Протагор":
                text = {
                    "stance": "support",
                    "speech": f"Тезис '{claim}' можно удержать, если сузить его без потери ядра.",
                }
            else:
                text = {
                    "stance": self.random.choice(["challenge", "qualify"]),
                    "speech": f"{agent.name} уже видит в тезисе зону уязвимости.",
                }
        elif kind == "question":
            text = {
                "question": _mock_question(agent.name, claim),
                "detected_issue": _mock_issue(agent.name),
            }
        elif kind == "answer":
            text = _mock_answer(claim)
        elif kind == "vote":
            contradiction = any(
                token in summary
                for token in ["контрпример", "предопредел", "неопределенность", "слишком широк", "критерий"]
            )
            candidate_refined = str(payload.get("candidate_refined_claim", "")).strip()
            if agent.name == "Синтезатор" and contradiction:
                status = "spawn_new_claim"
            elif agent.name == "Скептик" and contradiction and "слишком широк" not in summary:
                status = "refute"
            elif contradiction:
                status = "refine"
            else:
                status = "provisionally_accept"

            text = {
                "status": status,
                "rationale": _mock_rationale(status),
                "contradiction_found": contradiction and status in {"refine", "refute"},
                "refined_claim": candidate_refined if status in {"refine", "refute"} else "",
                "new_claim": _mock_new_claim(claim) if status == "spawn_new_claim" else "",
            }
        else:
            text = {"text": "noop"}

        completion = json.dumps(text, ensure_ascii=False)
        self.usage.register(prompt, completion)
        return text

    def child_summary(self, initial_claim: str, final_claim: str) -> str:
        return _fallback_child_summary(final_claim)


def _mock_question(agent_name: str, claim: str) -> str:
    if agent_name == "Скептик":
        if "свобода воли" in claim.lower():
            return "Если выбор предопределен состоянием мозга, где здесь свобода воли?"
        return f"Какой контрпример прямо ломает тезис '{claim}'?"
    if agent_name == "Педант":
        return "Какой ключевой термин здесь не определен и по какому критерию вы его проверяете?"
    if agent_name == "Прагматик":
        return "Как тезис меняет практическое решение в двух похожих реальных случаях?"
    return "Какой более узкий тезис делает спор продуктивнее, чем исходная формулировка?"


def _mock_issue(agent_name: str) -> str:
    mapping = {
        "Скептик": "сильный контрпример к общей формулировке",
        "Педант": "неясный критерий ключевого термина",
        "Прагматик": "разрыв между тезисом и наблюдаемыми последствиями",
        "Синтезатор": "из тезиса напрашивается более сильная альтернатива",
    }
    return mapping.get(agent_name, "слабое место тезиса")


def _mock_answer(claim: str) -> dict[str, Any]:
    claim_lower = claim.lower()
    if "свобода воли" in claim_lower:
        return {
            "answer": "Свобода воли не абсолютна: это ограниченная способность к осознанному выбору.",
            "concedes_point": True,
            "refined_claim": "Свобода воли существует как ограниченная способность выбирать в рамках причинных ограничений.",
        }
    if "ии" in claim_lower:
        return {
            "answer": "Сильнее будет тезис о моральной личности ИИ только при ясных критериях автономии и ответственности.",
            "concedes_point": True,
            "refined_claim": "Достаточно развитый ИИ может считаться моральной личностью только при проверяемых критериях автономии и ответственности.",
        }
    return {
        "answer": "Тезис лучше удерживать в более узкой и проверяемой форме.",
        "concedes_point": True,
        "refined_claim": f"Тезис '{claim}' верен только в ограниченной и уточненной формулировке.",
    }


def _mock_new_claim(claim: str) -> str:
    if "свобода воли" in claim.lower():
        return "Свобода требует не абсолютной независимости, а способности к рефлексивному самоконтролю."
    if "ии" in claim.lower():
        return "Моральная личность ИИ зависит не от интеллекта как такового, а от способности нести понятную ответственность."
    return f"Новый тезис: спор полезнее вести не о '{claim}', а о его проверяемой альтернативе."


def _mock_rationale(status: str) -> str:
    mapping = {
        "refine": "Исходный тезис слишком широк и требует сужения.",
        "refute": "Найдено противоречие, которое ломает текущую формулировку.",
        "provisionally_accept": "Сильного удара по тезису пока не найдено.",
        "spawn_new_claim": "Обсуждение породило более сильный дочерний тезис.",
    }
    return mapping[status]


def _role_hint(agent_name: str, task: str) -> str:
    by_agent = {
        "Протагор": {
            "position": "ищи защищаемое ядро тезиса и сразу намечай узкую версию",
            "answer": "защищай коротко; если удар сильный, уступай и формулируй более точный тезис",
            "vote": "не держись за проигранную формулировку любой ценой; если нужно, честно выбирай refine",
        },
        "Скептик": {
            "position": "оспаривай тезис через контрпример или несовместимость",
            "question": "задавай острый вопрос, который ставит тезис на грань refute",
            "vote": "предпочитай refute, если у тезиса нет ясного критерия или найден сильный контрпример",
        },
        "Педант": {
            "position": "ищи неясные слова и недостающие критерии",
            "question": "требуй точного определения и проверяемого критерия",
            "vote": "предпочитай refine, если можно спасти тезис через строгую формулировку",
        },
        "Прагматик": {
            "position": "переводи тезис в наблюдаемые последствия",
            "question": "бей по разрыву между словом и практикой",
            "vote": "предпочитай refute, если тезис ничего не меняет в реальных случаях",
        },
        "Синтезатор": {
            "position": "сразу ищи более сильную альтернативную формулировку",
            "question": "задавай вопрос, который открывает путь к новому тезису",
            "vote": "если спор породил самостоятельную и плодотворную альтернативу, выбирай spawn_new_claim, а не refine",
        },
    }
    agent_rules = dict(by_agent.get(agent_name, {}))
    if agent_name == "Синтезатор":
        agent_rules.update(
            {
                "position": "Ищи не косметическое уточнение, а новую более сильную идею, способную заменить исходный тезис",
                "question": "Задавай вопрос, который заставляет пересобрать саму рамку спора, а не просто сузить формулировку",
                "vote": "Если видишь самостоятельную новую идею, которая плодотворнее исходного тезиса, выбирай spawn_new_claim даже если refine тоже возможен",
            }
        )
    return agent_rules.get(task) or agent_rules.get("position") or "действуй по роли"


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _schema_for_task(task: str) -> dict[str, Any]:
    schemas: dict[str, dict[str, Any]] = {
        "position": {
            "name": "position_payload",
            "schema": {
                "type": "object",
                "properties": {
                    "stance": {"type": "string"},
                    "speech": {"type": "string"},
                },
                "required": ["stance", "speech"],
                "additionalProperties": False,
            },
        },
        "question": {
            "name": "question_payload",
            "schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "detected_issue": {"type": "string"},
                },
                "required": ["question", "detected_issue"],
                "additionalProperties": False,
            },
        },
        "answer": {
            "name": "answer_payload",
            "allow_empty_fields": ["refined_claim"],
            "schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "concedes_point": {"type": "boolean"},
                    "refined_claim": {"type": "string"},
                },
                "required": ["answer", "concedes_point", "refined_claim"],
                "additionalProperties": False,
            },
        },
        "vote": {
            "name": "vote_payload",
            "allow_empty_fields": ["refined_claim", "new_claim"],
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "rationale": {"type": "string"},
                    "contradiction_found": {"type": "boolean"},
                    "refined_claim": {"type": "string"},
                    "new_claim": {"type": "string"},
                },
                "required": [
                    "status",
                    "rationale",
                    "contradiction_found",
                    "refined_claim",
                    "new_claim",
                ],
                "additionalProperties": False,
            },
        },
    }
    return schemas.get(
        task,
        {
            "name": "generic_payload",
            "schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    )


def _has_required_content(
    payload: dict[str, Any],
    required_fields: list[str],
    allow_empty_fields: set[str],
) -> bool:
    for field in required_fields:
        value = payload.get(field)
        if isinstance(value, str) and not value.strip() and field not in allow_empty_fields:
            return False
        if value is None:
            return False
    return True


def _fallback_payload_for_task(
    task: str,
    original_payload: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    if task == "vote":
        status = str(parsed.get("status") or "refine").strip() or "refine"
        candidate_refined = str(original_payload.get("candidate_refined_claim", "")).strip()
        candidate_new = str(original_payload.get("candidate_new_claim", "")).strip()
        contradiction = bool(parsed.get("contradiction_found"))
        refined_claim = str(parsed.get("refined_claim", "")).strip()
        new_claim = str(parsed.get("new_claim", "")).strip()
        rationale = str(parsed.get("rationale", "")).strip()

        if status == "spawn_new_claim" and not new_claim:
            new_claim = candidate_new or candidate_refined
        if status in {"refine", "refute"} and not refined_claim:
            refined_claim = candidate_refined
        if not rationale:
            rationale_map = {
                "refine": "Тезис слишком широк и требует более точной формулировки.",
                "refute": "Найдена проблема, которая ломает текущую формулировку тезиса.",
                "provisionally_accept": "Сильного удара по тезису в этом раунде не найдено.",
                "spawn_new_claim": "Спор породил новую идею, которая сильнее простого уточнения.",
            }
            rationale = rationale_map.get(status, "Нужен более ясный вердикт по текущему тезису.")
        return {
            "status": status,
            "rationale": rationale,
            "contradiction_found": contradiction,
            "refined_claim": refined_claim if status in {"refine", "refute"} else "",
            "new_claim": new_claim if status == "spawn_new_claim" else "",
        }

    if task == "question":
        question = str(parsed.get("question", "")).strip()
        issue = str(parsed.get("detected_issue", "")).strip()
        claim = str(original_payload.get("claim", "")).strip()
        if not question:
            question = f"Какой контрпример сильнее всего проверяет тезис '{claim}'?"
        if not issue:
            issue = "непроясненное слабое место тезиса"
        return {"question": question, "detected_issue": issue}

    if task == "answer":
        answer = str(parsed.get("answer", "")).strip() or "Тезис приходится сузить, чтобы он остался осмысленным."
        refined_claim = str(parsed.get("refined_claim", "")).strip()
        if not refined_claim:
            refined_claim = str(original_payload.get("candidate_refined_claim", "")).strip()
        return {
            "answer": answer,
            "concedes_point": bool(parsed.get("concedes_point", True)),
            "refined_claim": refined_claim,
        }

    if task == "position":
        speech = str(parsed.get("speech", "")).strip() or "В тезисе есть место для серьезной проверки."
        stance = str(parsed.get("stance", "")).strip() or "qualify"
        return {"stance": stance, "speech": speech}

    return parsed


def _fallback_child_summary(final_claim: str) -> str:
    claim = final_claim.strip()
    lower = claim.lower()
    if "свобод" in lower and "вол" in lower:
        return "Простыми словами: на нас многое влияет, но человек все равно может выбирать не совсем как машина."
    if "язык" in lower or "мышлен" in lower:
        return "Простыми словами: думать можно не только словами, но словами легче проверять, правильно ли ты понял мысль."
    if "ии" in lower or "искусствен" in lower or "машин" in lower:
        return "Простыми словами: умная машина важна только тогда, когда она отвечает за свои решения."
    if "истин" in lower:
        return "Простыми словами: иногда правда зависит от того, откуда смотреть, но не всегда."
    return f"Простыми словами: {claim}"


def _should_fallback_to_mock(error_text: str) -> bool:
    lowered = error_text.lower()
    fatal_markers = [
        "unsupported_country_region_territory",
        "country, region, or territory not supported",
        "request_forbidden",
        "invalid_api_key",
        "incorrect_api_key",
        "insufficient_quota",
        "billing_hard_limit",
        "account_deactivated",
        "permission_denied",
        "error code: 401",
        "error code: 403",
    ]
    return any(marker in lowered for marker in fatal_markers)


def _should_retry_without_json_mode(error_text: str) -> bool:
    lowered = error_text.lower()
    retry_markers = [
        "response_format",
        "json_object",
        "json schema",
        "unsupported parameter",
        "invalid parameter",
    ]
    return any(marker in lowered for marker in retry_markers)


def _chat_completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return "{}"
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "") if message is not None else ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                text = getattr(item, "text", "")
                if text:
                    parts.append(str(text))
        return "\n".join(part for part in parts if part).strip() or "{}"
    return str(content).strip() or "{}"


def _mock_fallback_warning(error_text: str) -> str:
    normalized = " ".join(str(error_text).split())
    if len(normalized) > 180:
        normalized = normalized[:177] + "..."
    return f"OpenRouter недоступен, матч продолжится в mock-режиме. Причина: {normalized}"


def _collect_openrouter_diagnostics(api_key: str) -> list[str]:
    host = "openrouter.ai"
    diagnostics: list[str] = []
    dns_ok = False
    https_ok = False
    proxy_line = _proxy_env_summary()

    try:
        addresses = sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                if item and item[4]
            }
        )
        preview = ", ".join(addresses[:2])
        if len(addresses) > 2:
            preview += ", ..."
        hint = _address_routing_hint(addresses)
        if hint:
            diagnostics.append(f"DNS {host}: ok ({preview}; {hint})")
        else:
            diagnostics.append(f"DNS {host}: ok ({preview})")
        dns_ok = True
    except Exception as exc:
        diagnostics.append(f"DNS {host}: ошибка ({_short_text(str(exc), 80)})")

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    request = Request(f"https://{host}/api/v1/models", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=8) as response:
            diagnostics.append(f"HTTPS {host}: ok")
            diagnostics.append(f"OpenRouter API: HTTP {response.status}")
            https_ok = True
    except HTTPError as exc:
        https_ok = True
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        diagnostics.append(f"HTTPS {host}: ok")
        diagnostics.append(f"OpenRouter API: {_summarize_api_http_error(exc.code, body)}")
    except URLError as exc:
        diagnostics.append(f"HTTPS {host}: ошибка ({_short_text(str(exc.reason), 80)})")
        diagnostics.append("OpenRouter API: не удалось проверить из-за сетевой ошибки")
    except Exception as exc:
        diagnostics.append(f"HTTPS {host}: ошибка ({_short_text(str(exc), 80)})")
        diagnostics.append("OpenRouter API: не удалось проверить из-за ошибки подключения")

    curl_probe = _curl_probe(host, headers)
    if curl_probe:
        diagnostics.append(curl_probe)

    openssl_probe = _openssl_probe(host)
    if openssl_probe:
        diagnostics.append(openssl_probe)

    if dns_ok and https_ok:
        diagnostics.insert(0, "Интернет: ok")
    else:
        diagnostics.insert(0, "Интернет: есть проблема с подключением до OpenRouter")
    diagnostics.insert(1, proxy_line)
    return diagnostics


def _proxy_env_summary() -> str:
    names = ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY")
    parts: list[str] = []
    for name in names:
        raw = os.getenv(name) or os.getenv(name.lower()) or ""
        raw = raw.strip()
        if not raw:
            continue
        parts.append(f"{name}={_sanitize_proxy_value(name, raw)}")
    if not parts:
        return "Прокси env: не заданы"
    return _short_text(f"Прокси env: {'; '.join(parts)}", 180)


def _sanitize_proxy_value(name: str, value: str) -> str:
    if name == "NO_PROXY":
        return _short_text(value, 80)
    try:
        parsed = urlsplit(value)
    except Exception:
        parsed = None
    if parsed and parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc.rsplit("@", 1)[-1]
        port = f":{parsed.port}" if parsed.port else ""
        return _short_text(f"{parsed.scheme}://{host}{port}", 80)
    if "@" in value:
        value = value.rsplit("@", 1)[-1]
    return _short_text(value, 80)


def _address_routing_hint(addresses: list[str]) -> str:
    parsed = []
    for item in addresses:
        try:
            parsed.append(ipaddress.ip_address(item))
        except ValueError:
            continue
    if not parsed:
        return ""
    if all(_is_benchmark_address(item) for item in parsed):
        return "непубличный диапазон 198.18.0.0/15; похоже на VPN, прокси или DNS-подмену"
    suspicious = [str(item) for item in parsed if not item.is_global]
    if suspicious:
        preview = ", ".join(suspicious[:2])
        if len(suspicious) > 2:
            preview += ", ..."
        return f"есть непубличные адреса: {preview}; проверь VPN, прокси и DNS"
    return ""


def _is_benchmark_address(address: Any) -> bool:
    if not isinstance(address, ipaddress.IPv4Address):
        return False
    return address in ipaddress.ip_network("198.18.0.0/15")


def _curl_probe(host: str, headers: dict[str, str]) -> str | None:
    if not shutil.which("curl"):
        return None
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        "--max-time",
        "8",
    ]
    for name, value in headers.items():
        command.extend(["-H", f"{name}: {value}"])
    command.append(f"https://{host}/api/v1/models")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "curl: таймаут"
    except Exception as exc:
        return f"curl: ошибка запуска ({_short_text(str(exc), 80)})"
    if result.returncode == 0:
        status = result.stdout.strip() or "000"
        return f"curl: HTTP {status}"
    detail = result.stderr.strip() or result.stdout.strip() or f"rc={result.returncode}"
    return f"curl: ошибка rc={result.returncode} ({_short_text(detail, 100)})"


def _openssl_probe(host: str) -> str | None:
    if not shutil.which("openssl"):
        return None
    command = [
        "openssl",
        "s_client",
        "-brief",
        "-connect",
        f"{host}:443",
        "-servername",
        host,
    ]
    try:
        result = subprocess.run(
            command,
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "openssl: таймаут"
    except Exception as exc:
        return f"openssl: ошибка запуска ({_short_text(str(exc), 80)})"
    detail = result.stderr.strip() or result.stdout.strip()
    if result.returncode == 0:
        summary = _openssl_success_summary(detail)
        if summary:
            return f"openssl: TLS ok ({summary})"
        return "openssl: TLS ok"
    return f"openssl: ошибка ({_short_text(detail or f'rc={result.returncode}', 100)})"


def _openssl_success_summary(detail: str) -> str:
    for line in detail.splitlines():
        normalized = " ".join(line.split())
        lowered = normalized.lower()
        if lowered.startswith("protocol version:") or lowered.startswith("ciphersuite:"):
            return normalized
    return ""


def _summarize_api_http_error(status_code: int, body: str) -> str:
    try:
        payload = json.loads(body)
    except Exception:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else {}
    if not isinstance(error, dict):
        error = {}
    code = str(error.get("code") or "").strip()
    message = str(error.get("message") or "").strip()
    suffix = f" {code}" if code else ""
    if message:
        return f"HTTP {status_code}{suffix}: {_short_text(message, 120)}"
    return f"HTTP {status_code}{suffix}".strip()


def _short_text(text: str, limit: int) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _reasoning_effort_for_model(model: str) -> str | None:
    normalized = model.lower()
    if normalized.startswith("gpt-5"):
        return "low"
    return None


def _is_nano_model(model: str) -> bool:
    return model.lower().endswith("nano")


def _fetch_openrouter_balance() -> dict[str, Any]:
    return {
        "available_usd": None,
        "source": "manual_required",
        "error": "set OPENROUTER_BALANCE_USD or balance.txt for UI balance",
    }


def _extract_balance_value(payload: dict[str, Any]) -> float | None:
    candidates = [
        payload.get("total_available"),
        payload.get("available_balance"),
        payload.get("balance"),
    ]
    for candidate in candidates:
        if isinstance(candidate, (int, float)):
            return float(candidate)
        if isinstance(candidate, str):
            try:
                return float(candidate)
            except ValueError:
                continue
    return None
