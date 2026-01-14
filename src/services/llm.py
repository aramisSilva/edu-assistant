from openai import OpenAI
from src.core.config import OPENAI_API_KEY
from src.core.prompts import SYSTEM_PROMPT

client = OpenAI(api_key=OPENAI_API_KEY)

def chat_completion(messages, model: str = "gpt-4.1-mini", temperature: float = 0.6) -> str:
    r = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return r.choices[0].message.content

def generate_pedagogical_answer(discipline_label: str, user_text: str, recent_msgs, extra_context: str | None = None):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.append({"role": "system", "content": f"Disciplina atual: {discipline_label}. Seja consistente com este contexto."})

    if extra_context:
        msgs.append({"role": "system", "content": extra_context})

    for role, content in recent_msgs:
        msgs.append({"role": role, "content": content})

    msgs.append({"role": "user", "content": user_text})
    return chat_completion(msgs, temperature=0.6)

def generate_short_title(user_text: str, model: str = "gpt-4.1-mini") -> str:
    msgs = [
        {"role": "system", "content": "Crie um título curto (até 6 palavras), claro e específico para o assunto. Responda apenas com o título."},
        {"role": "user", "content": user_text},
    ]
    title = chat_completion(msgs, model=model, temperature=0.2).strip()
    return title[:60] if title else "Novo chat"
