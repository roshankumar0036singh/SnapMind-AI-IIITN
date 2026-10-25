from abc import ABC, abstractmethod
from typing import Any, Dict, List
import openai
import instructor
from src.config import get_settings
from src.schemas.case_file import CaseFile
from src.memory.agent_memory import AgentMemoryStore

settings = get_settings()

class BaseAgent(ABC):
    """
    Base class for all Runemark agents.
    Enforces planner-free wake-up conditions and isolated private memory.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id.lower()
        self.memory = AgentMemoryStore(self.agent_id)
        
        # Grok (xAI) client wrapped with instructor for guaranteed Pydantic output
        raw_client = openai.OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=settings.XAI_API_KEY or "dummy_key_for_offline"
        )
        self.client = instructor.from_openai(raw_client)

    @abstractmethod
    def can_wake(self, case: CaseFile) -> bool:
        """Deterministic wake-up condition evaluated over CaseFile state."""
        pass

    @abstractmethod
    async def act(self, case: CaseFile) -> Dict[str, Any]:
        """Perform action (generate claims, attacks, or rulings) without global coordinator."""
        pass
