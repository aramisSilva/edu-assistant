from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date

@dataclass(frozen=True)
class DeadlineStatus:
    code: str
    label: str
    days_left: int | None
    severity: int

def _parse_iso_date(due_iso: str) -> date | None:
    if not due_iso:
        return None
    try:
        return datetime.strptime(due_iso[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def get_deadline_status(due_iso: str) -> DeadlineStatus:
    """
    Classificação visual (MVP):
    - <0  : Atrasada
    - 0   : Vence hoje
    - 1   : Vence amanhã
    - 2-3 : Urgente
    - 4-7 : Próxima
    - >7  : Planejada
    """
    d = _parse_iso_date(due_iso)
    if d is None:
        return DeadlineStatus(code="UNKNOWN", label="Prazo não informado", days_left=None, severity=0)

    days_left = (d - date.today()).days

    if days_left < 0:
        return DeadlineStatus("OVERDUE", "Atrasada", days_left, 5)
    if days_left == 0:
        return DeadlineStatus("TODAY", "Vence hoje", days_left, 5)
    if days_left == 1:
        return DeadlineStatus("TOMORROW", "Vence amanhã", days_left, 4)
    if 2 <= days_left <= 3:
        return DeadlineStatus("URGENT", "Urgente", days_left, 4)
    if 4 <= days_left <= 7:
        return DeadlineStatus("SOON", "Próxima", days_left, 3)
    return DeadlineStatus("PLANNED", "Planejada", days_left, 1)
