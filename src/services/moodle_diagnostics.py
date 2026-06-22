from __future__ import annotations

from src.core import config
from src.infra import repo
from src.services.moodle_client import MoodleClient, MoodleClientError


def _check(label: str, status: str, detail: str) -> dict:
    return {"label": label, "status": status, "detail": detail}


def diagnose_moodle(student_id: int, client: MoodleClient | None = None) -> dict:
    base_url = config.MOODLE_BASE_URL
    token = config.MOODLE_TOKEN
    last_sync = repo.get_moodle_sync_state(student_id)
    checks = [
        _check("URL Moodle", "ok" if base_url else "error", base_url or "MOODLE_BASE_URL não configurada."),
        _check("Token REST", "ok" if token else "error", "Token configurado." if token else "Configure MOODLE_TOKEN no arquivo .env."),
    ]

    result = {
        "status": "error",
        "base_url": base_url,
        "token_configured": bool(token),
        "moodle_available": False,
        "user": None,
        "courses_count": 0,
        "last_sync": last_sync,
        "message": "Configure a integração Moodle antes de sincronizar.",
        "checks": checks,
    }
    if not base_url or not token:
        return result

    owns_client = client is None
    client = client or MoodleClient(base_url, token, timeout=5.0)
    try:
        site_info = client.get_site_info()
        user_id = int(site_info["userid"])
        user = {
            "id": user_id,
            "username": site_info.get("username"),
            "fullname": site_info.get("fullname") or site_info.get("userfullname"),
        }
        courses = client.get_user_courses(user_id)
        courses_count = len(courses)
        checks.extend([
            _check("Conexão Moodle", "ok", "Moodle respondeu ao serviço REST."),
            _check("Usuário do token", "ok", f"Usuário identificado: {user.get('username') or user_id}."),
            _check(
                "Matrículas",
                "ok" if courses_count else "warning",
                f"{courses_count} curso(s) matriculado(s) para este token.",
            ),
        ])
        status = "ok" if courses_count else "warning"
        message = (
            "Integração Moodle pronta para sincronizar."
            if courses_count
            else "Token válido, mas o aluno não está matriculado em cursos. Matricule edu.student e sincronize novamente."
        )
        result.update({
            "status": status,
            "moodle_available": True,
            "user": user,
            "courses_count": courses_count,
            "message": message,
            "checks": checks,
        })
        return result
    except MoodleClientError as exc:
        checks.append(_check("Conexão Moodle", "error", str(exc)))
        result.update({
            "message": f"Não foi possível validar a integração Moodle: {exc}",
            "checks": checks,
        })
        return result
    finally:
        if owns_client:
            client.close()
