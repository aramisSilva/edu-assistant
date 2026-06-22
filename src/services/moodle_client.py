from __future__ import annotations

import httpx


class MoodleClientError(RuntimeError):
    pass


class MoodleClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0, transport=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(timeout=timeout, transport=transport)

    def close(self):
        self.client.close()

    def _call(self, function: str, **params):
        if not self.token:
            raise MoodleClientError("Configure MOODLE_TOKEN no arquivo .env.")
        payload = {
            "wstoken": self.token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
            **params,
        }
        try:
            response = self.client.post(f"{self.base_url}/webservice/rest/server.php", data=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise MoodleClientError("O Moodle demorou demais para responder.") from exc
        except httpx.RequestError as exc:
            raise MoodleClientError("Nao foi possivel conectar ao Moodle local.") from exc
        except (httpx.HTTPStatusError, ValueError) as exc:
            raise MoodleClientError("O Moodle retornou uma resposta invalida.") from exc
        if isinstance(data, dict) and data.get("exception"):
            message = data.get("message") or data.get("errorcode") or "Erro retornado pelo Moodle."
            raise MoodleClientError(f"Moodle recusou a sincronizacao: {message}")
        return data

    def get_site_info(self) -> dict:
        return self._call("core_webservice_get_site_info")

    def get_user_courses(self, user_id: int) -> list[dict]:
        return self._call("core_enrol_get_users_courses", userid=user_id)

    def get_action_events(self, page_size: int = 50) -> list[dict]:
        events = []
        after_event_id = 0
        while True:
            page = self._call(
                "core_calendar_get_action_events_by_timesort",
                timesortfrom=0,
                aftereventid=after_event_id,
                limitnum=page_size,
            )
            current = page.get("events", [])
            events.extend(current)
            if len(current) < page_size:
                return events
            next_id = int(current[-1]["id"])
            if next_id == after_event_id:
                raise MoodleClientError("A paginacao de eventos do Moodle nao avancou.")
            after_event_id = next_id
