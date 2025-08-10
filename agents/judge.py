import re
from typing import List, Dict, Tuple
from langchain.prompts import ChatPromptTemplate
from utils.api_manager import APIManager
from graph.state import DebateState, JudgeVote, Message
import json

JUDEGE_LLM_MODEL="gemini-2.5-pro"
class JudgeAgent:
    """Implements a judge agent for evaluating debates"""

    EVALUATION_CRITERIA = {
        "clarity": "How clear and understandable were the arguments?",
        "evidence": "How well supported were claims with facts and logic?",
        "relevance": "How directly did responses address the topic and opponent?",
        "persuasiveness": "How compelling and convincing were the arguments?",
        "conduct": "How respectful and professional was the debate conduct?",
        "consistency": "How logically consistent were the positions throughout?",
    }

    def __init__(self, judge_id: str, api_manager: APIManager):
        self.judge_id = judge_id
        self.api_manager = api_manager
        # self.evaluation_prompt = ChatPromptTemplate.from_messages(
        #     [("system", self._get_system_prompt()), ("human", "{debate_transcript}")]
        # )
        self.evaluation_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._get_system_prompt().replace("{", "{{").replace("}", "}}")),
                ("human", "{debate_transcript}"),
            ]
        )

    def _get_system_prompt(self) -> str:
        """Constructs the judge's system prompt"""
        return """You are an impartial judge evaluating a formal debate between two agents with opposing ideological views.

Your task is to:
1. Carefully analyze the entire debate transcript
2. Evaluate each agent's performance across multiple criteria
3. Determine a winner based on debate quality, not your personal agreement
4. Provide detailed reasoning for your decision

Evaluation criteria:
- Clarity: How clear and understandable were the arguments?
- Evidence: How well supported were claims with facts and logic?
- Relevance: How directly did responses address the topic and opponent?
- Persuasiveness: How compelling and convincing were the arguments?
- Conduct: How respectful and professional was the debate conduct?
- Consistency: How logically consistent were the positions throughout?

Important: Judge based on debate performance, not ideological preference.

Provide your evaluation in this JSON format:
{
    "reasoning": "Detailed explanation of your decision...",
    "winner": "Agent A" or "Agent B",
    "confidence": 0.0 to 1.0,
    "criteria_scores": {
        "clarity": {"agent_a": 0-10, "agent_b": 0-10},
        "evidence": {"agent_a": 0-10, "agent_b": 0-10},
        "relevance": {"agent_a": 0-10, "agent_b": 0-10},
        "persuasiveness": {"agent_a": 0-10, "agent_b": 0-10},
        "conduct": {"agent_a": 0-10, "agent_b": 0-10},
        "consistency": {"agent_a": 0-10, "agent_b": 0-10}
    },
    "key_moments": ["List of decisive moments in the debate"],
    "strengths": {
        "agent_a": ["List of Agent A's strengths"],
        "agent_b": ["List of Agent B's strengths"]
    },
    "weaknesses": {
        "agent_a": ["List of Agent A's weaknesses"],
        "agent_b": ["List of Agent B's weaknesses"]
    }
}"""

    def evaluate_debate(self, state: DebateState) -> JudgeVote:
        """Evaluates the complete debate and returns a vote"""
        # Prepare debate transcript
        transcript = self._prepare_transcript(state)

        # Get LLM evaluation
        llm = self.api_manager.get_llm(temperature=0.3)
        # llm = self.api_manager.get_llm(temperature=0.3, model="gemini-2.5-pro")
        messages = self.evaluation_prompt.format_messages(debate_transcript=transcript)
        response = llm.invoke(messages)

        # Parse JSON response
        try:
            content_str = response.content
            json_match = re.search(r'\{.*\}', content_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                evaluation = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in content.")
        except:
            # Fallback parsing if JSON fails
            evaluation = self._parse_evaluation_fallback(response.content)

        # Calculate aggregate scores
        criteria_scores = {}
        for criterion, scores in evaluation.get("criteria_scores", {}).items():
            total_a = scores.get("agent_a", 0)
            total_b = scores.get("agent_b", 0)
            criteria_scores[criterion] = {
                "agent_a": total_a,
                "agent_b": total_b,
                "winner": "agent_a" if total_a > total_b else "agent_b",
            }

        return JudgeVote(
            judge_id=self.judge_id,
            winner=evaluation.get("winner", "Agent A"),
            confidence=evaluation.get("confidence", -2),
            reasoning=evaluation.get("reasoning", ""),
            criteria_scores=criteria_scores,
        )

    def _prepare_transcript(self, state: DebateState) -> str:
        """Prepares a formatted transcript of the debate"""
        transcript_parts = [
            f"DEBATE TOPIC: {state['topic']}",
            f"AGENT A POSITION: {state['agent_a_persona'][:200]}...",
            f"AGENT B POSITION: {state['agent_b_persona'][:200]}...",
            "\nDEBATE TRANSCRIPT:\n",
        ]

        for i, msg in enumerate(state["messages"]):
            transcript_parts.append(
                f"Turn {msg.turn} - {msg.agent} ({msg.message_type}):\n{msg.content}\n"
            )

        return "\n".join(transcript_parts)

    def _parse_evaluation_fallback(self, content: str) -> Dict:
        """Fallback parser if JSON parsing fails"""
        # Simple extraction logic
        evaluation = {
            "winner": "Agent A" if "Agent A" in content[:100] else "Agent B",
            "confidence": -1,
            "reasoning": content,
            "criteria_scores": {},
        }
        return evaluation
