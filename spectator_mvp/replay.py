from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ui import SpectatorUI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Реплей партии из jsonl-лога.")
    parser.add_argument("path", help="Путь к jsonl-логу партии.")
    parser.add_argument("--pause", choices=["key", "enter", "off"], default="key")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ui = SpectatorUI(args.pause)
    path = Path(args.path).resolve()
    replay(load_events(path), ui, path)


def load_events(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def replay(events: list[dict], ui: SpectatorUI, path: Path) -> None:
    match_title = "РЕПЛЕЙ СОКРАТИЧЕСКОЙ ПАРТИИ"
    thesis = ""
    initial_thesis = ""
    round_label = "Подготовка"
    spotlight_title = "СТАРТ МАТЧА"
    spotlight_lines = [f"Загружен лог: {path.name}"]
    feed_lines: list[str] = []
    roles: dict[str, str] = {}
    scores: dict[str, int] = {}
    balance_text = ""
    cost_text = ""

    def scoreboard_rows() -> list[tuple[str, str, str]]:
        if not roles:
            return []
        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        rank_map = {name: index + 1 for index, (name, _) in enumerate(ordered)}
        return [
            (name, role, f"{scores.get(name, 0)} очк. | #{rank_map.get(name, len(roles))}")
            for name, role in roles.items()
        ]

    def render() -> None:
        top_right = " | ".join(part for part in [balance_text, cost_text] if part)
        ui.render_dashboard(
            match_title=match_title,
            thesis=thesis or "Тезис пока не загружен.",
            round_label=round_label,
            spotlight_title=spotlight_title,
            spotlight_lines=spotlight_lines,
            feed_lines=feed_lines,
            scoreboard_rows=scoreboard_rows(),
            footer="Управление: шаг вперед по клавише. Самое важное событие всегда в центре экрана.",
            top_right=top_right,
        )

    for event in events:
        kind = event["event"]
        payload = event["payload"]

        if kind == "match_started":
            thesis = payload["thesis"]
            initial_thesis = payload["thesis"]
            balance_text = _balance_text(payload.get("balance"))
            round_label = "Пролог"
            spotlight_title = "НА СТОЛ ВЫНЕСЕН ТЕЗИС"
            spotlight_lines = [
                thesis,
                "Пять философов готовятся проверить его на прочность.",
                f"Раундов впереди: {payload['rounds']}",
                f"Модель: {payload.get('model', 'unknown')}",
            ]
            ui.splash(match_title, "Открытие матча", thesis, top_right=balance_text)
            ui.pause()
            continue

        if kind == "backend_healthcheck":
            if payload.get("warning"):
                feed_lines.append("[связь] ИИ отвечает нестабильно, но матч продолжен.")
            elif payload.get("error"):
                feed_lines.append("[связь] Подключение к ИИ дало сбой.")
            else:
                feed_lines.append("[связь] Подключение к ИИ готово.")
            continue

        if kind == "seating":
            spotlight_title = "ЗА СТОЛОМ ПЯТЬ ФИЛОСОФОВ"
            spotlight_lines = []
            for player in payload["players"]:
                roles[player["name"]] = player["role"]
                scores.setdefault(player["name"], 0)
                spotlight_lines.append(f"{player['name']} — {player['role']}")
            feed_lines.append("[стол] философы заняли места")
        elif kind == "round_started":
            round_label = f"Раунд {payload['round']}"
            thesis = payload["claim"]
            spotlight_title = f"РАУНД {payload['round']}: ВОПРОС НА ОБСУЖДЕНИИ"
            spotlight_lines = [payload["claim"]]
            feed_lines.append(f"[раунд {payload['round']}] началось обсуждение тезиса")
        elif kind == "position":
            spotlight_title = "СТАРТОВЫЕ ПОЗИЦИИ"
            spotlight_lines = [
                f"{payload['agent']['name']} выбирает позицию: {_human_stance(payload['stance'])}",
                payload["speech"],
            ]
            feed_lines.append(
                f"[позиция] {payload['agent']['name']}: {_human_stance(payload['stance'])} — {payload['speech']}"
            )
        elif kind == "question":
            spotlight_title = f"ХОД: {payload['agent']['name'].upper()}"
            spotlight_lines = [f"Вопрос: {payload['question']}"]
            if payload.get("detected_issue"):
                spotlight_lines.append(f"Слабое место: {payload['detected_issue']}")
            feed_lines.append(f"[вопрос] {payload['agent']['name']}: {payload['question']}")
        elif kind == "answer":
            spotlight_title = "ОТВЕТ ЗАЩИТНИКА"
            spotlight_lines = [payload["answer"]]
            if payload.get("refined_claim"):
                spotlight_lines.append(f"Новая версия тезиса: {payload['refined_claim']}")
            feed_lines.append(f"[ответ] {payload['agent']['name']}: {payload['answer']}")
        elif kind == "vote":
            human_status = _human_status(payload["status"])
            spotlight_title = f"ГОЛОС: {payload['agent']['name']}"
            spotlight_lines = [f"Решение: {human_status}", payload["rationale"]]
            if payload.get("new_claim"):
                spotlight_lines.append(f"Новая идея: {payload['new_claim']}")
            if payload.get("contradiction_found"):
                spotlight_lines.append("Игрок считает, что здесь найдено серьёзное противоречие.")
            feed_lines.append(f"[голос] {payload['agent']['name']}: {human_status}")
        elif kind == "round_event":
            spotlight_title = "СОБЫТИЕ РАУНДА"
            spotlight_lines = [payload["text"]]
            feed_lines.append(f"[событие] {payload['text']}")
        elif kind == "arbiter_message":
            spotlight_title = payload["title"].upper()
            spotlight_lines = [payload["text"]]
            feed_lines.append(f"[арбитр] {payload['title']}")
        elif kind == "round_finished":
            verdict = payload["verdict"]
            scores = dict(payload.get("scores_after_round", scores))
            human_status = verdict.get("human_status") or _human_status(verdict["status"])
            spotlight_title = "ИТОГ РАУНДА"
            spotlight_lines = [
                f"Победитель раунда: {verdict.get('winner') or 'не определен'}",
                f"Что случилось с тезисом: {human_status}",
            ]
            if verdict.get("refined_claim"):
                thesis = verdict["refined_claim"]
                spotlight_lines.append(f"Новый текущий тезис: {verdict['refined_claim']}")
            if verdict.get("new_claim"):
                spotlight_lines.append(f"Родившаяся идея: {verdict['new_claim']}")
            feed_lines.append(
                f"[итог] победитель раунда {verdict.get('winner') or 'неизвестен'}, итог: {human_status}"
            )
        elif kind == "match_finished":
            scores = dict(payload.get("scores", scores))
            balance_text = _balance_text(payload.get("balance"))
            if payload.get("estimated_cost_usd") is not None:
                cost_text = f"Расход: ${payload['estimated_cost_usd']:.4f}"
            round_label = "Финал"
            spotlight_title = "МАТЧ ЗАВЕРШЕН"
            initial_value = payload.get("initial_claim", initial_thesis or thesis)
            spotlight_lines = [
                f"Было: {initial_value}",
                f"Стало: {payload['final_claim']}",
                f"Что изменилось: {payload.get('change_summary', 'Итог спора зафиксирован.')}",
                f"Победитель партии: {payload.get('champion', 'не определен')}",
                f"Вызовы LLM: {payload['calls']}",
            ]
            if payload.get("estimated_cost_usd") is not None:
                spotlight_lines.append(f"Оценка стоимости: ${payload['estimated_cost_usd']:.6f}")
            if payload.get("child_summary"):
                spotlight_lines.append("")
                spotlight_lines.append(f"Для ребенка: {payload['child_summary']}")
            feed_lines.append(f"[финал] чемпион партии: {payload.get('champion', 'не определен')}")

        render()
        ui.pause()


def _human_status(status: str) -> str:
    mapping = {
        "refine": "тезис уточнили",
        "refute": "тезис сломался",
        "provisionally_accept": "тезис пока держится",
        "spawn_new_claim": "родилась новая идея",
    }
    return mapping.get(status, status)


def _human_stance(stance: str) -> str:
    mapping = {
        "support": "поддерживает",
        "challenge": "атакует",
        "qualify": "уточняет",
    }
    return mapping.get(stance, stance)


def _balance_text(balance: dict | None) -> str:
    if not isinstance(balance, dict):
        return ""
    value = balance.get("available_usd")
    if isinstance(value, (int, float)):
        return f"Баланс: ${float(value):.2f}"
    if balance.get("source") == "manual_required":
        return "Баланс: задай OPENROUTER_BALANCE_USD или balance.txt"
    return "Баланс: недоступен"


if __name__ == "__main__":
    main()
