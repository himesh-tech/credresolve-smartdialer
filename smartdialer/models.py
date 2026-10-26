from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

class AgentState(str, Enum):
    OFFLINE="OFFLINE"; AVAILABLE="AVAILABLE"; RESERVED="RESERVED"; DIALING="DIALING"
    CONNECTED="CONNECTED"; WRAP_UP="WRAP_UP"; PAUSED="PAUSED"

class CallState(str, Enum):
    QUEUED="QUEUED"; RESERVED="RESERVED"; INITIATED="INITIATED"; RINGING="RINGING"
    ANSWERED="ANSWERED"; CONNECTED="CONNECTED"; COMPLETED="COMPLETED"
    FAILED="FAILED"; CANCELLED="CANCELLED"

TERMINAL_CALL_STATES = {CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED}

class Agent:
    agent_id: str
    state: AgentState = AgentState.AVAILABLE
    current_call_id: Optional[str] = None
    reservation_expires_at: Optional[float] = None

class Borrower:
    borrower_id: str
    priority: int = 0
    attempts: int = 0
    eligible: bool = True

class Call:
    call_id: str
    borrower_id: str
    agent_id: str
    campaign_id: str
    state: CallState = CallState.RESERVED
    provider_call_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_event_sequence: int = -1
    
class ProviderEvent:
    event_id: str
    call_id: str
    state: CallState
    sequence: int
    occurred_at: float = field(default_factory=time.time)
