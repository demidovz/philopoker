from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .theses import THESIS_CATALOG, thesis_by_id, thesis_choices_text


load_dotenv()


DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


DEFAULT_THESES = [item["text"] for item in THESIS_CATALOG]


PRICE_HINTS = {
    DEFAULT_MODEL: {"input_per_1m": 0.00, "output_per_1m": 0.00},
}


MODEL_CATALOG = [
    {
        "id": DEFAULT_MODEL,
        "label": "NVIDIA Nemotron 3 Super",
        "note": "OpenRouter free route",
    },
]


@dataclass
class AppConfig:
    thesis: str
    rounds: int
    mode: str
    model: str
    pause_mode: str
    temperature: float
    api_key: str | None
    log_path: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Наблюдательский MVP сократического поединка."
    )
    parser.add_argument("--thesis", help="Тезис для проверки.")
    parser.add_argument(
        "--thesis-id",
        help="Идентификатор готового тезиса. Используй --list-theses для списка.",
    )
    parser.add_argument(
        "--list-theses",
        action="store_true",
        help="Показать каталог готовых тезисов и выйти.",
    )
    parser.add_argument("--rounds", type=int, default=2, help="Число раундов.")
    parser.add_argument(
        "--mode",
        choices=["openrouter", "openai", "mock", "auto"],
        default="auto",
        help="Источник ответов: OpenRouter, mock или авто-выбор.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("SOCRATIC_MODEL", DEFAULT_MODEL),
        help="Модель OpenRouter для агентов.",
    )
    parser.add_argument(
        "--pause",
        choices=["key", "enter", "off"],
        default="key",
        help="Пауза между ходами.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("SOCRATIC_TEMPERATURE", "0.6")),
        help="Температура для OpenRouter.",
    )
    parser.add_argument(
        "--log-file",
        help="Путь к jsonl-логу матча.",
    )
    return parser


def load_config() -> AppConfig:
    parser = build_parser()
    args = parser.parse_args()
    if args.list_theses:
        print("Доступные тезисы:")
        print(thesis_choices_text())
        raise SystemExit(0)

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    thesis_from_id = thesis_by_id(args.thesis_id) if args.thesis_id else None
    if args.thesis_id and thesis_from_id is None:
        parser.error(
            f"Неизвестный thesis-id '{args.thesis_id}'. Используй --list-theses."
        )

    thesis = (
        args.thesis
        or thesis_from_id
        or os.getenv("SOCRATIC_THESIS")
        or DEFAULT_THESES[0]
    )
    mode = args.mode
    if mode == "openai":
        mode = "openrouter"
    if mode == "auto":
        mode = "openrouter" if api_key else "mock"
    log_file = args.log_file or _default_log_path()
    return AppConfig(
        thesis=thesis,
        rounds=max(1, args.rounds),
        mode=mode,
        model=args.model,
        pause_mode=args.pause,
        temperature=args.temperature,
        api_key=api_key,
        log_path=Path(log_file).resolve(),
    )


def _default_log_path() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(Path("logs") / f"socratic_match_{stamp}.jsonl")
