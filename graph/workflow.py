from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Literal
import json
from datetime import datetime

from graph.state import DebateState, Message, JudgeVote
from agents.debater import DebaterAgent
from agents.judge import JudgeAgent
from agents.personas import PersonaManager
from utils.api_manager import APIManager
from utils.metrics import MetricsCollector


class DebateWorkflow:
    """Orchestrates the multi-agent debate using LangGraph"""

    def __init__(self, topic: str):
        self.topic = topic
        self.api_manager = APIManager()
        self.metrics_collector = MetricsCollector()

        # Initialize agents
        agent_a_persona, agent_b_persona = PersonaManager.get_personas(topic)
        self.agent_a = DebaterAgent("Agent A", agent_a_persona, self.api_manager)
        self.agent_b = DebaterAgent("Agent B", agent_b_persona, self.api_manager)

        # Initialize judges
        self.judges = [JudgeAgent(f"Judge {i+1}", self.api_manager) for i in range(3)]

        # Build workflow
        self.memory = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Builds the LangGraph workflow"""
        workflow = StateGraph(DebateState)

        # Add nodes
        workflow.add_node("agent_a_turn", self.agent_a_turn)
        workflow.add_node("agent_b_turn", self.agent_b_turn)
        workflow.add_node("judge_evaluation", self.judge_evaluation)
        workflow.add_node("final_decision", self.final_decision)

        # Add edges
        workflow.add_edge("agent_a_turn", "agent_b_turn")
        workflow.add_edge("agent_b_turn", "agent_a_turn")

        # Conditional edges
        workflow.add_conditional_edges(
            "agent_a_turn",
            self.should_continue_debate,
            {True: "agent_b_turn", False: "judge_evaluation"},
        )

        workflow.add_conditional_edges(
            "agent_b_turn",
            self.should_continue_debate,
            {True: "agent_a_turn", False: "judge_evaluation"},
        )

        workflow.add_edge("judge_evaluation", "final_decision")
        workflow.add_edge("final_decision", END)

        # Set entry point
        workflow.set_entry_point("agent_a_turn")

        return workflow.compile(checkpointer=self.memory)

    def agent_a_turn(self, state: DebateState) -> DebateState:
        """Executes Agent A's turn"""
        if state["current_turn"] > 10:
            return state

        # Generate response
        response = self.agent_a.generate_response(state)
        state["messages"].append(response)

        # Update metrics
        self.metrics_collector.update_message_metrics(response)

        # Update state
        state["current_speaker"] = "Agent B"

        return state

    def agent_b_turn(self, state: DebateState) -> DebateState:
        """Executes Agent B's turn"""
        # Generate response
        response = self.agent_b.generate_response(state)
        state["messages"].append(response)

        # Update metrics
        self.metrics_collector.update_message_metrics(response)

        # Update state
        state["current_turn"] += 1
        state["current_speaker"] = "Agent A"

        return state

    def should_continue_debate(self, state: DebateState) -> bool:
        """Determines if the debate should continue"""
        return state["current_turn"] <= 10

    def judge_evaluation(self, state: DebateState) -> DebateState:
        """All judges evaluate the debate"""
        state["debate_complete"] = True

        for judge in self.judges:
            vote = judge.evaluate_debate(state)
            state["judge_votes"].append(vote)

        return state

    def final_decision(self, state: DebateState) -> DebateState:
        """Determines the final winner based on judge votes"""
        # Count votes
        vote_counts = {"Agent A": 0, "Agent B": 0}
        for vote in state["judge_votes"]:
            vote_counts[vote.winner] += 1

        # Determine winner
        state["final_winner"] = max(vote_counts, key=vote_counts.get)

        # Update metrics
        state["metrics"] = self.metrics_collector.get_final_metrics(state)

        return state

    def run(self) -> DebateState:
        """Runs the complete debate workflow"""
        # Initialize state
        agent_a_persona, agent_b_persona = PersonaManager.get_personas(self.topic)

        initial_state = DebateState(
            topic=self.topic,
            agent_a_persona=agent_a_persona,
            agent_b_persona=agent_b_persona,
            messages=[],
            current_turn=1,
            current_speaker="Agent A",
            debate_complete=False,
            judge_votes=[],
            final_winner=None,
            metrics={},
        )

        # Run workflow
        config = {
            "configurable": {
                "thread_id": f"debate_{self.topic}_{datetime.now().isoformat()}"
            }
        }
        final_state = self.workflow.invoke(initial_state, config)

        return final_state
