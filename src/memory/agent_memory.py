import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class AgentMemoryStore:
    """
    Private lasting memory for an individual agent (Acceptance Check 9).
    Strictly isolated per agent ID (Heimdall, Thor, Loki, Odin).
    """
    def __init__(self, agent_id: str, base_dir: str = "data/memory"):
        self.agent_id = agent_id.lower()
        self.storage_dir = os.path.join(base_dir, self.agent_id)
        os.makedirs(self.storage_dir, exist_ok=True)
        self.memory_file = os.path.join(self.storage_dir, "lessons.json")
        self.events_log = os.path.join(self.storage_dir, "memory_events.jsonl")
        self.memories: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2)

    def log_event(self, event_type: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.agent_id,
            "event_type": event_type,
            **details
        }
        with open(self.events_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_memories(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        self.log_event("memory_read", {"scope_queried": scope, "count": len(self.memories)})
        if not scope:
            return self.memories
        return [m for m in self.memories if m.get("scope") == scope or m.get("scope") == "global"]

    def write_memory(self, memory_type: str, content: str, scope: str = "global", basis_refs: List[str] = None):
        mem_id = f"{self.agent_id}_mem_{len(self.memories) + 1}"
        record = {
            "id": mem_id,
            "agent_id": self.agent_id,
            "memory_type": memory_type,
            "content": content,
            "scope": scope,
            "basis_refs": basis_refs or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.memories.append(record)
        self._save()
        self.log_event("memory_written", {"memory_id": mem_id, "content": content})
        return record
