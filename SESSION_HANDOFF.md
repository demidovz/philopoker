# Session Handoff

## Текущее состояние

Проект работает как наблюдательский MVP:

- запуск одной командой через `game.bat`;
- выбор тезиса и модели;
- симуляция матча;
- реплей партии;
- логирование в `jsonl`;
- анализ логов через `analyze_logs.py`.

## Как запускать

```powershell
cd C:\Users\user\workspace\maevtica\philosophical_poker
.\game.bat
```

```bash
cd /home/c/workspace/projects/maevtica/philosophical_poker
./game.sh
# при первом запуске скрипт создаст .venv и установит зависимости
```

- Под WSL выбор тезиса и модели работает стрелками `↑` `↓` и `Enter`.
- Если OpenRouter недоступен, запуск через обычный `./game.sh` не переходит в `mock` автоматически: показывается экран с действиями `Повторить подключение` / `Отмена`.
- Для гарантированного оффлайн-запуска нужно явно указывать `--mode mock`.

## Что важно помнить

- Основной API ключ хранится локально в `../openrouter.key` и не должен попадать в git.
- Баланс для интерфейса берётся из `balance.txt` или `OPENROUTER_BALANCE_USD`.
- OpenRouter используется как основной backend для матчей.

## Лучшие текущие модели

- Текущая дефолтная: `nvidia/nemotron-3-super-120b-a12b:free`

## Наблюдения по качеству партий

- У free-маршрута через OpenRouter качество и доступность зависят от текущего роутинга провайдера.
- `nano` часто не двигает тезис достаточно сильно.
- Игра всё ещё слишком часто заканчивается мягким уточнением.

## Следующие приоритеты

### P1. Сильнее мотивировать изменение тезиса

- ввести отложенные очки за вопрос, который реально вызвал изменение тезиса;
- связать вопрос с `refined_claim` или `new_claim` причинно, а не только по порядку;
- штрафовать повторяющиеся мягкие уточнения.

### P2. Добавить скрытую фазу планирования хода

Каждый игрок перед ходом должен формировать скрытый structured plan:

- цель атаки;
- тип атаки;
- желаемый эффект;
- альтернатива, если защита признает удар.

### P3. Улучшить финальный тезис

- убрать обрезание длинных финальных формулировок;
- сильнее сжимать результат в одну ясную мысль;
- отдельно хранить полный и короткий итог.

### P4. Улучшить разнообразие ролей

- запрет повторять тот же вопрос в том же раунде;
- явные role-specific utility;
- усилить Синтезатора как создателя нового тезиса.

## Быстрые команды

```powershell
python run_match.py --mode openrouter --rounds 2 --thesis-id relative_truth
python replay_match.py logs\\<имя_лога>.jsonl
python analyze_logs.py logs\\<имя_лога>.jsonl
python -m unittest tests.test_observer_mvp tests.test_replay_pipeline tests.test_analyze_logs tests.test_thesis_catalog -v
```

## Основные файлы для следующей сессии

- [play_match.py](/C:/Users/user/workspace/maevtica/philosophical_poker/play_match.py)
- [spectator_mvp/game.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/game.py)
- [spectator_mvp/llm.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/llm.py)
- [spectator_mvp/replay.py](/C:/Users/user/workspace/maevtica/philosophical_poker/spectator_mvp/replay.py)
- [GAME_DESIGN_NOTES.md](/C:/Users/user/workspace/maevtica/philosophical_poker/GAME_DESIGN_NOTES.md)
