# main.py
import os
import json
from datetime import datetime
from typing import List, Dict
import networkx as nx
import matplotlib.pyplot as plt

from graph.workflow import DebateWorkflow
from graph.state import DebateState
from utils.metrics import MetricsCollector

class DebateSystem:
    """Main system for running multiple debates"""
    
    TOPICS = [
        "communism_vs_imperialism",
        "modern_vs_traditional_medicine", 
        "open_vs_regulated_ai",
        "growth_vs_environment",
        "religion_vs_secularism"
    ]
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
        
    def run_all_debates(self):
        """Runs all configured debates"""
        for topic in self.TOPICS:
            print(f"\n{'='*60}")
            print(f"Starting debate on: {topic}")
            print(f"{'='*60}\n")
            
            # Create topic directory
            topic_dir = os.path.join(self.output_dir, topic)
            os.makedirs(topic_dir, exist_ok=True)
            
            # Run debate
            workflow = DebateWorkflow(topic)
            state = workflow.run()
            
            # Save results
            self._save_debate_results(state, topic_dir)
            
            # Generate visualizations
            self._generate_visualizations(workflow, state, topic_dir)
            
            # Collect results
            self.results.append({
                'topic': topic,
                'winner': state['final_winner'],
                'judge_agreement': state['metrics']['judge_agreement'],
                'total_turns': state['metrics']['total_turns']
            })
            
            print(f"\nDebate completed. Winner: {state['final_winner']}")
            
        # Generate summary report
        self._generate_summary_report()
        
    def _save_debate_results(self, state: DebateState, output_dir: str):
        """Saves debate transcript and analysis"""
        # Save full transcript
        transcript_path = os.path.join(output_dir, "transcript.txt")
        with open(transcript_path, 'w') as f:
            f.write(f"DEBATE TOPIC: {state['topic']}\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write(f"Final Winner: {state['final_winner']}\n\n")
            
            f.write("="*80 + "\n")
            f.write("DEBATE TRANSCRIPT\n")
            f.write("="*80 + "\n\n")
            
            for msg in state['messages']:
                f.write(f"Turn {msg.turn} - {msg.agent} ({msg.message_type}):\n")
                f.write(f"{msg.content}\n")
                f.write("-"*40 + "\n\n")
                
        # Save judge analysis
        judges_path = os.path.join(output_dir, "judge_analysis.json")
        judge_data = []
        for vote in state['judge_votes']:
            judge_data.append({
                'judge_id': vote.judge_id,
                'winner': vote.winner,
                'confidence': vote.confidence,
                'reasoning': vote.reasoning,
                'criteria_scores': vote.criteria_scores
            })
            
        with open(judges_path, 'w') as f:
            json.dump(judge_data, f, indent=2, ensure_ascii=False)
            
        # Save metrics
        metrics_path = os.path.join(output_dir, "metrics.json")
        with open(metrics_path, 'w') as f:
            json.dump(state['metrics'], f, indent=2, ensure_ascii=False)
            
        # Generate metrics report
        metrics_collector = MetricsCollector()
        report = metrics_collector.generate_metrics_report(state, output_dir)
        
        report_path = os.path.join(output_dir, "metrics_report.md")
        with open(report_path, 'w') as f:
            f.write(report)
            
    def _generate_visualizations(self, workflow: DebateWorkflow, state: DebateState, output_dir: str):
        """Generates workflow and debate visualizations"""
        # 1. Workflow graph
        self._visualize_workflow(workflow, output_dir)
        
        # 2. Debate flow diagram
        self._visualize_debate_flow(state, output_dir)
        
    def _visualize_workflow(self, workflow: DebateWorkflow, output_dir: str):
        """Creates a visual representation of the LangGraph workflow"""
        G = nx.DiGraph()
        
        # Add nodes
        nodes = [
            ("Start", {"color": "green"}),
            ("Agent A Turn", {"color": "lightblue"}),
            ("Agent B Turn", {"color": "lightcoral"}),
            ("Judge Evaluation", {"color": "yellow"}),
            ("Final Decision", {"color": "orange"}),
            ("End", {"color": "red"})
        ]
        
        for node, attrs in nodes:
            G.add_node(node, **attrs)
            
        # Add edges
        edges = [
            ("Start", "Agent A Turn"),
            ("Agent A Turn", "Agent B Turn", {"label": "continue"}),
            ("Agent B Turn", "Agent A Turn", {"label": "continue"}),
            ("Agent A Turn", "Judge Evaluation", {"label": "complete"}),
            ("Agent B Turn", "Judge Evaluation", {"label": "complete"}),
            ("Judge Evaluation", "Final Decision"),
            ("Final Decision", "End")
        ]
        
        for edge in edges:
            if len(edge) == 3:
                G.add_edge(edge[0], edge[1], **edge[2])
            else:
                G.add_edge(edge[0], edge[1])
                
        # Draw graph
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Draw nodes
        node_colors = [G.nodes[node].get('color', 'lightgray') for node in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000)
        
        # Draw edges and labels
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, arrowstyle='->')
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # Draw edge labels
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels)
        
        plt.title("Debate Workflow Structure", fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "workflow_graph.png"))
        plt.close()
        
    def _visualize_debate_flow(self, state: DebateState, output_dir: str):
        """Creates a visual flow of the actual debate"""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Prepare data
        turns = []
        for msg in state['messages']:
            turns.append({
                'turn': msg.turn,
                'agent': msg.agent,
                'type': msg.message_type,
                'preview': msg.content[:100] + "..."
            })
            
        # Create timeline
        y_positions = {"Agent A": 0.7, "Agent B": 0.3}
        colors = {"Agent A": "blue", "Agent B": "red"}
        
        for turn in turns:
            y = y_positions[turn['agent']]
            color = colors[turn['agent']]
            
            # Draw message box
            ax.text(turn['turn'], y, f"{turn['type']}\n{turn['preview']}", 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3),
                   fontsize=8, ha='center', va='center')
            
            # Draw connection lines
            if turn['turn'] > 1:
                prev_agent = "Agent B" if turn['agent'] == "Agent A" else "Agent A"
                ax.plot([turn['turn']-1, turn['turn']], 
                       [y_positions[prev_agent], y], 
                       'k--', alpha=0.3)
                       
        # Add judge evaluation
        judge_y = 0.5
        for i, vote in enumerate(state['judge_votes']):
            ax.text(11 + i*0.3, judge_y, f"{vote.judge_id}\n→{vote.winner}", 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5),
                   fontsize=8, ha='center', va='center')
                   
        # Final winner
        ax.text(12, 0.5, f"WINNER:\n{state['final_winner']}", 
               bbox=dict(boxstyle="round,pad=0.5", facecolor="green", alpha=0.5),
               fontsize=12, ha='center', va='center', weight='bold')
               
        ax.set_xlim(0.5, 12.5)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Turn", fontsize=12)
        ax.set_title(f"Debate Flow: {state['topic']}", fontsize=14)
        ax.set_yticks([0.3, 0.7])
        ax.set_yticklabels(["Agent B", "Agent A"])
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "debate_flow.png"))
        plt.close()
        
    def _generate_summary_report(self):
        """Generates a summary report across all debates"""
        report = f"""
# Multi-Agent Debate System - Summary Report
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Overall Results

| Topic | Winner | Judge Agreement | Total Turns |
|-------|--------|----------------|-------------|
"""
        
        for result in self.results:
            report += f"| {result['topic']} | {result['winner']} | {result['judge_agreement']*100:.1f}% | {result['total_turns']} |\n"
            
        # Win statistics
        agent_a_wins = sum(1 for r in self.results if r['winner'] == 'Agent A')
        agent_b_wins = sum(1 for r in self.results if r['winner'] == 'Agent B')
        
        report += f"""
### Win Statistics
- Agent A Wins: {agent_a_wins} ({agent_a_wins/len(self.results)*100:.1f}%)
- Agent B Wins: {agent_b_wins} ({agent_b_wins/len(self.results)*100:.1f}%)

### Average Judge Agreement: {sum(r['judge_agreement'] for r in self.results)/len(self.results)*100:.1f}%
"""
        
        summary_path = os.path.join(self.output_dir, "summary_report.md")
        with open(summary_path, 'w') as f:
            f.write(report)
            
        print(f"\nSummary report saved to: {summary_path}")

if __name__ == "__main__":
    # Run all debates
    system = DebateSystem()
    system.run_all_debates()
    
    print("\n" + "="*60)
    print("All debates completed successfully!")
    print(f"Results saved to: {system.output_dir}")
    print("="*60)