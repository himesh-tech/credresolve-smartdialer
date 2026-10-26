from time import perf_counter
from smartdialer.demo_data import build_repository
from smartdialer.providers import ReliableMockProvider
from smartdialer.service import SmartDialer

if __name__ == "__main__":
    repo = build_repository(100, 5000, campaign_limit=1000)
    dialer = SmartDialer(repo, ReliableMockProvider())
    start = perf_counter()
    result = dialer.run_batch("predictive", answer_rate=0.5)
    elapsed = perf_counter() - start
    print("Synthetic local mock load test")
    print(f"Created calls: {len(result['created'])}")
    print(f"Available agents after run: {repo.available_agent_count()}")
    print(f"Elapsed seconds: {elapsed:.4f}")
    print(f"Local mock calls/second: {len(result['created']) / max(elapsed, 1e-9):.1f}")
    assert len(result["created"]) <= 100
    print("PASS: batch did not exceed 100 initially available agents.")
