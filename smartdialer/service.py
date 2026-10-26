from .models import CallState, ProviderEvent
from .pacing import ProgressiveDialer, PredictivePacingEngine, SafetyController
from .providers import ProviderError

class SmartDialer:
    def __init__(self, repository, provider, campaign_id="default"):
        self.repo, self.provider, self.campaign_id = repository, provider, campaign_id
        self.progressive, self.predictive, self.safety = ProgressiveDialer(), PredictivePacingEngine(), SafetyController()
        self.metrics = {"requests": 0, "initiated": 0, "connected": 0, "completed": 0,
                        "failed": 0, "provider_errors": 0, "duplicate_events": 0, "ignored_events": 0}

    def run_batch(self, mode="progressive", answer_rate=0.5):
        available, borrowers = self.repo.available_agent_count(), self.repo.eligible_borrower_count()
        active = self.repo.active_calls(self.campaign_id)
        ringing = sum(c.state == CallState.RINGING for c in active)
        connected = sum(c.state in (CallState.ANSWERED, CallState.CONNECTED) for c in active)
        if mode == "predictive":
            proposal = self.predictive.propose(available, borrowers, answer_rate, self.provider.healthy, ringing, connected)
        else:
            proposal = self.progressive.propose(available, borrowers)
        limit = self.repo.campaign_limits.get(self.campaign_id, 10**9)
        used = self.repo.initiated_by_campaign.get(self.campaign_id, 0)
        remaining = max(0, limit - used - len(active))
        safe = self.safety.approve(proposal.requested_calls, available, borrowers, self.provider.healthy, remaining)
        self.metrics["requests"] += 1
        created = []
        for _ in range(safe.requested_calls):
            call = self.repo.reserve_pair(self.campaign_id)
            if call is None: break
            try:
                result = self.provider.initiate(call.call_id)
                self.repo.mark_initiated(call.call_id)
                self.metrics["initiated"] += 1
                call.provider_call_id = result.provider_call_id
                for event in result.events:
                    status = self.repo.apply_event(event)
                    if status == "duplicate": self.metrics["duplicate_events"] += 1
                    elif status == "ignored": self.metrics["ignored_events"] += 1
                    elif status == "applied":
                        if event.state == CallState.CONNECTED: self.metrics["connected"] += 1
                        elif event.state == CallState.COMPLETED: self.metrics["completed"] += 1
                        elif event.state == CallState.FAILED: self.metrics["failed"] += 1
                created.append(call.call_id)
            except ProviderError:
                self.metrics["provider_errors"] += 1
                self.repo.apply_event(ProviderEvent(f"{call.call_id}:failure", call.call_id, CallState.FAILED, 99))
                self.metrics["failed"] += 1
        self.repo.make_agents_available()
        return {"mode": mode, "proposal": proposal.requested_calls, "approved": safe.requested_calls,
                "created": created, "proposal_reason": proposal.rationale, "safety_reason": safe.rationale}
