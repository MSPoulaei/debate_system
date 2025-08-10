from typing import TypedDict, List, Dict, Optional, Literal, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
import operator

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
    topic: str
    agent_a_persona: str
    agent_b_persona: str
    messages: Annotated[List[Message], operator.add]       # allows returning {"messages": [msg]}
    current_turn: int
    current_speaker: str
    debate_complete: bool
    judge_votes: Annotated[List[JudgeVote], operator.add]  # allows returning {"judge_votes": [vote]}
    final_winner: Optional[str]
    metrics: Dict