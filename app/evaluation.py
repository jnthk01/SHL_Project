"""
Evaluation module for SHL Assessment Recommender.
Measures retrieval quality, recommendation relevance, groundedness, and response accuracy.
"""

import json
from typing import Dict, List, Tuple
from app.catalog import CatalogManager, load_catalog
from app.agent import create_agent
from app.models import Message


class Evaluator:
    """Evaluates agent performance across multiple dimensions."""

    def __init__(self):
        self.catalog = load_catalog()
        self.catalog_manager = CatalogManager()
        self.agent = create_agent(self.catalog_manager)

    def evaluate_retrieval_quality(self, queries: List[str]) -> Dict:
        """Measure retrieval quality - does search return relevant results?"""
        results = []
        for query in queries:
            retrieved = self.catalog_manager.search(query)
            # Quality = % of results that contain query keywords
            if retrieved:
                query_lower = query.lower()
                relevant = sum(1 for r in retrieved if query_lower in r.get("name", "").lower())
                precision = relevant / len(retrieved) if retrieved else 0
                results.append({
                    "query": query,
                    "retrieved": len(retrieved),
                    "relevant": relevant,
                    "precision": precision
                })
        avg_precision = sum(r["precision"] for r in results) / len(results) if results else 0
        return {"retrieval_precision": avg_precision, "details": results}

    def evaluate_recommendation_relevance(self, test_cases: List[Dict]) -> Dict:
        """Measure recommendation relevance - do recommendations match user needs?"""
        results = []
        for case in test_cases:
            messages = [Message(role="user", content=case["query"])]
            response = self.agent.process(messages)

            # Relevance = recommendations contain role/skill keywords from query
            query_keywords = set(case["query"].lower().split())
            relevant_count = 0
            for rec in response.recommendations:
                rec_text = (rec.name + " " + rec.name).lower()
                if any(kw in rec_text for kw in case.get("expected_keywords", [])):
                    relevant_count += 1

            relevance = relevant_count / len(response.recommendations) if response.recommendations else 0
            results.append({
                "query": case["query"],
                "recommendations_count": len(response.recommendations),
                "relevant_count": relevant_count,
                "relevance": relevance
            })
        avg_relevance = sum(r["relevance"] for r in results) / len(results) if results else 0
        return {"recommendation_relevance": avg_relevance, "details": results}

    def evaluate_groundedness(self, queries: List[str]) -> Dict:
        """Measure groundedness - do recommendations exist in catalog?"""
        results = []
        catalog_names = {r.get("name", "").lower() for r in self.catalog}

        for query in queries:
            messages = [Message(role="user", content=query)]
            response = self.agent.process(messages)

            grounded = 0
            for rec in response.recommendations:
                # Check if name exists in catalog (fuzzy match)
                rec_lower = rec.name.lower()
                if any(cat_name in rec_lower or rec_lower in cat_name for cat_name in catalog_names):
                    grounded += 1

            groundedness = grounded / len(response.recommendations) if response.recommendations else 1.0
            results.append({
                "query": query,
                "total": len(response.recommendations),
                "grounded": grounded,
                "groundedness": groundedness
            })
        avg_groundedness = sum(r["groundedness"] for r in results) / len(results) if results else 1.0
        return {"groundedness": avg_groundedness, "details": results}

    def evaluate_response_accuracy(self, test_cases: List[Dict]) -> Dict:
        """Measure response accuracy - does behavior match expected?"""
        results = []
        for case in test_cases:
            messages = [Message(role="user", content=case["query"])]
            response = self.agent.process(messages)

            # Check expected behavior
            expected_behavior = case.get("behavior", "recommend")
            correct = False

            if expected_behavior == "clarify":
                correct = len(response.recommendations) == 0 and "?" in response.reply
            elif expected_behavior == "recommend":
                correct = len(response.recommendations) > 0
            elif expected_behavior == "compare":
                correct = "vs" in response.reply.lower() or "compare" in response.reply.lower()
            elif expected_behavior == "refuse":
                correct = "specialize" in response.reply.lower() or "only provide" in response.reply.lower()

            results.append({
                "query": case["query"],
                "expected": expected_behavior,
                "correct": correct
            })
        accuracy = sum(r["correct"] for r in results) / len(results) if results else 0
        return {"response_accuracy": accuracy, "details": results}

    def run_full_evaluation(self) -> Dict:
        """Run all evaluations and return summary."""
        # Test queries for retrieval
        retrieval_queries = [
            "Java developer",
            "Python programming",
            "Data analyst",
            "Project manager",
            "Customer service"
        ]

        # Test cases for relevance
        relevance_cases = [
            {"query": "Java developer test", "expected_keywords": ["java"]},
            {"query": "Python coding assessment", "expected_keywords": ["python"]},
            {"query": "Data analyst cognitive test", "expected_keywords": ["data", "cognitive"]}
        ]

        # Test cases for groundedness
        groundedness_queries = [
            "Java developer",
            "OPQ personality",
            "Data analyst assessment"
        ]

        # Test cases for accuracy
        accuracy_cases = [
            {"query": "What role are you hiring for?", "behavior": "clarify"},
            {"query": "Java developer assessment", "behavior": "recommend"},
            {"query": "Compare OPQ vs GSA", "behavior": "compare"},
            {"query": "What's the salary?", "behavior": "refuse"}
        ]

        return {
            "retrieval_quality": self.evaluate_retrieval_quality(retrieval_queries),
            "recommendation_relevance": self.evaluate_recommendation_relevance(relevance_cases),
            "groundedness": self.evaluate_groundedness(groundedness_queries),
            "response_accuracy": self.evaluate_response_accuracy(accuracy_cases)
        }


def run_evaluation():
    """Run evaluation and print results."""
    evaluator = Evaluator()
    results = evaluator.run_full_evaluation()

    print("=" * 60)
    print("SHL ASSESSMENT RECOMMENDER EVALUATION")
    print("=" * 60)

    for metric, data in results.items():
        print(f"\n{metric.upper().replace('_', ' ')}:")
        print(f"  Score: {data.get(list(data.keys())[0], 'N/A'):.2%}")
        if metric == "response_accuracy":
            for detail in data["details"]:
                print(f"    - {detail['query'][:40]}: {'✓' if detail['correct'] else '✗'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_evaluation()