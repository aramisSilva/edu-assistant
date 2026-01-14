def build_daily_plan(ranking):
    """
    ranking: list[(topic, count)]
    """
    top = [t for t, _ in ranking[:3] if t != "Sem tópico"]
    if not top:
        return "Plano do dia (15 min): revise 1 tópico da disciplina e faça 1 exercício básico."
    return (
        "Plano do dia (15–20 min):\n"
        f"- 7 min: revisar **{top[0]}**\n"
        f"- 7 min: praticar 1 exercício de **{top[0]}**\n"
        f"- 5 min: revisar rapidamente **{top[1] if len(top)>1 else top[0]}**\n"
    )
