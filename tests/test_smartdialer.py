import threading
import unittest
from smartdialer.demo_data import build_repository
from smartdialer.models import CallState, ProviderEvent
from smartdialer.providers import ReliableMockProvider, FlakyMockProvider
from smartdialer.service import SmartDialer

class SmartDialerTests(unittest.TestCase):
    def test_progressive_never_exceeds_available_agents(self):
        repo = build_repository(3, 10)
        result = SmartDialer(repo, ReliableMockProvider()).run_batch("progressive")
        self.assertLessEqual(len(result["created"]), 3)

    def test_predictive_is_safety_capped(self):
        repo = build_repository(4, 50)
        result = SmartDialer(repo, ReliableMockProvider()).run_batch("predictive", answer_rate=0.05)
        self.assertLessEqual(result["approved"], 4)
        self.assertLessEqual(len(result["created"]), 4)

    def test_provider_failure_releases_capacity(self):
        repo = build_repository(1, 2)
        dialer = SmartDialer(repo, FlakyMockProvider(fail=True))
        dialer.run_batch("progressive")
        self.assertEqual(repo.available_agent_count(), 1)
        self.assertEqual(dialer.metrics["provider_errors"], 1)

    def test_two_workers_cannot_reserve_same_agent(self):
        repo = build_repository(1, 2)
        results, lock = [], threading.Lock()
        def worker():
            call = repo.reserve_pair("default")
            if call:
                with lock: results.append(call)
        threads = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in threads]; [t.join() for t in threads]
        self.assertEqual(len(results), 1)

    def test_duplicate_event_id_is_idempotent(self):
        repo = build_repository(1, 2)
        call = repo.reserve_pair("default")
        repo.mark_initiated(call.call_id)
        event = ProviderEvent("same-event", call.call_id, CallState.RINGING, 1)
        self.assertEqual(repo.apply_event(event), "applied")
        self.assertEqual(repo.apply_event(event), "duplicate")

    def test_terminal_call_does_not_regress(self):
        repo = build_repository(1, 2)
        call = repo.reserve_pair("default")
        repo.mark_initiated(call.call_id)
        self.assertEqual(repo.apply_event(ProviderEvent("done", call.call_id, CallState.COMPLETED, 4)), "applied")
        self.assertEqual(repo.apply_event(ProviderEvent("late", call.call_id, CallState.RINGING, 1)), "ignored")
        self.assertEqual(repo.calls[call.call_id].state, CallState.COMPLETED)

if __name__ == "__main__": unittest.main()
