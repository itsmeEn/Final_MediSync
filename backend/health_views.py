import logging
import time
import uuid

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
    checks = {
        "database": _check_db(),
        "cache": _check_cache(),
    }
    ok = all(v.get("ok") for v in checks.values())
    status = "ok" if ok else "degraded"
    duration_ms = int((time.perf_counter() - overall_start) * 1000)

    payload = {
        "status": status,
        "checks": checks,
        "response_time_ms": duration_ms,
        "request_id": getattr(request, "request_id", None),
    }

    if ok:
        return JsonResponse(payload, status=200)

    logger.warning("health_degraded %s", payload)
    return JsonResponse(payload, status=503)

