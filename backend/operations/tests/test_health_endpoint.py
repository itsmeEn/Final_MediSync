from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_ok_or_degraded_returns_json(self):
        resp = self.client.get("/health/")
        self.assertIn(resp.status_code, (200, 503))
        payload = resp.json()
        self.assertIn("status", payload)
        self.assertIn("checks", payload)
        self.assertIn("database", payload["checks"])
        self.assertIn("cache", payload["checks"])

    def test_healthz_alias(self):
        resp = self.client.get("/healthz/")
        self.assertIn(resp.status_code, (200, 503))
