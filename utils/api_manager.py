import os
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import itertools

load_dotenv()


class APIManager:
    """Manages multiple OpenAI API keys with round-robin distribution"""

    def __init__(self):
        self.base_url=os.getenv("OPENAI_BASE_URL")
        self.api_keys = []
        for i in range(1, 6):
            key = os.getenv(f"OPENAI_API_KEY{i}")
            if key:
                self.api_keys.append(key)

        if not self.api_keys:
            raise ValueError("No OpenAI API keys found in environment")

        self.key_cycle = itertools.cycle(self.api_keys)

    def get_llm(
        self, temperature: float = 0.7, model: str = "gemini-2.5-flash-preview-05-20"
    ) -> ChatOpenAI:
        """Get an LLM instance with the next available API key"""
        api_key = next(self.key_cycle)
        return ChatOpenAI(api_key=api_key, model=model, base_url=self.base_url, temperature=temperature)
