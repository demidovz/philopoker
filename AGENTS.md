# Project Notes For Codex

This repository contains a philosophical poker prototype with a spectator MVP UI.

## Main Entry Points

- `play_match.py`: interactive launcher with thesis/model selection and recovery flow
- `run_match.py`: direct match runner
- `replay_match.py`: replay existing `jsonl` logs
- `analyze_logs.py`: summarize a saved match log
- `spectator_mvp/game.py`: main spectator loop and state transitions
- `spectator_mvp/llm.py`: OpenRouter backend and JSON completion logic

## Current LLM Setup

- Default backend: OpenRouter
- Default model: `nvidia/nemotron-3-super-120b-a12b:free`
- Preferred local secret loading:
  - `OPENROUTER_API_KEY` env var
  - or local `../openrouter.key` during development
- Do not commit keys, balances, or logs.

## Useful Commands

```powershell
python run_match.py --mode openrouter --rounds 2 --thesis-id relative_truth
python replay_match.py logs\<log_name>.jsonl
python analyze_logs.py logs\<log_name>.jsonl
python -m unittest tests.test_observer_mvp tests.test_replay_pipeline tests.test_analyze_logs tests.test_thesis_catalog -v
```

## Files Worth Reading First

- `README.md`
- `PROJECT_OVERVIEW.md`
- `SESSION_HANDOFF.md`
- `NEURAL_SETUP.md`
- `GAME_DESIGN_NOTES.md`
- `spectator_mvp/game.py`
- `spectator_mvp/llm.py`

## Near-Term Priorities

- Improve incentives for real thesis shifts instead of soft restatements
- Add a hidden planning phase for each move
- Improve final thesis compression and presentation
- Make role behavior more distinct during a round
