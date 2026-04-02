#!/usr/bin/env python3
from play_match import _configure_utf8_stdio, _ensure_api_key_from_keyfile, _ensure_balance_from_file
from spectator_mvp.config import load_config
from spectator_mvp.game import SocraticMatch


def main() -> None:
    _configure_utf8_stdio()
    _ensure_api_key_from_keyfile()
    _ensure_balance_from_file()
    config = load_config()
    match = SocraticMatch(config, live_ui=False)
    match.run()
    print(f"Лог партии сохранен: {config.log_path}")


if __name__ == "__main__":
    main()
