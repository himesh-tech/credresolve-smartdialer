from dataclasses import dataclass
from .models import CallState, ProviderEvent

class ProviderError(RuntimeError): pass

@dataclass
class ProviderResult:
    provider_call_id: str
    events: list

class MockProvider:
    name = "base"
    def __init__(self): self.healthy = True
    def initiate(self, call_id): raise NotImplementedError

class ReliableMockProvider(MockProvider):
    name = "provider_a"
    def initiate(self, call_id):
        if not self.healthy: raise ProviderError("provider unavailable")
        states = [CallState.RINGING, CallState.ANSWERED, CallState.CONNECTED, CallState.COMPLETED]
        events = [ProviderEvent(f"{call_id}:{i}", call_id, state, i) for i, state in enumerate(states, 1)]
        return ProviderResult(f"{self.name}_{call_id}", events)

class FlakyMockProvider(MockProvider):
    name = "provider_b"
    def __init__(self, fail=False, duplicate=True, out_of_order=True):
        super().__init__()
        self.fail, self.duplicate, self.out_of_order = fail, duplicate, out_of_order
    def initiate(self, call_id):
        if self.fail or not self.healthy: raise ProviderError("simulated timeout")
        events = [ProviderEvent(f"{call_id}:1", call_id, CallState.RINGING, 1),
                  ProviderEvent(f"{call_id}:2", call_id, CallState.ANSWERED, 2),
                  ProviderEvent(f"{call_id}:3", call_id, CallState.COMPLETED, 3)]
        if self.duplicate: events.insert(2, events[1])
        if self.out_of_order: events = [events[0], events[-1], *events[1:-1]]
        return ProviderResult(f"{self.name}_{call_id}", events)
