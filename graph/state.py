from typing import TypedDict, List, Dict, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Represents a single message in the debate"""

    agent: str
    content: str
    turn: int
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: Literal["argument", "rebuttal", "question", "answer", "conclusion"]


class JudgeVote(BaseModel):
    """Represents a judge's vote and analysis"""

    judge_id: str
    winner: Literal["Agent A", "Agent B"]
    confidence: float
    reasoning: str
    criteria_scores: Dict[str, float]  # Scores for each evaluation criterion


class DebateState(TypedDict):
    """Main state object for the debate workflow"""

    topic: str
    agent_a_persona: str
    agent_b_persona: str
    messages: List[Message]
    current_turn: int
    current_speaker: Literal["Agent A", "Agent B"]
    debate_complete: bool
    judge_votes: List[JudgeVote]
    final_winner: Optional[str]
    metrics: Dict[str, any]
