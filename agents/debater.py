from typing import List, Dict, Optional
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from agents.personas import PersonaManager
from utils.api_manager import APIManager
from graph.state import Message, DebateState
import json


class DebaterAgent:
    """Implements a debating agent with ideological persona"""

    def __init__(self, agent_id: str, persona: str, api_manager: APIManager):
        self.agent_id = agent_id
        self.persona = persona
        self.api_manager = api_manager
        self.debate_prompt = ChatPromptTemplate.from_messages(
            [("system", self._get_system_prompt()), ("human", "{context}")]
        )

    def _get_system_prompt(self) -> str:
        """Constructs the system prompt including persona and debate instructions"""
        return f"""{self.persona}

You are participating in a formal debate. Your responses should:

1. **Structure**: Begin with a clear position statement, provide supporting arguments with evidence, and conclude with a compelling summary.

2. **Techniques**: 
   - Use logical reasoning and factual evidence
   - Employ rhetorical questions strategically
   - Address counterarguments preemptively
   - Build upon previous points coherently
   
3. **Engagement**:
   - Directly respond to your opponent's arguments
   - Ask probing questions to expose weaknesses
   - Use analogies and examples effectively
   - Maintain intellectual honesty while advocating strongly

4. **Tone**: Remain respectful but assertive, passionate but logical.

Remember: You have only 5 turns to make your case. Make each response count.

Classify your response type as one of: "argument", "rebuttal", "question", "answer", or "conclusion"
Format: Start with [TYPE: your_type] then your response."""

    def generate_response(self, state: DebateState) -> Message:
        """Generates a response based on the current debate state"""
        # Prepare context from debate history
        context = self._prepare_context(state)

        # Get LLM response
        llm = self.api_manager.get_llm(temperature=0.8)
        messages = self.debate_prompt.format_messages(context=context)
        response = llm.invoke(messages)

        # Parse response type and content
        content = response.content
        message_type = "argument"  # default

        if content.startswith("[TYPE:"):
            try:
                type_end = content.index("]")
                message_type = content[6:type_end].strip().lower()
                content = content[type_end + 1 :].strip()
            except:
                pass

        return Message(
            agent=self.agent_id,
            content=content,
            turn=state["current_turn"],
            message_type=message_type,
        )

    def _prepare_context(self, state: DebateState) -> str:
        """Prepares the context for the LLM including debate history"""
        context_parts = [
            f"Debate Topic: {state['topic']}",
            f"Current Turn: {state['current_turn']} of 10",
            f"You are: {self.agent_id}",
            "",
        ]

        if state["messages"]:
            context_parts.append("Debate History:")
            for msg in state["messages"][-6:]:  # Last 6 messages for context
                context_parts.append(
                    f"{msg.agent} ({msg.message_type}): {msg.content[:500]}..."
                )

        if state["current_turn"] == 9 and self.agent_id == "Agent A":
            context_parts.append(
                "\nThis is your FINAL turn. Make your closing argument compelling and memorable."
            )
        elif state["current_turn"] == 10 and self.agent_id == "Agent B":
            context_parts.append(
                "\nThis is your FINAL turn. Make your closing argument compelling and memorable."
            )

        return "\n".join(context_parts)
