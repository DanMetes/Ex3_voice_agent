from collections import deque
from typing import List, Dict, Any

class ConversationState:
    """Ring buffer conversation memory (system + N turns)."""
    def __init__(self, max_turns: int = 8, system_prompt: str | None = None):
        self.max_turns = max_turns
        self.system_prompt = system_prompt or (
            "You are a helpful, concise voice assistant. "
            "Keep replies short (1-3 sentences) and ask clarifying questions when needed."
        )
        self.history: deque[Dict[str, str]] = deque()

    def reset(self):
        self.history.clear()

    def add_user(self, text: str):
        self.history.append({ "role": "user", "content": text })
        self._trim()

    def add_assistant(self, text: str):
        self.history.append({ "role": "assistant", "content": text })
        self._trim()

    def get_messages(self) -> List[Dict[str, str]]:
        msgs = [{"role":"system","content": self.system_prompt}]
        msgs.extend(list(self.history))
        return msgs

    def _trim(self):
        # keep only last max_turns*2 messages (user+assistant pairs)
        while len(self.history) > self.max_turns * 2:
            self.history.popleft()
