from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Анализатор jsonl-логов сократических матчей.")
    parser.add_argument("path", help="Путь к jsonl-файлу или директории с логами.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    target = Path(args.path).resolve()
    files = _collect_files(target)
    if not files:
        raise SystemExit("Логи не найдены.")

    summary = aggregate(files)
    print_summary(summary, files)


def _collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.jsonl"))
    return []


def load_events(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def aggregate(paths: list[Path]) -> dict[str, Any]:
    event_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    question_counts: Counter[str] = Counter()
    vote_status_by_agent: dict[str, Counter[str]] = defaultdict(Counter)
    questions_by_agent: dict[str, list[str]] = defaultdict(list)
    final_claims: list[str] = []
    total_calls = 0
    total_cost = 0.0

    for path in paths:
        for item in load_events(path):
            event = item["event"]
            payload = item["payload"]
            event_counts[event] += 1

            if event == "question":
                agent_name = payload["agent"]["name"]
                question_counts[agent_name] += 1
                questions_by_agent[agent_name].append(payload["question"])

            if event == "vote":
                agent_name = payload["agent"]["name"]
                vote_status_by_agent[agent_name][payload["status"]] += 1

            if event == "round_finished":
                verdict_counts[payload["verdict"]["status"]] += 1

            if event == "match_finished":
                total_calls += int(payload.get("calls", 0))
                total_cost += float(payload.get("estimated_cost_usd") or 0.0)
                final_claims.append(payload.get("final_claim", ""))

    return {
        "events": event_counts,
        "verdicts": verdict_counts,
        "questions": question_counts,
        "votes": vote_status_by_agent,
        "question_examples": questions_by_agent,
        "final_claims": final_claims,
        "total_calls": total_calls,
        "total_cost": total_cost,
    }


def print_summary(summary: dict[str, Any], files: list[Path]) -> None:
    print("СВОДКА ЛОГОВ")
    print(f"Файлов: {len(files)}")
    print(f"Матчей: {summary['events'].get('match_finished', 0)}")
    print(f"Раундов: {summary['events'].get('round_finished', 0)}")
    print(f"Вызовов LLM: {summary['total_calls']}")
    print(f"Оценка стоимости: ${summary['total_cost']:.6f}")
    print()

    print("ВЕРДИКТЫ")
    for status, count in summary["verdicts"].most_common():
        print(f"- {status}: {count}")
    print()

    print("ВОПРОСЫ ПО РОЛЯМ")
    for agent, count in summary["questions"].most_common():
        print(f"- {agent}: {count}")
    print()

    print("ГОЛОСА ПО РОЛЯМ")
    for agent, counter in sorted(summary["votes"].items()):
        statuses = ", ".join(f"{status}={count}" for status, count in counter.most_common())
        print(f"- {agent}: {statuses}")
    print()

    print("ПРИМЕРЫ ВОПРОСОВ")
    for agent, examples in sorted(summary["question_examples"].items()):
        example = examples[0] if examples else ""
        print(f"- {agent}: {example}")
    print()

    print("ФИНАЛЬНЫЕ ТЕЗИСЫ")
    for claim in summary["final_claims"][-5:]:
        print(f"- {claim}")
