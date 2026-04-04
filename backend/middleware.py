import logging
import time
import uuid


logger = logging.getLogger("medisync.performance")


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        response["X-Request-ID"] = request_id
        response["X-Response-Time-ms"] = str(duration_ms)

        path = getattr(request, "path", "") or ""
        method = getattr(request, "method", "") or ""
        if duration_ms > 2000:
            logger.warning("slow_request method=%s path=%s status=%s ms=%s request_id=%s", method, path, getattr(response, "status_code", None), duration_ms, request_id)
        return response

