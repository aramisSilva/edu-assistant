from __future__ import annotations

import os

os.environ.setdefault("EDU_ASSISTANT_FRONTEND_DEV_URL", "http://localhost:5173")

from src.api.app import app  # noqa: E402
