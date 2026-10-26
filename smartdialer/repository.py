from threading import RLock
import time
from .models import Agent, AgentState, Borrower, Call, CallState, TERMINAL_CALL_STATES

class InMemoryRepository:
    def __init__(self):
        self._lock = RLock()
        self.agents = {}
        self.borrowers = {}
        self.calls = {}
        self.processed_event_ids = set()
        self.campaign_limits = {}
        self.initiated_by_campaign = {}

    def add_agent(self, agent):
        with self._lock: self.agents[agent.agent_id] = agent

    def add_borrower(self, borrower):
        with self._lock: self.borrowers[borrower.borrower_id] = borrower

    def set_campaign_limit(self, campaign_id, limit):
        with self._lock: self.campaign_limits[campaign_id] = max(0, limit)

    def available_agent_count(self):
        with self._lock: return sum(a.state == AgentState.AVAILABLE for a in self.agents.values())

    def eligible_borrower_count(self):
        with self._lock: return sum(b.eligible for b in self.borrowers.values())

    def reserve_pair(self, campaign_id, lease_seconds=30):
        with self._lock:
            limit = self.campaign_limits.get(campaign_id, 10**9)
            initiated = self.initiated_by_campaign.get(campaign_id, 0)
            active = sum(c.campaign_id == campaign_id and c.state not in TERMINAL_CALL_STATES
                         for c in self.calls.values())
            if initiated + active >= limit: return None
            agents = sorted((a for a in self.agents.values() if a.state == AgentState.AVAILABLE),
                            key=lambda a: a.agent_id)
            borrowers = sorted((b for b in self.borrowers.values() if b.eligible),
                               key=lambda b: (-b.priority, b.attempts, b.borrower_id))
            if not agents or not borrowers: return None
            agent, borrower = agents[0], borrowers[0]
            agent.state = AgentState.RESERVED
            borrower.eligible = False
            borrower.attempts += 1
            call = Call(f"call_{len(self.calls)+1:06d}", borrower.borrower_id,
                        agent.agent_id, campaign_id)
            agent.current_call_id = call.call_id
            agent.reservation_expires_at = time.time() + lease_seconds
            self.calls[call.call_id] = call
            return call

    def mark_initiated(self, call_id):
        with self._lock:
            call = self.calls[call_id]
            if call.state in TERMINAL_CALL_STATES: return
            call.state = CallState.INITIATED
            self.initiated_by_campaign[call.campaign_id] = self.initiated_by_campaign.get(call.campaign_id, 0) + 1
            self.agents[call.agent_id].state = AgentState.DIALING

    def apply_event(self, event):
        with self._lock:
            if event.event_id in self.processed_event_ids: return "duplicate"
            self.processed_event_ids.add(event.event_id)
            call = self.calls.get(event.call_id)
            if not call or call.state in TERMINAL_CALL_STATES: return "ignored"
            if event.sequence <= call.last_event_sequence: return "ignored"
            rank = {CallState.RESERVED: 0, CallState.INITIATED: 1, CallState.RINGING: 2,
                    CallState.ANSWERED: 3, CallState.CONNECTED: 4, CallState.COMPLETED: 5,
                    CallState.FAILED: 5, CallState.CANCELLED: 5}
            if event.state not in TERMINAL_CALL_STATES and rank.get(event.state, -1) < rank.get(call.state, -1):
                return "ignored"
            call.state = event.state
            call.last_event_sequence = event.sequence
            agent = self.agents[call.agent_id]
            if event.state == CallState.RINGING: agent.state = AgentState.DIALING
            elif event.state in (CallState.ANSWERED, CallState.CONNECTED): agent.state = AgentState.CONNECTED
            elif event.state in TERMINAL_CALL_STATES:
                agent.state = AgentState.WRAP_UP if event.state == CallState.COMPLETED else AgentState.AVAILABLE
                agent.current_call_id = None
                agent.reservation_expires_at = None
                if event.state in (CallState.FAILED, CallState.CANCELLED):
                    self.borrowers[call.borrower_id].eligible = True
            return "applied"

    def release_expired_reservations(self, now=None):
        now = now or time.time()
        released = 0
        with self._lock:
            for agent in self.agents.values():
                if agent.state == AgentState.RESERVED and agent.reservation_expires_at and agent.reservation_expires_at <= now:
                    call = self.calls.get(agent.current_call_id)
                    if call and call.state == CallState.RESERVED:
                        call.state = CallState.FAILED
                        self.borrowers[call.borrower_id].eligible = True
                    agent.state, agent.current_call_id, agent.reservation_expires_at = AgentState.AVAILABLE, None, None
                    released += 1
        return released

    def make_agents_available(self):
        with self._lock:
            for agent in self.agents.values():
                if agent.state == AgentState.WRAP_UP: agent.state = AgentState.AVAILABLE

    def active_calls(self, campaign_id=None):
        with self._lock:
            return [c for c in self.calls.values() if c.state not in TERMINAL_CALL_STATES
                    and (campaign_id is None or c.campaign_id == campaign_id)]
