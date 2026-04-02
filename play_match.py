#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from spectator_mvp.config import MODEL_CATALOG, load_config
from spectator_mvp.game import SocraticMatch
from spectator_mvp.replay import replay
from spectator_mvp.theses import THESIS_CATALOG, thesis_by_index
from spectator_mvp.ui import SpectatorUI


def main() -> None:
    _configure_utf8_stdio()
    _ensure_api_key_from_keyfile()
    _ensure_balance_from_file()
    _pick_launch_options_if_needed()
    config = load_config()
    if not _run_match_with_retries(config):
        return
    print()
    print(f"Лог партии сохранен: {config.log_path}")
    print("Симуляция завершена. Начинается просмотр партии.")
    ui = SpectatorUI(config.pause_mode)
    replay(_match_events(config.log_path), ui, config.log_path)


def _configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            if stream_name == "stdin":
                reconfigure(encoding="utf-8")
            else:
                reconfigure(encoding="utf-8", errors="replace")


def _ensure_api_key_from_keyfile() -> None:
    if os.getenv("OPENROUTER_API_KEY"):
        return
    root = Path(__file__).resolve().parent
    candidate_paths = [
        root.parent / "openrouter.key",
        root / "openrouter.key",
        root / "key.txt",
    ]
    for key_path in candidate_paths:
        if not key_path.exists():
            continue
        key = key_path.read_text(encoding="utf-8").strip()
        if key:
            os.environ["OPENROUTER_API_KEY"] = key
            return


def _ensure_balance_from_file() -> None:
    if os.getenv("OPENROUTER_BALANCE_USD") or os.getenv("OPENAI_BALANCE_USD"):
        return
    balance_path = Path(__file__).resolve().parent / "balance.txt"
    if not balance_path.exists():
        return
    balance = balance_path.read_text(encoding="utf-8").strip()
    if balance:
        os.environ["OPENROUTER_BALANCE_USD"] = balance


def _top_right_money() -> str:
    balance = os.getenv("OPENROUTER_BALANCE_USD", "").strip() or os.getenv("OPENAI_BALANCE_USD", "").strip()
    if balance:
        return f"Баланс: ${balance}"
    return "Баланс: через balance.txt"

def _run_match_with_retries(config) -> bool:
    while True:
        match = SocraticMatch(config, live_ui=False)
        _install_progress(match)
        print(_simulation_header(config))
        health = match.backend.healthcheck()
        if not _healthcheck_ready_to_start(health):
            diagnostics = _health_diagnostic_lines(health)
            print()
            if not _can_offer_openrouter_retry(config, health):
                for line in diagnostics:
                    print(line)
                raise RuntimeError(
                    f"Backend {health.get('backend')} недоступен: {health.get('error', 'unknown error')}"
                )
            action = _prompt_openrouter_recovery(
                str(health.get("error", "unknown error")),
                diagnostics,
            )
            if action == "retry":
                continue
            print("Запуск отменен.")
            return False
        match.run(health=health)
        return True


def _healthcheck_ready_to_start(health: dict[str, Any]) -> bool:
    if not health.get("ok"):
        return False
    warning = str(health.get("warning", "")).lower()
    if "server_error" in warning:
        return False
    return True


def _can_offer_openrouter_retry(config, health: dict[str, Any]) -> bool:
    if config.mode != "openrouter":
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    backend = str(health.get("backend", ""))
    return backend in {"openrouter", "unknown"}


def _health_diagnostic_lines(health: dict[str, Any]) -> list[str]:
    diagnostics = health.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []
    return [
        _compact_error_text(str(item), limit=120)
        for item in diagnostics
        if str(item).strip()
    ]


def _prompt_openrouter_recovery(error_text: str, diagnostics: list[str]) -> str:
    if _supports_arrow_picker():
        return _pick_openrouter_recovery_with_arrows(error_text, diagnostics)
    return _pick_openrouter_recovery_with_input(error_text, diagnostics)


def _pick_openrouter_recovery_with_arrows(error_text: str, diagnostics: list[str]) -> str:
    options = ["Повторить подключение", "Отмена"]
    if os.name != "nt":
        selected = _pick_with_posix_arrows(
            [{"label": item} for item in options],
            lambda ui, index: _render_openrouter_recovery(
                ui,
                index,
                options,
                error_text,
                diagnostics,
                use_arrows=True,
            ),
        )
        return "retry" if selected == 1 else "cancel"

    import msvcrt

    ui = SpectatorUI("off")
    selected = 0
    while True:
        _render_openrouter_recovery(ui, selected, options, error_text, diagnostics, use_arrows=True)
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            return "retry" if selected == 0 else "cancel"
        if key in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            if code == "H":
                selected = (selected - 1) % len(options)
            elif code == "P":
                selected = (selected + 1) % len(options)


def _pick_openrouter_recovery_with_input(error_text: str, diagnostics: list[str]) -> str:
    ui = SpectatorUI("off")
    options = ["Повторить подключение", "Отмена"]
    while True:
        _render_openrouter_recovery(ui, 0, options, error_text, diagnostics, use_arrows=False)
        answer = input("\nДействие [1=повторить, 2=отмена, Enter=1]: ").strip()
        if answer in ("", "1"):
            return "retry"
        if answer == "2":
            return "cancel"


def _render_openrouter_recovery(
    ui: SpectatorUI,
    selected: int,
    options: list[str],
    error_text: str,
    diagnostics: list[str],
    *,
    use_arrows: bool,
) -> None:
    spotlight_lines = []
    for index, item in enumerate(options):
        marker = ">" if index == selected else " "
        spotlight_lines.append(f"{marker} {index + 1}. {item}")

    feed_lines = [
        "OpenRouter не ответил на проверку перед стартом матча.",
        _compact_error_text(error_text),
    ]
    feed_lines.extend(diagnostics[:6])
    if use_arrows:
        feed_lines.append("Стрелки ↑ ↓ выбирают действие. Enter подтверждает.")
    else:
        feed_lines.append("Введи номер действия и нажми Enter.")

    ui.render_dashboard(
        match_title="СОКРАТИЧЕСКИЙ ПОЕДИНОК",
        thesis="Матч не начнется автоматически, пока OpenRouter недоступен.",
        round_label="Проблема с OpenRouter",
        spotlight_title="ДЕЙСТВИЕ",
        spotlight_lines=spotlight_lines,
        feed_lines=feed_lines,
        scoreboard_rows=[],
        footer="Без ответа от OpenRouter запуск не будет автоматически переключаться в mock-режим.",
        top_right=_top_right_money(),
    )


def _compact_error_text(error_text: str, limit: int = 180) -> str:
    normalized = " ".join(str(error_text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _pick_launch_options_if_needed() -> None:
    has_thesis_arg = any(arg.startswith("--thesis") for arg in sys.argv[1:])
    has_model_arg = any(arg == "--model" or arg.startswith("--model=") for arg in sys.argv[1:])
    if "--list-theses" in sys.argv[1:] or not sys.stdin.isatty():
        return
    if has_thesis_arg and has_model_arg:
        return

    if _supports_arrow_picker():
        thesis_choice = _pick_thesis_with_arrows()
        model_choice = _pick_model_with_arrows()
    else:
        thesis_choice = _pick_thesis_with_input()
        model_choice = _pick_model_with_input()

    if not has_thesis_arg:
        thesis = thesis_by_index(thesis_choice)
        if thesis:
            os.environ["SOCRATIC_THESIS"] = thesis
    if not has_model_arg:
        os.environ["SOCRATIC_MODEL"] = MODEL_CATALOG[model_choice - 1]["id"]


def _pick_thesis_with_arrows() -> int:
    if os.name != "nt":
        return _pick_with_posix_arrows(
            THESIS_CATALOG,
            lambda ui, selected: _render_thesis_picker(ui, selected, use_arrows=True, error_message=""),
        )

    import msvcrt

    ui = SpectatorUI("off")
    selected = 0

    while True:
        _render_thesis_picker(ui, selected, use_arrows=True, error_message="")
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            return selected + 1
        if key in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            if code == "H":
                selected = (selected - 1) % len(THESIS_CATALOG)
            elif code == "P":
                selected = (selected + 1) % len(THESIS_CATALOG)


def _pick_model_with_arrows() -> int:
    if os.name != "nt":
        return _pick_with_posix_arrows(
            MODEL_CATALOG,
            lambda ui, selected: _render_model_picker(ui, selected, use_arrows=True, error_message=""),
        )

    import msvcrt

    ui = SpectatorUI("off")
    selected = 0

    while True:
        _render_model_picker(ui, selected, use_arrows=True, error_message="")
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            return selected + 1
        if key in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            if code == "H":
                selected = (selected - 1) % len(MODEL_CATALOG)
            elif code == "P":
                selected = (selected + 1) % len(MODEL_CATALOG)


def _supports_arrow_picker() -> bool:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        return True
    try:
        import termios  # noqa: F401
        import tty  # noqa: F401
    except ImportError:
        return False
    return True


def _pick_with_posix_arrows(items: list[dict[str, Any]], render) -> int:
    import termios
    import tty

    ui = SpectatorUI("off")
    selected = 0
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        while True:
            render(ui, selected)
            key = _read_posix_key(fd)
            if key == "enter":
                return selected + 1
            if key == "up":
                selected = (selected - 1) % len(items)
            elif key == "down":
                selected = (selected + 1) % len(items)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
        print()


def _read_posix_key(fd: int) -> str:
    import os
    import select

    first = os.read(fd, 1)
    if first in (b"\r", b"\n"):
        return "enter"
    if first == b"\x03":
        raise KeyboardInterrupt
    if first == b"\x1b":
        if not select.select([fd], [], [], 0.05)[0]:
            return "escape"
        second = os.read(fd, 1)
        if second != b"[":
            return "escape"
        if not select.select([fd], [], [], 0.05)[0]:
            return "escape"
        third = os.read(fd, 1)
        if third == b"A":
            return "up"
        if third == b"B":
            return "down"
        return "escape"
    if first in (b"k", b"K"):
        return "up"
    if first in (b"j", b"J"):
        return "down"
    return "other"


def _pick_thesis_with_input() -> int:
    ui = SpectatorUI("off")
    error_message = ""
    while True:
        _render_thesis_picker(ui, 0, use_arrows=False, error_message=error_message)
        answer = input(f"\nТема [1-{len(THESIS_CATALOG)}, Enter=1]: ").strip()
        choice = 1 if not answer else int(answer) if answer.isdigit() else -1
        if thesis_by_index(choice):
            return choice
        error_message = "Нужно выбрать номер темы из списка."


def _pick_model_with_input() -> int:
    ui = SpectatorUI("off")
    error_message = ""
    while True:
        _render_model_picker(ui, 0, use_arrows=False, error_message=error_message)
        answer = input(f"\nМодель [1-{len(MODEL_CATALOG)}, Enter=1]: ").strip()
        choice = 1 if not answer else int(answer) if answer.isdigit() else -1
        if 1 <= choice <= len(MODEL_CATALOG):
            return choice
        error_message = "Нужно выбрать номер модели из списка."


def _render_thesis_picker(ui: SpectatorUI, selected: int, *, use_arrows: bool, error_message: str) -> None:
    spotlight_lines = []
    for index, item in enumerate(THESIS_CATALOG):
        marker = ">" if index == selected else " "
        spotlight_lines.append(f"{marker} {index + 1:>2}. {item['text']} [{item['category']}]")

    selected_item = THESIS_CATALOG[selected]
    feed_lines = [
        f"Выбрана тема: {selected_item['text']}",
        "Сначала выбираем вопрос для спора пяти философов.",
    ]
    if use_arrows:
        feed_lines.append("Стрелки ↑ ↓ меняют тему. Enter подтверждает выбор темы.")
    else:
        feed_lines.append("Введи номер темы и нажми Enter.")
    if error_message:
        feed_lines.append(error_message)

    ui.render_dashboard(
        match_title="СОКРАТИЧЕСКИЙ ПОЕДИНОК",
        thesis="Шаг 1 из 2: выбери тезис, который будет вынесен на стол.",
        round_label="Выбор темы",
        spotlight_title="ТЕМЫ ДЛЯ СПОРА",
        spotlight_lines=spotlight_lines,
        feed_lines=feed_lines,
        scoreboard_rows=[],
        footer="После подтверждения откроется экран выбора модели.",
        top_right=_top_right_money(),
    )


def _model_warning(model_id: str) -> str:
    if model_id == "nvidia/nemotron-3-super-120b-a12b:free":
        return "Подключение идет через OpenRouter. Это бесплатный маршрут для текущей версии проекта."
    return ""


def _render_model_picker(ui: SpectatorUI, selected: int, *, use_arrows: bool, error_message: str) -> None:
    spotlight_lines = []
    for index, item in enumerate(MODEL_CATALOG):
        marker = ">" if index == selected else " "
        spotlight_lines.append(f"{marker} {index + 1}. {item['label']} — {item['note']} ({item['id']})")

    selected_item = MODEL_CATALOG[selected]
    feed_lines = [
        f"Выбрана модель: {selected_item['label']}",
        "Теперь выбираем, какой моделью ИИ будет сыграна партия.",
    ]
    if use_arrows:
        feed_lines.append("Стрелки ↑ ↓ меняют модель. Enter запускает симуляцию.")
    else:
        feed_lines.append("Введи номер модели и нажми Enter.")
    warning = _model_warning(selected_item["id"])
    if warning:
        feed_lines.append(warning)
    if error_message:
        feed_lines.append(error_message)

    ui.render_dashboard(
        match_title="СОКРАТИЧЕСКИЙ ПОЕДИНОК",
        thesis="Шаг 2 из 2: выбери модель, которая будет отвечать за игроков.",
        round_label="Выбор модели",
        spotlight_title="МОДЕЛИ OPENROUTER",
        spotlight_lines=spotlight_lines,
        feed_lines=feed_lines,
        scoreboard_rows=[],
        top_right=_top_right_money(),
        footer="После подтверждения начнется симуляция партии.",
    )


def _install_progress(match: SocraticMatch) -> None:
    total_steps = 1 + match.config.rounds * 18
    state = {"done": 0}
    original_healthcheck = match.backend.healthcheck
    original_json_completion = match.backend.json_completion

    def wrapped_healthcheck() -> dict[str, Any]:
        _print_progress(state["done"], total_steps, "Подключение к ИИ")
        result = original_healthcheck()
        state["done"] += 1
        _print_progress(state["done"], total_steps, "Подключение к ИИ готово")
        warning = str(result.get("warning", "")).strip()
        if warning:
            print()
            print(f"Предупреждение: {warning}")
        return result

    def wrapped_json_completion(agent, instruction, payload, max_tokens=160):
        stage = _human_stage_name(str(payload.get("task", "step")))
        round_no = payload.get("round")
        prefix = f"Раунд {round_no} | " if round_no else ""
        _print_progress(state["done"], total_steps, f"{prefix}{stage} | {agent.name}")
        result = original_json_completion(agent, instruction, payload, max_tokens=max_tokens)
        state["done"] += 1
        _print_progress(state["done"], total_steps, f"{prefix}{stage} | {agent.name}")
        return result

    match.backend.healthcheck = wrapped_healthcheck
    match.backend.json_completion = wrapped_json_completion


def _human_stage_name(stage: str) -> str:
    mapping = {
        "position": "позиция",
        "question": "вопрос",
        "answer": "ответ",
        "vote": "решение",
    }
    return mapping.get(stage, stage)


def _print_progress(done: int, total: int, label: str) -> None:
    percent = int((done / total) * 100) if total else 100
    bar_width = 28
    filled = int(bar_width * percent / 100)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(f"\rСимуляция [{bar}] {percent:>3}%  {done}/{total}  {label:<40}", end="", flush=True)


def _simulation_header(config) -> str:
    thesis = config.thesis
    if len(thesis) > 90:
        thesis = thesis[:87] + "..."
    return (
        "Подготовка партии\n"
        f"Режим: {config.mode}\n"
        f"Модель: {config.model}\n"
        f"Раунды: {config.rounds}\n"
        f"Тема: {thesis}\n"
    )


def _match_events(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    main()
