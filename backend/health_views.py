import logging
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


logger = logging.getLogger("medisync.health")


def _check_db():
    start = time.perf_counter()
    ok = False
    error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        ok = True
    except Exception as e:
        error = str(e)
    ms = int((time.perf_counter() - start) * 1000)
    return {"ok": ok, "ms": ms, "error": error}

def _db_identity():
    try:
        cfg = (settings.DATABASES or {}).get("default") or {}
        identity = {
            "vendor": getattr(connection, "vendor", None),
            "name": cfg.get("NAME"),
            "host": cfg.get("HOST"),
            "port": cfg.get("PORT"),
        }
        if getattr(connection, "vendor", None) == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database();")
                identity["current_database"] = cursor.fetchone()[0]
        return identity
    except Exception as e:
        return {"error": str(e)}

def _safe_count(table_name: str):
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            return int(cursor.fetchone()[0])
    except Exception:
        return None


def _check_cache():
    start = time.perf_counter()
    ok = False
    error = None
    try:
        key = f"health:{uuid.uuid4()}"
        cache.set(key, "1", timeout=10)
        ok = cache.get(key) == "1"
    except Exception as e:
        error = str(e)
    ms = int((time.perf_counter() - start) * 1000)
    return {"ok": ok, "ms": ms, "error": error}


@require_GET
def health(request):
    overall_start = time.perf_counter()
    db_identity = _db_identity()
    checks = {
        "database": _check_db(),
        "cache": _check_cache(),
    }
    ok = all(v.get("ok") for v in checks.values())
    status = "ok" if ok else "degraded"
    duration_ms = int((time.perf_counter() - overall_start) * 1000)

    payload = {
        "status": status,
        "db": {
            **(db_identity if isinstance(db_identity, dict) else {}),
            "counts": {
                "admin_users": _safe_count("admin_users"),
                "users_user": _safe_count("users_user"),
            },
        },
        "checks": checks,
        "response_time_ms": duration_ms,
        "request_id": getattr(request, "request_id", None),
    }

    if ok:
        return JsonResponse(payload, status=200)

    logger.warning("health_degraded %s", payload)
    return JsonResponse(payload, status=503)
