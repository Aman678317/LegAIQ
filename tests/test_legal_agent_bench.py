"""Root-level test entry point for the Legal Agent Bench walkthrough."""

import unittest

from legal_agent_bench.legal_agent_bench.core import load_task, score


class LegalAgentBenchScoringTests(unittest.TestCase):
    def test_complete_answer_scores_100(self):
        _, task = load_task("lease-review-001")
        answer = " ".join(item["required_phrases"][0] for item in task["rubric"])
        response = {"summary": answer, "findings": [{"citations": ["lease.txt:1"]}]}
        self.assertEqual(score(task, response)["score"], 100.0)

    def test_answer_without_citations_does_not_pass(self):
        _, task = load_task("lease-review-001")
        answer = " ".join(item["required_phrases"][0] for item in task["rubric"])
        self.assertEqual(score(task, {"summary": answer, "findings": []})["score"], 0.0)
