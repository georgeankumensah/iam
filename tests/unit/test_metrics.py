from unittest.mock import patch

from django.test import TestCase
from prometheus_client import REGISTRY


class MetricsRegistryTests(TestCase):
    def test_metrics_endpoint_returns_prometheus_text(self):
        from core.metrics import metrics_payload

        payload = metrics_payload()
        self.assertTrue(payload.startswith(b"# HELP"))
        self.assertIn(b"iam_http_requests_total", payload)
        self.assertIn(b"iam_http_request_duration_seconds", payload)
        self.assertIn(b"iam_zitadel_token_size_bytes", payload)
        self.assertIn(b"iam_celery_task_duration_seconds", payload)
        self.assertIn(b"iam_db_connections_active", payload)
        self.assertIn(b"iam_pam_sessions_active", payload)

    def test_request_count_increments(self):
        from core.metrics import request_count

        before = REGISTRY.get_sample_value("iam_http_requests_total", {"method": "GET", "endpoint": "test", "status": "200"}) or 0
        request_count.labels(method="GET", endpoint="test", status="200").inc()
        after = REGISTRY.get_sample_value("iam_http_requests_total", {"method": "GET", "endpoint": "test", "status": "200"})
        self.assertEqual(after, before + 1)

    def test_zitadel_token_size_gauge(self):
        from core.metrics import zitadel_token_size_bytes

        zitadel_token_size_bytes.labels(token_type="access").set(512)
        value = REGISTRY.get_sample_value("iam_zitadel_token_size_bytes", {"token_type": "access"})
        self.assertEqual(value, 512)

    def test_db_connection_gauge(self):
        from core.metrics import db_connection_count

        db_connection_count.set(1)
        value = REGISTRY.get_sample_value("iam_db_connections_active")
        self.assertEqual(value, 1)


class MetricsViewTests(TestCase):
    def test_metrics_view_returns_200(self):
        from django.http import HttpRequest

        from core.health_views import metrics_view

        request = HttpRequest()
        request.method = "GET"
        resp = metrics_view(request)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain; version=0.0.4")
        self.assertIn(b"iam_http_requests_total", resp.content)


class MetricsCollectTests(TestCase):
    def test_collect_db_connection_metrics(self):
        from core.tasks import collect_db_connection_metrics

        result = collect_db_connection_metrics()
        self.assertTrue(result["db_connected"])

    @patch("pam.models.PamSession.objects.filter")
    def test_collect_pam_session_metrics(self, mock_filter):
        mock_filter.return_value.count.return_value = 5
        from core.tasks import collect_pam_session_metrics

        result = collect_pam_session_metrics()
        self.assertEqual(result["active_pam_sessions"], 5)


class OTELSetupTests(TestCase):
    def test_setup_otel_disabled_by_default(self):
        from core.otel import setup_otel

        with self.settings(OTEL_ENABLED=False):
            result = setup_otel()
        self.assertFalse(result)

    def test_setup_otel_skipped_when_packages_missing(self):
        from core.otel import setup_otel

        with self.settings(OTEL_ENABLED=True):
            result = setup_otel()
        self.assertFalse(result)
