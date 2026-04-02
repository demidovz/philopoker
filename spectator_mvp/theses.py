from __future__ import annotations


THESIS_CATALOG: list[dict[str, str]] = [
    {"id": "free_will", "category": "метафизика", "text": "Свобода воли существует."},
    {"id": "objective_beauty", "category": "эстетика", "text": "Красота объективна."},
    {"id": "moral_society", "category": "этика", "text": "Мораль без общества невозможна."},
    {"id": "relative_truth", "category": "эпистемология", "text": "Истина всегда зависит от точки зрения."},
    {"id": "consciousness_science", "category": "сознание", "text": "Наука не может полностью объяснить сознание."},
    {"id": "ai_personhood", "category": "технологии", "text": "Достаточно развитый ИИ должен считаться моральной личностью."},
    {"id": "democracy_truth", "category": "политика", "text": "Демократия лучше автократии в поиске общественной истины."},
    {"id": "language_limits", "category": "язык", "text": "Границы языка определяют границы мышления."},
    {"id": "justice_equality", "category": "политика", "text": "Справедливость требует равенства стартовых возможностей."},
    {"id": "happiness_knowledge", "category": "античность", "text": "Человек не может быть счастлив, не зная себя."},
    {"id": "history_progress", "category": "история", "text": "История в целом движется к моральному прогрессу."},
    {"id": "simulation", "category": "метафизика", "text": "Вероятно, мы живем в симуляции."},
]


def thesis_choices_text() -> str:
    lines = []
    for index, item in enumerate(THESIS_CATALOG, start=1):
        lines.append(f"{index:>2}. {item['id']} — {item['text']} [{item['category']}]")
    return "\n".join(lines)


def thesis_by_id(thesis_id: str) -> str | None:
    for item in THESIS_CATALOG:
        if item["id"] == thesis_id:
            return item["text"]
    return None


def thesis_by_index(index: int) -> str | None:
    if 1 <= index <= len(THESIS_CATALOG):
        return THESIS_CATALOG[index - 1]["text"]
    return None
