from __future__ import annotations

import os
import shutil
import sys
import textwrap
from typing import Iterable


class SpectatorUI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"

    def __init__(self, pause_mode: str) -> None:
        self.pause_mode = pause_mode
        self._is_tty = sys.stdout.isatty()
        self._ascii_only = (getattr(sys.stdout, "encoding", "") or "").lower() in {
            "cp1251",
            "cp866",
        }

    def clear(self) -> None:
        if not self._is_tty:
            return
        os.system("cls" if os.name == "nt" else "clear")

    def banner(self, title: str, subtitle: str, top_right: str = "") -> None:
        self.clear()
        width = self._width()
        print(self._color(self._rule("=", width), self.CYAN))
        print(self._header_line(title, top_right, width, self.BOLD + self.WHITE, self.BOLD + self.GREEN))
        print(self._center(subtitle, width, self.DIM + self.CYAN))
        print(self._color(self._rule("=", width), self.CYAN))

    def section(self, title: str) -> None:
        print()
        print(self._color(f"[ {title} ]", self.BOLD + self.YELLOW))

    def divider(self, char: str = "-") -> None:
        print(self._color(self._rule(char, self._width()), self.DIM))

    def emit(self, label: str, text: str) -> None:
        label_text = self._color(f"{label:<14}", self.BOLD + self.CYAN)
        wrapped = self._wrap(text, max(24, self._width() - 16))
        if not wrapped:
            print(label_text)
            return
        print(f"{label_text} {wrapped[0]}")
        for line in wrapped[1:]:
            print(f"{'':14} {line}")

    def emit_block(self, label: str, lines: Iterable[str]) -> None:
        print(self._color(f"{label:<14}", self.BOLD + self.CYAN))
        for line in lines:
            for wrapped in self._wrap(line, max(24, self._width() - 4)):
                print(f"  {wrapped}")

    def announce(self, title: str, text: str, marker: str = "!") -> None:
        width = self._width()
        color = self._marker_color(marker)
        print()
        print(self._color(self._rule(marker, width), color))
        print(self._center(title, width, self.BOLD + color))
        for line in self._wrap(text, max(30, width - 2)):
            print(self._color(line, color))
        print(self._color(self._rule(marker, width), color))

    def scoreboard(self, title: str, rows: list[tuple[str, str, str]]) -> None:
        width = self._width()
        print()
        print(self._color(title, self.BOLD + self.MAGENTA))
        print(self._color(self._rule("-", width), self.DIM))
        print(
            self._color(f"{'Игрок':<16}{'Роль':<32}{'Счет/статус':<24}", self.BOLD + self.WHITE)
        )
        print(self._color(self._rule("-", width), self.DIM))
        for name, role, status in rows:
            print(f"{self._color(name, self.BOLD + self.GREEN):<25}{role:<32}{status:<24}")
        print(self._color(self._rule("-", width), self.DIM))

    def splash(self, title: str, subtitle: str, thesis: str, top_right: str = "") -> None:
        self.clear()
        width = self._width()
        print()
        print(self._color(self._rule("=", width), self.MAGENTA))
        print(self._header_line(title, top_right, width, self.BOLD + self.WHITE, self.BOLD + self.GREEN))
        print(self._center(subtitle, width, self.BOLD + self.YELLOW))
        print(self._color(self._rule("=", width), self.MAGENTA))
        print()
        print(self._panel("ТЕЗИС НА ОБСУЖДЕНИИ", [thesis], self.BLUE))

    def render_dashboard(
        self,
        *,
        match_title: str,
        thesis: str,
        round_label: str,
        spotlight_title: str,
        spotlight_lines: list[str],
        feed_lines: list[str],
        scoreboard_rows: list[tuple[str, str, str]],
        footer: str,
        top_right: str = "",
    ) -> None:
        self.clear()
        width = self._width()
        print(self._color(self._rule("=", width), self.CYAN))
        print(self._header_line(match_title, top_right, width, self.BOLD + self.WHITE, self.BOLD + self.GREEN))
        print(self._center(round_label, width, self.BOLD + self.YELLOW))
        print(self._color(self._rule("=", width), self.CYAN))
        print()
        print(self._panel("ТЕКУЩИЙ ТЕЗИС", [thesis], self.BLUE))
        print()
        print(self._panel(spotlight_title, spotlight_lines or ["Ожидание следующего действия..."], self.MAGENTA))
        print()
        print(self._panel("ЛЕНТА СОБЫТИЙ", feed_lines[-10:] or ["Партия только начинается."], self.WHITE))
        print()
        score_lines = [f"{name} | {role} | {status}" for name, role, status in scoreboard_rows]
        print(self._panel("ТАБЛО", score_lines or ["Табло пока пусто."], self.GREEN))
        print()
        print(self._color(footer, self.DIM + self.CYAN))

    def pause(self) -> None:
        if self.pause_mode == "off":
            return
        if self.pause_mode == "enter":
            input("\nНажмите Enter для следующего шага...")
            return

        print(self._color("\nНажмите любую клавишу для следующего шага...", self.DIM), end="", flush=True)
        if os.name == "nt":
            import msvcrt

            msvcrt.getwch()
            print()
            return
        self._read_single_key_posix()
        print()

    def _read_single_key_posix(self) -> None:
        import termios
        import tty

        if not sys.stdin.isatty():
            sys.stdin.read(1)
            return

        fd = sys.stdin.fileno()
        original = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, original)

    def _panel(self, title: str, lines: list[str], color: str) -> str:
        width = self._width()
        inner = max(20, width - 4)
        wrapped_lines: list[str] = []
        for line in lines:
            wrapped = self._wrap(line, inner)
            wrapped_lines.extend(wrapped or [""])
        if self._ascii_only:
            top = f"+{'-' * inner}+"
            sep = f"+{'-' * inner}+"
            bottom = f"+{'-' * inner}+"
            left = "|"
            right = "|"
        else:
            top = f"┌{'─' * inner}┐"
            sep = f"├{'─' * inner}┤"
            bottom = f"└{'─' * inner}┘"
            left = "│"
            right = "│"
        middle_title = self._color(title[:inner].center(inner), self.BOLD + color)
        body = [f"{left}{middle_title}{right}", sep]
        for line in wrapped_lines:
            body.append(f"{left}{line.ljust(inner)}{right}")
        return "\n".join([self._color(top, color), *body, self._color(bottom, color)])

    def _width(self) -> int:
        columns = shutil.get_terminal_size((120, 30)).columns
        return max(72, columns - 2)

    def _rule(self, char: str, width: int) -> str:
        return char * width

    def _center(self, text: str, width: int, style: str) -> str:
        return self._color(text.center(width), style)

    def _header_line(
        self,
        left_text: str,
        right_text: str,
        width: int,
        left_style: str,
        right_style: str,
    ) -> str:
        right = str(right_text).strip()
        if not right:
            return self._center(left_text, width, left_style)
        gap = 4
        left_width = max(20, width - len(right) - gap)
        left_part = left_text.center(left_width)
        padding = max(gap, width - left_width - len(right))
        return self._color(left_part, left_style) + (" " * padding) + self._color(right, right_style)

    def _wrap(self, text: str, width: int) -> list[str]:
        return textwrap.wrap(str(text), width=width, break_long_words=False, break_on_hyphens=False)

    def _color(self, text: str, color: str) -> str:
        if not self._is_tty:
            return text
        return f"{color}{text}{self.RESET}"

    def _marker_color(self, marker: str) -> str:
        if marker == "=":
            return self.CYAN
        if marker == "!":
            return self.YELLOW
        if marker == "*":
            return self.GREEN
        return self.WHITE
