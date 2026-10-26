# Architecture Decision Record

## Problem
Increase agent utilization without initiating more agent-bound calls than the available safe capacity. Workers can race or crash, and telecom events may be duplicated or out of order.

## Main decision: separate pacing and safety
Progressive or predictive pacing proposes a count. The independent Safety Controller caps it by available agents, eligible borrowers, provider health and remaining campaign budget. Predictive logic has no provider reference and cannot bypass the controller.

## Progressive vs predictive
Progressive mode requests at most one call per available agent. Predictive mode uses an explainable heuristic: `spare = max(0, available agents - ringing calls - connected calls)`, `desired = floor(spare / answer_rate)`, with answer rate clipped to 5–100% and an overdial cap. The safety controller still hard-caps approved calls to currently available agents. This deliberately preserves the progressive safety property rather than maximizing overdialing.

## Atomic reservations
The in-memory repository reserves agent and borrower under one lock, preventing two local threads from allocating the same agent. This is not sufficient across multiple processes. Production should use a transaction and conditional update (`WHERE state='AVAILABLE'`), verify the affected row count, add unique constraints for active assignments, and use lease/fencing tokens.

## Provider interface
Mock Provider A emits normal ordered events. Mock Provider B can timeout, duplicate events and deliver them out of order. The service does not need to know provider-specific implementation details.

## Event processing
Event IDs are idempotent. Sequence numbers and terminal-state checks prevent late events from regressing completed/failed calls. A production implementation should persist an event inbox, validate webhook signatures, retain raw payloads, retry safely, and reconcile conflicting states with provider status.

## Failure handling
- Initiation timeout: fail call and release agent/borrower.
- Duplicate event: ignore by event ID.
- Out-of-order event: ignore stale sequence or any event after terminal state.
- Worker crash during reservation: reservation lease can expire and be reclaimed.
- Sudden agent availability drop: next pacing decision uses current available count.
- Provider unhealthy: safety controller falls back to progressive capacity; provider adapter rejects initiation.

## State machines
Agent: `OFFLINE -> AVAILABLE -> RESERVED -> DIALING -> CONNECTED -> WRAP_UP -> AVAILABLE`. Failed setup releases `RESERVED/DIALING` back to `AVAILABLE`; `PAUSED` is a separate operational state.

Call: `QUEUED -> RESERVED -> INITIATED -> RINGING -> ANSWERED -> CONNECTED -> COMPLETED`, with `FAILED` or `CANCELLED` terminal exits from applicable active states.

## Metrics
Prototype metrics: initiated, connected, completed, failed, duplicate/ignored events and provider errors. Production dashboard should add agent utilization, answer rate, abandonment rate, setup latency, provider timeout rate, event lag, reservation expiry and cost per recovered rupee.

## Scaling
At 100 -> 1,000 -> 10,000 agents, likely bottlenecks include hot campaign/agent records, database contention, event ingestion and provider rate limits. Profile first; then consider campaign partitioning, transactional conditional reservations, durable queues, idempotent consumers, provider circuit breakers and observability.

## ROI and experiment
Synthetic simulation cannot prove business ROI. Before investment, run a randomized or stepped-wedge experiment across comparable campaign/portfolio segments. Predefine guardrails for complaint rate and abandonment; compare successful connections, kept promises/payments, agent utilization and cost per recovered rupee with confidence intervals.

## Known limitations
This prototype uses process-local memory, synchronous mock provider events and synthetic data. It is not production ready and does not establish actual financial impact.
