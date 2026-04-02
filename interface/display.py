def format_player_status(player):
    position_icon = "✅" if player.current_position == "agree" else "❌" if player.current_position == "disagree" else "❓"
    player_type_icon = "🤖" if player.player_type == "ai" else "👤"

    return f"{player_type_icon} {player.name}: {player.chips} 🪙 {position_icon}"

def format_card_display(card, round_num):
    category_icons = {
        'ethics': '⚖️',
        'metaphysics': '🌌',
        'epistemology': '🧠',
        'logic': '🔬',
        'aesthetics': '🎨'
    }

    icon = category_icons.get(card.category, '❓')

    return f"""
┌─────────────────────────────────────────────────────┐
│                   РАУНД {round_num}                      │
├─────────────────────────────────────────────────────┤
│ {icon} Категория: {card.category.upper():<38} │
│                                                     │
│ 💭 Утверждение:                                     │
│    "{card.statement:<46}" │
└─────────────────────────────────────────────────────┘
"""

def format_betting_info(total_pot, current_bets):
    lines = [
        "💰 ИНФОРМАЦИЯ О СТАВКАХ:",
        f"   Общий банк: {total_pot} фишек"
    ]

    for player_name, bet in current_bets.items():
        lines.append(f"   {player_name}: {bet} фишек")

    return "\n".join(lines)

def format_question_phase(questions):
    if not questions:
        return "❓ Критических вопросов не поступило"

    lines = ["❓ КРИТИЧЕСКИЕ ВОПРОСЫ:"]
    for i, (questioner, question) in enumerate(questions, 1):
        lines.append(f"   {i}. {questioner}: {question}")

    return "\n".join(lines)

def format_voting_results(votes):
    truth_votes = sum(1 for vote in votes.values() if vote == 'truth')
    lie_votes = len(votes) - truth_votes

    result = "ПРАВДА" if truth_votes > lie_votes else "ЛОЖЬ"

    lines = [
        "🗳️  РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ:",
        f"   Правда: {truth_votes} голосов",
        f"   Ложь: {lie_votes} голосов",
        f"   Решение: {result}"
    ]

    return "\n".join(lines)