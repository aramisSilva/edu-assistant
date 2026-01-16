from datetime import datetime

def format_date_br(iso_date: str) -> str:
    """
    Recebe 'YYYY-MM-DD' (ou 'YYYY-MM-DDTHH:MM:SS...') e retorna 'DD/MM/AAAA'.
    Se não conseguir parsear, retorna o valor original.
    """
    if not iso_date:
        return iso_date

    try:
        if "T" in iso_date:
            dt = datetime.fromisoformat(iso_date.replace("Z", ""))
            return dt.strftime("%d/%m/%Y")
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso_date
