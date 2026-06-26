"""Locust load test for IAM 3.0 API.

Run:
    locust -f tests/load/locustfile.py --host https://iam-api.clet.gov.gh

Or headless:
    locust -f tests/load/locustfile.py --host https://iam-api.clet.gov.gh \
      --users 100 --spawn-rate 10 --run-time 5m --headless
"""

from locust import HttpUser, between, task


class IAMHealthUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def health_live(self):
        self.client.get("/health/live")

    @task(5)
    def health_ready(self):
        self.client.get("/health/ready")

    @task(3)
    def health_metrics(self):
        self.client.get("/health/metrics")

    @task(1)
    def well_known_claims(self):
        self.client.get("/.well-known/iam-claims-schema.json")


class IAMAPIUser(HttpUser):
    wait_time = between(3, 8)

    def on_start(self):
        """Authenticate as a test user."""
        resp = self.client.post("/login/", json={"email": "loadtest@clet.gov.gh", "password": "dummy"})
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = ""

    @task(2)
    def get_me(self):
        if self.token:
            self.client.get("/v1/me/", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def get_health(self):
        self.client.get("/health/live")
