from .models import Agent, Borrower
from .repository import InMemoryRepository

def build_repository(agent_count=5, borrower_count=30, campaign_id="default", campaign_limit=100):
    repo = InMemoryRepository()
    for i in range(1, agent_count + 1): repo.add_agent(Agent(f"agent_{i:03d}"))
    for i in range(1, borrower_count + 1): repo.add_borrower(Borrower(f"borrower_{i:04d}", priority=i % 3))
    repo.set_campaign_limit(campaign_id, campaign_limit)
    return repo
