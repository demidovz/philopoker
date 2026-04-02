# Philosophical Poker

Наблюдательский прототип философской игры по мотивам сократического метода.

## Что уже есть

- Полноэкранный консольный интерфейс под Windows.
- Выбор тезиса и модели перед запуском матча.
- Симуляция партии в лог `jsonl`, затем пошаговый реплей.
- Пять ролей:
  - Протагор
  - Скептик
  - Педант
  - Прагматик
  - Синтезатор
- Поддержка `mock` и `openrouter`.
- Финальный экран с блоками:
  - было
  - стало
  - что изменилось
  - для ребенка

## Основная точка входа

- Windows: [game.bat](/C:/Users/user/workspace/maevtica/philosophical_poker/game.bat)
- WSL/Linux: [game.sh](game.sh)
- Python orchestration: [play_match.py](/C:/Users/user/workspace/maevtica/philosophical_poker/play_match.py)

## Ключевые модули

- Движок матча: [game.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/game.py)
- LLM backend: [llm.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/llm.py)
- Реплей: [replay.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/replay.py)
- UI: [ui.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/ui.py)
- Каталог тезисов и моделей: [config.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/config.py), [theses.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/theses.py)

## Текущее практическое состояние

- По умолчанию проект запускается через OpenRouter.
- Рабочая модель по умолчанию: `nvidia/nemotron-3-super-120b-a12b:free`.
- Ключ читается из `../openrouter.key`, если не задан `OPENROUTER_API_KEY`.
- Баланс для UI берётся из `balance.txt` или `OPENROUTER_BALANCE_USD`.
