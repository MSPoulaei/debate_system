from typing import Dict, List
from collections import Counter, defaultdict
from graph.state import DebateState, Message
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class MetricsCollector:
    """Collects and analyzes debate metrics"""

    def __init__(self):
        self.message_types = defaultdict(lambda: defaultdict(int))
        self.word_counts = defaultdict(list)
        self.response_times = []
        self.rhetorical_questions = defaultdict(int)

    def update_message_metrics(self, message: Message):
        """Updates metrics with a new message"""
        # Message type tracking
        self.message_types[message.agent][message.message_type] += 1

        # Word count
        word_count = len(message.content.split())
        self.word_counts[message.agent].append(word_count)

        # Rhetorical questions
        question_count = message.content.count("?")
        if question_count > 0:
            self.rhetorical_questions[message.agent] += question_count

    def get_final_metrics(self, state: DebateState) -> Dict:
        """Compiles final metrics for the debate"""
        metrics = {
            "total_turns": state["current_turn"] - 1,
            "total_messages": len(state["messages"]),
            "message_types": dict(self.message_types),
            "average_word_counts": {
                agent: sum(counts) / len(counts) if counts else 0
                for agent, counts in self.word_counts.items()
            },
            "total_word_counts": {
                agent: sum(counts) for agent, counts in self.word_counts.items()
            },
            "rhetorical_questions": dict(self.rhetorical_questions),
            "judge_agreement": self._calculate_judge_agreement(state["judge_votes"]),
            "confidence_scores": [vote.confidence for vote in state["judge_votes"]],
            "criteria_analysis": self._analyze_criteria(state["judge_votes"]),
        }

        return metrics

    def _calculate_judge_agreement(self, votes: List) -> float:
        """Calculates the level of agreement among judges"""
        if not votes:
            return 0.0

        winners = [vote.winner for vote in votes]
        winner_counts = Counter(winners)
        max_agreement = max(winner_counts.values())

        return max_agreement / len(votes)

    def _analyze_criteria(self, votes: List) -> Dict:
        """Analyzes scoring patterns across criteria"""
        criteria_totals = defaultdict(lambda: {"agent_a": [], "agent_b": []})

        for vote in votes:
            for criterion, scores in vote.criteria_scores.items():
                criteria_totals[criterion]["agent_a"].append(scores.get("agent_a", 0))
                criteria_totals[criterion]["agent_b"].append(scores.get("agent_b", 0))

        # Calculate averages
        criteria_averages = {}
        for criterion, scores in criteria_totals.items():
            criteria_averages[criterion] = {
                "agent_a_avg": (
                    sum(scores["agent_a"]) / len(scores["agent_a"])
                    if scores["agent_a"]
                    else 0
                ),
                "agent_b_avg": (
                    sum(scores["agent_b"]) / len(scores["agent_b"])
                    if scores["agent_b"]
                    else 0
                ),
            }

        return criteria_averages

    def generate_metrics_report(self, state: DebateState, output_dir: str):
        """Generates a comprehensive metrics report with visualizations"""
        metrics = state["metrics"]

        # Create DataFrame for analysis
        df_data = []
        for msg in state["messages"]:
            df_data.append(
                {
                    "turn": msg.turn,
                    "agent": msg.agent,
                    "message_type": msg.message_type,
                    "word_count": len(msg.content.split()),
                    "question_marks": msg.content.count("?"),
                    "exclamations": msg.content.count("!"),
                }
            )

        df = pd.DataFrame(df_data)

        # Generate visualizations
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Debate Metrics: {state["topic"]}', fontsize=16)

        # 1. Message types distribution
        ax1 = axes[0, 0]
        message_type_data = []
        for agent, types in metrics["message_types"].items():
            for msg_type, count in types.items():
                message_type_data.append(
                    {"Agent": agent, "Type": msg_type, "Count": count}
                )

        if message_type_data:
            df_types = pd.DataFrame(message_type_data)
            df_pivot = df_types.pivot(
                index="Type", columns="Agent", values="Count"
            ).fillna(0)
            df_pivot.plot(kind="bar", ax=ax1)
            ax1.set_title("Message Types by Agent")
            ax1.set_xlabel("Message Type")
            ax1.set_ylabel("Count")

        # 2. Word count over turns
        ax2 = axes[0, 1]
        for agent in df["agent"].unique():
            agent_df = df[df["agent"] == agent]
            ax2.plot(agent_df["turn"], agent_df["word_count"], marker="o", label=agent)
        ax2.set_title("Word Count per Turn")
        ax2.set_xlabel("Turn")
        ax2.set_ylabel("Word Count")
        ax2.legend()

        # 3. Judge votes visualization
        ax3 = axes[1, 0]
        judge_data = []
        for vote in state["judge_votes"]:
            judge_data.append(
                {
                    "Judge": vote.judge_id,
                    "Winner": vote.winner,
                    "Confidence": vote.confidence,
                }
            )
        df_judges = pd.DataFrame(judge_data)

        # Vote distribution
        vote_counts = df_judges["Winner"].value_counts()
        ax3.pie(vote_counts.values, labels=vote_counts.index, autopct="%1.1f%%")
        ax3.set_title("Judge Vote Distribution")

        # 4. Criteria scores comparison
        ax4 = axes[1, 1]
        criteria_data = metrics["criteria_analysis"]
        criteria_names = list(criteria_data.keys())
        agent_a_scores = [criteria_data[c]["agent_a_avg"] for c in criteria_names]
        agent_b_scores = [criteria_data[c]["agent_b_avg"] for c in criteria_names]

        x = range(len(criteria_names))
        width = 0.35
        ax4.bar([i - width / 2 for i in x], agent_a_scores, width, label="Agent A")
        ax4.bar([i + width / 2 for i in x], agent_b_scores, width, label="Agent B")
        ax4.set_xlabel("Criteria")
        ax4.set_ylabel("Average Score")
        ax4.set_title("Average Scores by Criteria")
        ax4.set_xticks(x)
        ax4.set_xticklabels(criteria_names, rotation=45)
        ax4.legend()

        plt.tight_layout()
        plt.savefig(f"{output_dir}/metrics_{state['topic']}.png")
        plt.close()

        # Generate text report
        report = f"""
# Debate Metrics Report
## Topic: {state['topic']}
## Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Overall Statistics
- Total Turns: {metrics['total_turns']}
- Total Messages: {metrics['total_messages']}
- Final Winner: {state['final_winner']}
- Judge Agreement: {metrics['judge_agreement']*100:.1f}%

### Agent Performance
#### Agent A
- Average Word Count: {metrics['average_word_counts'].get('Agent A', 0):.1f}
- Total Words: {metrics['total_word_counts'].get('Agent A', 0)}
- Rhetorical Questions: {metrics['rhetorical_questions'].get('Agent A', 0)}

#### Agent B
- Average Word Count: {metrics['average_word_counts'].get('Agent B', 0):.1f}
- Total Words: {metrics['total_word_counts'].get('Agent B', 0)}
- Rhetorical Questions: {metrics['rhetorical_questions'].get('Agent B', 0)}

### Judge Analysis
"""
        for vote in state["judge_votes"]:
            report += f"\n#### {vote.judge_id}\n"
            report += f"- Winner: {vote.winner} (Confidence: {vote.confidence:.2f})\n"
            report += f"- Reasoning: {vote.reasoning[:200]}...\n"

        return report
