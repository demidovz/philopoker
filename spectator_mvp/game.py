from __future__ import annotations

import re
from collections import Counter

from .config import AppConfig, PRICE_HINTS, load_config
from .llm import MockBackend, OpenRouterBackend
from .logging_utils import JsonlLogger
from .models import AgentProfile, DebateState, MoveRecord, RoundVerdict
from .ui import SpectatorUI


AGENTS = [
    AgentProfile(
        name="Протагор",
        role="Защитник тезиса",
        mission="удерживать сильную версию тезиса, но честно сужать его под давлением сильных вопросов",
        style="кратко, точно, без риторики",
    ),
    AgentProfile(
        name="Скептик",
        role="Разрушитель уверенности",
        mission="искать контрпример, скрытую несовместимость или ложную универсальность",
        style="жестко и конкретно",
    ),
    AgentProfile(
        name="Педант",
        role="Охотник за неясностью",
        mission="требовать определений, критериев и проверяемых формулировок",
        style="сухо и формально",
    ),
    AgentProfile(
        name="Прагматик",
        role="Проверка реальностью",
        mission="сводить тезис к последствиям, наблюдаемым случаям и практическим различиям",
        style="приземленно и предметно",
    ),
    AgentProfile(
        name="Синтезатор",
        role="Генератор нового тезиса",
        mission="предлагать более сильную, узкую или неожиданно плодотворную альтернативу",
        style="спокойно и конструктивно",
    ),
]


POSITION_INSTRUCTION = """
Сначала оцени тезис. Ответ в JSON:
{"stance":"support|challenge|qualify","speech":"одна фраза до 20 слов"}
"""

QUESTION_INSTRUCTION = """
Сформулируй один сильный сократический вопрос.
Требования:
- бей в противоречие, скрытую предпосылку, контрпример или критерий проверки;
- не повторяй уже заданные вопросы и уже атакованные слабые места;
- не задавай пустой общий вопрос.
Ответ в JSON:
{"question":"один короткий вопрос до 20 слов","detected_issue":"одно конкретное слабое место тезиса"}
"""

ANSWER_INSTRUCTION = """
Ответь как защитник тезиса.
Требования:
- не повторяй вопрос;
- либо дай конкретную защиту, либо честно признай удар и сузь тезис;
- refined_claim должен быть чистой новой формулировкой тезиса, без мета-комментариев;
- ответ должен быть короче и яснее, чем обычная дискуссионная реплика.
Ответ в JSON:
{"answer":"один краткий ответ до 24 слов","concedes_point":true,"refined_claim":"если нужно, новая строгая формулировка; иначе пустая строка"}
"""

VOTE_INSTRUCTION = """
Дай вердикт по текущему состоянию тезиса.
Правила:
- contradiction_found=true только если реально найдено существенное противоречие, сильный контрпример или критическая неясность;
- refined_claim заполняй только если тезис надо сузить;
- new_claim заполняй только если обсуждение породило новый самостоятельный тезис;
- объясни причину кратко и предметно.
Ответ в JSON:
{"status":"refine|refute|provisionally_accept|spawn_new_claim","rationale":"одно конкретное предложение","contradiction_found":true,"refined_claim":"если нужен уточненный тезис","new_claim":"если нужен новый тезис; иначе пустая строка"}
"""


class SocraticMatch:
    def __init__(self, config: AppConfig, live_ui: bool = True) -> None:
        self.config = config
        self.live_ui = live_ui
        self.ui = SpectatorUI(config.pause_mode) if live_ui else None
        self.backend = self._build_backend()
        self.state = DebateState(
            current_claim=config.thesis,
            initial_claim=config.thesis,
            scores={agent.name: 0 for agent in AGENTS},
        )
        self.logger = JsonlLogger(config.log_path)

    def _build_backend(self):
        if self.config.mode == "openrouter":
            if not self.config.api_key:
                raise RuntimeError("Для режима openrouter нужен OPENROUTER_API_KEY.")
            return OpenRouterBackend(
                api_key=self.config.api_key,
                model=self.config.model,
                temperature=self.config.temperature,
                allow_fallback_to_mock=False,
            )
        return MockBackend()

    def run(self, health: dict[str, object] | None = None) -> None:
        health = health or self.backend.healthcheck()
        balance = self.backend.balance_info()
        if not health.get("ok"):
            raise RuntimeError(
                f"Backend {health.get('backend')} недоступен: {health.get('error', 'unknown error')}"
            )
            error_text = str(health.get("error", "unknown error"))
            if health.get("backend") == "openrouter" and "server_error" in error_text:
                health["warning"] = (
                    "OpenRouter временно ответил server_error на ping. Матч продолжается, "
                    "но старт может быть медленнее."
                )
                health["ok"] = True
                health.pop("error", None)
            else:
                raise RuntimeError(
                    f"Backend {health.get('backend')} недоступен: {health.get('error', 'unknown error')}"
                )

        self._maybe_banner("СОКРАТИЧЕСКИЙ ПОЕДИНОК", "Наблюдательский режим")
        self._maybe_emit("Режим", self.config.mode)
        self._maybe_emit("Backend", health.get("backend", "unknown"))
        self._maybe_emit("Модель", self.config.model)
        self._emit_balance_info(balance)
        if health.get("warning"):
            self._maybe_emit("Предупр.", health["warning"])
        self._maybe_emit("Тезис", self.state.current_claim)
        self._maybe_emit("Лог", str(self.config.log_path))
        self._emit_price_hint()

        self.logger.write(
            "match_started",
            {
                "mode": self.config.mode,
                "backend": health.get("backend", "unknown"),
                "model": self.config.model,
                "rounds": self.config.rounds,
                "thesis": self.state.current_claim,
                "balance": balance,
                "log_path": str(self.config.log_path),
            },
        )
        self.logger.write("backend_healthcheck", health)
        self.logger.write("seating", {"players": [agent for agent in AGENTS]})
        self._maybe_pause()

        for round_index in range(1, self.config.rounds + 1):
            verdict = self.play_round(round_index)
            if verdict.status == "refute":
                break
            if verdict.status == "spawn_new_claim" and verdict.new_claim:
                self.state.current_claim = verdict.new_claim
            elif verdict.status == "refine" and verdict.refined_claim:
                self.state.current_claim = verdict.refined_claim

        self._show_footer()

    def play_round(self, round_index: int) -> RoundVerdict:
        self._maybe_banner("СОКРАТИЧЕСКИЙ ПОЕДИНОК", f"Раунд {round_index}")
        self._maybe_emit("Тезис", self.state.current_claim)
        self.logger.write("round_started", {"round": round_index, "claim": self.state.current_claim})
        self.logger.write(
            "arbiter_message",
            {
                "round": round_index,
                "title": f"Раунд {round_index} начинается",
                "text": f"Арбитр выносит на стол тезис: {self.state.current_claim}",
                "level": "info",
            },
        )

        round_points = Counter({agent.name: 0 for agent in AGENTS})
        self._maybe_section("Позиции")
        for agent in AGENTS:
            result = self.backend.json_completion(
                agent,
                POSITION_INSTRUCTION,
                {
                    "task": "position",
                    "claim": self.state.current_claim,
                    "history": self.state.compact_history(limit=4),
                },
            )
            stance = str(result.get("stance", "qualify")).strip()
            speech = str(result.get("speech", "")).strip()
            if speech:
                round_points[agent.name] += 1

            self.state.history.append(MoveRecord(agent.name, "position", f"{stance}: {speech}"))
            self._maybe_emit(agent.name, f"[{stance}] {speech}")
            self.logger.write(
                "position",
                {
                    "round": round_index,
                    "agent": agent,
                    "claim": self.state.current_claim,
                    "stance": stance,
                    "speech": speech,
                },
            )
            self._maybe_pause()

        defender = AGENTS[0]
        candidate_refined_claims: list[str] = []
        asked_questions: list[str] = []
        attacked_issues: list[str] = []
        self._maybe_section("Вопросы")

        for agent in AGENTS[1:]:
            question_data = self.backend.json_completion(
                agent,
                QUESTION_INSTRUCTION,
                {
                    "task": "question",
                    "claim": self.state.current_claim,
                    "history": self.state.compact_history(limit=6),
                    "asked_questions": asked_questions,
                    "attacked_issues": attacked_issues,
                    "round": round_index,
                },
            )
            question = str(question_data.get("question", "")).strip()
            detected_issue = str(question_data.get("detected_issue", "")).strip()

            if question:
                round_points[agent.name] += 2
                asked_questions.append(question)
            if detected_issue:
                round_points[agent.name] += 2
                attacked_issues.append(detected_issue)

            self.state.history.append(MoveRecord(agent.name, "question", question))
            self._maybe_emit(agent.name, question)
            if detected_issue:
                self._maybe_emit("Атака", detected_issue)
            self.logger.write(
                "question",
                {
                    "round": round_index,
                    "agent": agent,
                    "claim": self.state.current_claim,
                    "question": question,
                    "detected_issue": detected_issue,
                },
            )
            self._maybe_pause()

            answer_data = self.backend.json_completion(
                defender,
                ANSWER_INSTRUCTION,
                {
                    "task": "answer",
                    "claim": self.state.current_claim,
                    "question": question,
                    "detected_issue": detected_issue,
                    "history": self.state.compact_history(limit=8),
                    "candidate_refined_claims": candidate_refined_claims,
                },
            )
            answer = str(answer_data.get("answer", "")).strip()
            refined_claim = _clean_optional_text(answer_data.get("refined_claim", ""))
            conceded = bool(answer_data.get("concedes_point", False))

            if answer:
                round_points[defender.name] += 1
            if conceded:
                round_points[defender.name] += 1
            if refined_claim:
                round_points[defender.name] += 1
                candidate_refined_claims.append(refined_claim)

            self.state.history.append(MoveRecord(defender.name, "answer", answer))
            self._maybe_emit(defender.name, answer)
            if refined_claim:
                self._maybe_emit("Уточнение", refined_claim)
            self.logger.write(
                "answer",
                {
                    "round": round_index,
                    "agent": defender,
                    "claim": self.state.current_claim,
                    "question": question,
                    "answer": answer,
                    "refined_claim": refined_claim,
                    "concedes_point": conceded,
                },
            )
            self._maybe_pause()

        self._maybe_section("Вердикт")
        candidate_refined_claim = (
            Counter(candidate_refined_claims).most_common(1)[0][0]
            if candidate_refined_claims
            else ""
        )
        verdict = self._collect_votes(
            round_index,
            round_points,
            candidate_refined_claim,
            asked_questions,
            attacked_issues,
        )

        for name in self.state.scores:
            self.state.scores[name] = self.state.scores.get(name, 0) + verdict.points.get(name, 0)

        for event_text in verdict.events:
            self.logger.write("round_event", {"round": round_index, "text": event_text})

        self.state.round_winners.append(verdict.winner or "")
        self.state.round_summaries.append(
            f"Раунд {round_index}: {verdict.human_status or verdict.status}. {verdict.rationale}"
        )
        self._maybe_emit("Статус", verdict.human_status or verdict.status)
        self._maybe_emit("Причина", verdict.rationale)
        if verdict.refined_claim:
            self._maybe_emit("Уточнение", verdict.refined_claim)
        if verdict.new_claim:
            self._maybe_emit("Новый тезис", verdict.new_claim)
        if verdict.events:
            self._maybe_emit_block("События", verdict.events)
        self._maybe_scoreboard("Очки раунда", verdict.points)

        self.logger.write(
            "round_finished",
            {
                "round": round_index,
                "claim": self.state.current_claim,
                "verdict": verdict,
                "scores_after_round": self.state.scores,
            },
        )
        self.logger.write(
            "arbiter_message",
            {
                "round": round_index,
                "title": "Вердикт арбитра",
                "text": self._build_arbiter_summary(verdict),
                "level": "highlight",
            },
        )
        self._maybe_pause()
        return verdict

    def _collect_votes(
        self,
        round_index: int,
        round_points: Counter,
        candidate_refined_claim: str,
        asked_questions: list[str],
        attacked_issues: list[str],
    ) -> RoundVerdict:
        statuses: list[str] = []
        rationales: list[str] = []
        refined_claims: list[str] = []
        new_claims: list[str] = []
        contradiction_votes = 0
        votes_by_agent: dict[str, dict[str, object]] = {}

        for agent in AGENTS:
            vote = self.backend.json_completion(
                agent,
                VOTE_INSTRUCTION,
                {
                    "task": "vote",
                    "claim": self.state.current_claim,
                    "history": self.state.compact_history(limit=10),
                    "candidate_refined_claim": candidate_refined_claim,
                    "attacked_issues": attacked_issues,
                    "questions_asked": asked_questions,
                },
                max_tokens=120,
            )

            status = str(vote.get("status", "refine")).strip()
            rationale = str(vote.get("rationale", "")).strip()
            refined_claim = _clean_optional_text(vote.get("refined_claim", ""))
            new_claim = _clean_optional_text(vote.get("new_claim", ""))
            contradiction_found = bool(vote.get("contradiction_found", False))

            statuses.append(status)
            rationales.append(rationale)
            votes_by_agent[agent.name] = {
                "status": status,
                "contradiction_found": contradiction_found,
            }

            if rationale:
                round_points[agent.name] += 1
            if contradiction_found and agent.name != "Протагор":
                round_points[agent.name] += 2
                contradiction_votes += 1
            if refined_claim:
                refined_claims.append(refined_claim)
            if new_claim:
                new_claims.append(new_claim)
                if agent.name == "Синтезатор":
                    round_points[agent.name] += 5
                else:
                    round_points[agent.name] += 1

            self._maybe_emit(agent.name, f"{status} | {rationale}")
            self.logger.write(
                "vote",
                {
                    "round": round_index,
                    "agent": agent,
                    "claim": self.state.current_claim,
                    "status": status,
                    "rationale": rationale,
                    "contradiction_found": contradiction_found,
                    "refined_claim": refined_claim,
                    "new_claim": new_claim,
                },
            )
            self._maybe_pause()

        majority_status = Counter(statuses).most_common(1)[0][0]
        refined_claim = Counter(refined_claims).most_common(1)[0][0] if refined_claims else None
        new_claim = Counter(new_claims).most_common(1)[0][0] if new_claims else None
        rationale = next(
            (item for item, status in zip(rationales, statuses) if status == majority_status and item),
            rationales[0] if rationales else "",
        )
        contradiction_found = contradiction_votes >= 2

        self._award_status_bonus(round_points, votes_by_agent, majority_status, refined_claim, new_claim)
        winner = self._resolve_round_winner(majority_status, round_points, votes_by_agent)
        team = self._team_for_agent(winner)
        events = self._build_round_events(
            majority_status,
            contradiction_found,
            refined_claim,
            new_claim,
        )

        return RoundVerdict(
            status=majority_status,
            rationale=rationale,
            new_claim=new_claim,
            refined_claim=refined_claim,
            contradiction_found=contradiction_found,
            winner=winner,
            team=team,
            points=dict(round_points),
            events=events,
            human_status=_human_status(majority_status),
        )

    def _award_status_bonus(
        self,
        points: Counter,
        votes_by_agent: dict[str, dict[str, object]],
        majority_status: str,
        refined_claim: str | None,
        new_claim: str | None,
    ) -> None:
        if majority_status == "refute":
            for name, vote in votes_by_agent.items():
                if vote["status"] == "refute" and name != "Протагор":
                    points[name] += 2
        elif majority_status == "provisionally_accept":
            if votes_by_agent.get("Протагор", {}).get("status") == "provisionally_accept":
                points["Протагор"] += 3
            for name, vote in votes_by_agent.items():
                if vote["status"] == "provisionally_accept":
                    points[name] += 1
        elif majority_status == "refine":
            for name, vote in votes_by_agent.items():
                if vote["status"] == "refine":
                    points[name] += 1
            if refined_claim and votes_by_agent.get("Педант", {}).get("status") == "refine":
                points["Педант"] += 2
        elif majority_status == "spawn_new_claim":
            for name, vote in votes_by_agent.items():
                if vote["status"] == "spawn_new_claim":
                    points[name] += 3
            if new_claim and votes_by_agent.get("Синтезатор", {}).get("status") == "spawn_new_claim":
                points["Синтезатор"] += 5

    def _resolve_round_winner(
        self,
        status: str,
        points: Counter,
        votes_by_agent: dict[str, dict[str, object]],
    ) -> str:
        if status == "refute":
            candidates = [
                name
                for name, vote in votes_by_agent.items()
                if vote["status"] == "refute" and name != "Протагор"
            ]
            return self._best_scored(points, candidates, fallback="Скептик")

        if status == "spawn_new_claim":
            candidates = [
                name for name, vote in votes_by_agent.items() if vote["status"] == "spawn_new_claim"
            ]
            if "Синтезатор" in candidates:
                return "Синтезатор"
            return self._best_scored(points, candidates, fallback="Синтезатор")

        if status == "provisionally_accept":
            if votes_by_agent.get("Протагор", {}).get("status") == "provisionally_accept":
                return "Протагор"
            candidates = [
                name for name, vote in votes_by_agent.items() if vote["status"] == "provisionally_accept"
            ]
            return self._best_scored(points, candidates, fallback="Протагор")

        candidates = [name for name, vote in votes_by_agent.items() if vote["status"] == "refine"]
        preferred = [name for name in candidates if name != "Протагор"]
        return self._best_scored(points, preferred or candidates, fallback="Педант")

    def _best_scored(self, points: Counter, candidates: list[str], fallback: str) -> str:
        if not candidates:
            return fallback
        return sorted(candidates, key=lambda name: (-points.get(name, 0), name))[0]

    def _build_round_events(
        self,
        status: str,
        contradiction_found: bool,
        refined_claim: str | None,
        new_claim: str | None,
    ) -> list[str]:
        events: list[str] = []
        if contradiction_found:
            events.append("Найдено существенное противоречие или сильный контрпример.")
        if refined_claim:
            events.append(f"Текущий тезис сужен: {refined_claim}")
        if new_claim:
            events.append(f"Порожден новый тезис: {new_claim}")
        if status == "refute":
            events.append("Исходная формулировка не выдержала проверку раунда.")
        elif status == "provisionally_accept":
            events.append("Тезис временно удержан: критики не добили его в этом раунде.")
        elif status == "spawn_new_claim":
            events.append("Спор сместился: новый тезис оказался продуктивнее исходного.")
        return events

    def _emit_price_hint(self) -> None:
        prices = PRICE_HINTS.get(self.config.model)
        if not prices:
            return
        text = (
            f"ориентир API: input ${prices['input_per_1m']}/1M, "
            f"output ${prices['output_per_1m']}/1M токенов"
        )
        self._maybe_emit("Цена", text)

    def _emit_balance_info(self, balance: dict[str, object] | None) -> None:
        if not isinstance(balance, dict):
            return
        value = balance.get("available_usd")
        if isinstance(value, (int, float)):
            self._maybe_emit("Баланс API", f"${float(value):.2f}")
            return
        source = str(balance.get("source", "unknown"))
        if source == "env":
            self._maybe_emit("Баланс API", "не удалось прочитать из OPENROUTER_BALANCE_USD")
            return
        if source == "manual_required":
            self._maybe_emit("Баланс API", "задай OPENROUTER_BALANCE_USD или balance.txt")
            return
        self._maybe_emit("Баланс API", "недоступно")

    def _show_footer(self) -> None:
        self._maybe_banner("МАТЧ ЗАВЕРШЕН", "Итоги")
        initial_claim = self.state.initial_claim or self.state.current_claim
        final_claim = _compress_claim(self.state.current_claim)
        balance = self.backend.balance_info()
        self.state.current_claim = final_claim
        change_summary = self._build_change_summary(initial_claim, final_claim)
        self.state.child_summary = self.backend.child_summary(initial_claim, final_claim)
        if not self.state.child_summary:
            self.state.child_summary = _child_summary(final_claim)
        self._maybe_emit("Было", initial_claim)
        self._maybe_emit("Финальный тезис", final_claim)
        self._maybe_emit("Что изменилось", change_summary)
        self._maybe_emit("Для ребенка", self.state.child_summary)
        self._maybe_emit_block("Сводка", self.state.round_summaries or ["Раунды не состоялись."])
        self._maybe_scoreboard("Общий счет", self.state.scores)
        champion = self._resolve_match_champion()
        estimated = self.backend.usage.estimated_cost_usd(self.config.model)
        self._maybe_emit("Победитель", champion)
        self._emit_balance_info(balance)
        self._maybe_emit("Вызовы", str(self.backend.usage.calls))
        if estimated is not None:
            self._maybe_emit("Оценка $", f"{estimated:.6f}")
        self._maybe_emit("Лог", str(self.config.log_path))
        self.logger.write(
            "match_finished",
            {
                "initial_claim": initial_claim,
                "final_claim": final_claim,
                "change_summary": change_summary,
                "round_summaries": self.state.round_summaries,
                "round_winners": self.state.round_winners,
                "scores": self.state.scores,
                "champion": champion,
                "child_summary": self.state.child_summary,
                "balance": balance,
                "calls": self.backend.usage.calls,
                "estimated_cost_usd": estimated,
            },
        )

    def _resolve_match_champion(self) -> str:
        wins = Counter(name for name in self.state.round_winners if name)
        return sorted(
            self.state.scores,
            key=lambda name: (-wins.get(name, 0), -self.state.scores.get(name, 0), name),
        )[0]

    def _build_change_summary(self, initial_claim: str, final_claim: str) -> str:
        if initial_claim.strip() == final_claim.strip():
            return "Философы не сдвинули тезис: он пережил матч почти без изменений."
        last_summary = self.state.round_summaries[-1] if self.state.round_summaries else ""
        if "сломался" in last_summary:
            return "Сильная критика показала, что исходная формулировка не выдерживает проверку."
        if "родилась новая идея" in last_summary:
            return "Спор вывел участников к более удачной новой идее, чем исходный тезис."
        return "Спор сузил исходную мысль и превратил ее в более точную и осторожную формулировку."

    def _team_for_agent(self, agent_name: str) -> str:
        if agent_name == "Протагор":
            return "защита"
        if agent_name == "Синтезатор":
            return "синтез"
        if agent_name == "Педант":
            return "уточнение"
        return "критика"

    def _build_arbiter_summary(self, verdict: RoundVerdict) -> str:
        parts = []
        parts.extend(verdict.events)
        parts.append(f"Победитель раунда: {verdict.winner}.")
        parts.append(f"Тип результата: {verdict.human_status or verdict.status}.")
        parts.append(verdict.rationale)
        return " ".join(parts)

    def _maybe_scoreboard(self, title: str, scores: dict[str, int]) -> None:
        if not self.ui:
            return
        rows = [(agent.name, agent.role, f"{scores.get(agent.name, 0)} очк.") for agent in AGENTS]
        self.ui.scoreboard(title, rows)

    def _maybe_banner(self, title: str, subtitle: str) -> None:
        if self.ui:
            self.ui.banner(title, subtitle)

    def _maybe_section(self, title: str) -> None:
        if self.ui:
            self.ui.section(title)

    def _maybe_emit(self, label: str, text: str) -> None:
        if self.ui:
            self.ui.emit(label, text)

    def _maybe_emit_block(self, label: str, lines: list[str]) -> None:
        if self.ui:
            self.ui.emit_block(label, lines)

    def _maybe_pause(self) -> None:
        if self.ui:
            self.ui.pause()


def main() -> None:
    config = load_config()
    match = SocraticMatch(config)
    match.run()


def _clean_optional_text(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"нет", "none", "null", "n/a", "-", "пусто"}:
        return ""
    return text


def _human_status(status: str) -> str:
    mapping = {
        "refine": "тезис уточнили",
        "refute": "тезис сломался",
        "provisionally_accept": "тезис пока держится",
        "spawn_new_claim": "родилась новая идея",
    }
    return mapping.get(status, status)


def _child_summary(claim: str) -> str:
    text = claim.strip()
    lower = text.lower()
    words = set(re.findall(r"[а-яё]+", lower))
    has_stem = lambda *stems: any(any(word.startswith(stem) for word in words) for stem in stems)

    if has_stem("свобод") and has_stem("вол"):
        return "Простыми словами: на нас влияет мир вокруг, но у человека все равно может быть свой настоящий выбор."
    if "ии" in words or has_stem("искусствен", "машин"):
        return "Простыми словами: умная машина важна не сама по себе, а если она умеет отвечать за свои решения."
    if has_stem("язык", "мышлен"):
        return "Простыми словами: думать можно не только словами, но проверять мысли легче, когда мы можем их ясно выразить."
    if has_stem("красот"):
        return "Простыми словами: красота рождается не только в вещи и не только в голове человека, а между ними."
    if has_stem("истин"):
        return "Простыми словами: иногда правда зависит от точки зрения, но не всякая правда меняется от взгляда."

    simple = _compress_claim(text, limit=140)
    return f"Простыми словами: {simple}"


def _compress_claim(text: str, limit: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= limit and len(re.findall(r"[.!?]", cleaned)) <= 2:
        return cleaned

    sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if sentence_parts:
        candidate = " ".join(sentence_parts[:2])
        if len(candidate) <= limit:
            return candidate
        cleaned = candidate

    match = re.search(r", но ", cleaned, flags=re.IGNORECASE)
    if match:
        head = _trim_clause(cleaned[: match.start()].strip(" ,."), limit // 2)
        tail = _trim_clause(cleaned[match.end() :].strip(" ,."), limit // 2)
        return f"{head}, но {tail}."

    return _trim_clause(cleaned, limit).rstrip(" ,.") + "."


def _trim_clause(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].strip()
    return (shortened or text[:limit]).rstrip(" ,.") + "..."
