"""Unit tests for the deterministic check operators."""

from legal_agent_bench.checks import evaluate_check


def test_contains_any_matches_case_and_whitespace_insensitive():
    result = evaluate_check({"contains_any": ["$42,000.00", "$42,000"]}, "monthly rent of  usd $42,000.00  plus tax")
    assert result.passed and "42,000" in result.reason


def test_contains_any_misses_when_phrase_absent():
    assert not evaluate_check({"contains_any": ["$50,000"]}, "rent is $42,000").passed


def test_contains_all_requires_every_phrase():
    ok = evaluate_check({"contains_all": ["nine (9) months", "renewal"]}, "renewal needs nine (9) months notice")
    missing = evaluate_check({"contains_all": ["nine (9) months", "deposit"]}, "renewal needs nine (9) months notice")
    assert ok.passed and not missing.passed and "deposit" in missing.reason


def test_not_contains_any():
    assert evaluate_check({"not_contains_any": ["as-is"]}, "clean draft").passed
    result = evaluate_check({"not_contains_any": ["as-is"]}, "sold as-is")
    assert not result.passed


def test_regex_operator():
    assert evaluate_check({"regex": r"\b1,700,000\b"}, "total is 1,700,000 shares").passed
    assert not evaluate_check({"regex": r"\b1,700,000\b"}, "total is 1700000 shares").passed


def test_max_words_operator():
    assert evaluate_check({"max_words": 5}, "one two three four five").passed
    assert not evaluate_check({"max_words": 5}, "one two three four five six").passed


def test_composite_all_any_none():
    spec = {"all": [{"contains_any": ["missing", "unsigned"]}, {"contains_any": ["CFO"]}]}
    assert evaluate_check(spec, "the CFO signature page is unsigned").passed
    assert not evaluate_check(spec, "the CEO signature page is unsigned").passed
    assert not evaluate_check(spec, "the CFO agreement is fine").passed

    assert evaluate_check({"any": [{"contains_any": ["x"]}, {"contains_any": ["y"]}]}, "has y").passed
    assert evaluate_check({"none": [{"contains_any": ["forbidden"]}]}, "nothing bad").passed


def test_unknown_operator_and_bad_spec_fail_closed():
    assert not evaluate_check({"contains_everything": []}, "text").passed
    assert not evaluate_check({"contains_any": ["a"], "regex": "b"}, "a").passed  # two operators
    assert not evaluate_check({"regex": "("}, "text").passed  # invalid regex -> fail closed
