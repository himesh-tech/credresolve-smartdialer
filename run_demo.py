from smartdialer.demo_data import build_repository
from smartdialer.providers import ReliableMockProvider, FlakyMockProvider
from smartdialer.service import SmartDialer

if __name__ == "__main__":
    repo = build_repository(5, 20, campaign_limit=15)
    dialer = SmartDialer(repo, ReliableMockProvider())
    print("=== Progressive mode ===")
    print(dialer.run_batch("progressive"))
    print("Metrics:", dialer.metrics)
    repo2 = build_repository(5, 20, campaign_limit=15)
    dialer2 = SmartDialer(repo2, FlakyMockProvider())
    print("\\n=== Predictive mode with flaky provider ===")
    print(dialer2.run_batch("predictive", answer_rate=0.5))
    print("Metrics:", dialer2.metrics)
