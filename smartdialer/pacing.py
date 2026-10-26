from dataclasses import dataclass

@dataclass
class PacingDecision:
    requested_calls: int
    rationale: str

class ProgressiveDialer:
    def propose(self, available_agents, eligible_borrowers):
        n = max(0, min(available_agents, eligible_borrowers))
        return PacingDecision(n, "One agent-bound call per available agent.")

class PredictivePacingEngine:
    def propose(self, available_agents, eligible_borrowers, answer_rate, provider_healthy=True,
                ringing_calls=0, connected_calls=0, max_overdial_factor=1.25):
        if available_agents <= 0 or eligible_borrowers <= 0:
            return PacingDecision(0, "No available capacity or eligible borrowers.")
        if not provider_healthy:
            return PacingDecision(min(available_agents, eligible_borrowers), "Provider unhealthy: progressive fallback.")
        rate = min(1.0, max(0.05, answer_rate))
        spare = max(0, available_agents - ringing_calls - connected_calls)
        desired = int(spare / rate)
        cap = int(max(1, spare) * max_overdial_factor)
        count = min(eligible_borrowers, max(0, min(desired, cap)))
        return PacingDecision(count, f"Free capacity={spare}; answer-rate estimate={rate:.0%}; raw={desired}; overdial cap={cap}.")

class SafetyController:
    def approve(self, requested_calls, available_agents, eligible_borrowers, provider_healthy, campaign_remaining):
        if not provider_healthy:
            n = min(available_agents, eligible_borrowers, campaign_remaining)
            return PacingDecision(n, "Safety fallback: provider unhealthy; progressive capacity.")
        n = max(0, min(requested_calls, available_agents, eligible_borrowers, campaign_remaining))
        return PacingDecision(n, f"Safety cap applied: request={requested_calls}, agents={available_agents}, borrowers={eligible_borrowers}, campaign remaining={campaign_remaining}.")
