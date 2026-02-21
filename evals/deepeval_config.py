from deepeval import evaluate
from deepeval.metrics import CorrectnessMetric, HallucinationMetric, RelevanceMetric
from deepeval.test_case import LLMTestCase

class EvalConfig:
    def __init__(self, correctness_threshold=0.8, hallucination_threshold=0.3):
        self.correctness = CorrectnessMetric(threshold=correctness_threshold)
        self.hallucination = HallucinationMetric(threshold=hallucination_threshold)
        self.relevance = RelevanceMetric(threshold=0.7)

    def evaluate(self, prompt, actual_output, expected_output=None):
        test_case = LLMTestCase(
            input=prompt,
            actual_output=actual_output,
            expected_output=expected_output
        )
        return evaluate(test_case, [self.correctness, self.hallucination])

def run_evals(test_cases):
    results = []
    config = EvalConfig()
    for tc in test_cases:
        result = config.evaluate(tc["prompt"], tc["output"], tc.get("expected"))
        results.append(result)
    return results
