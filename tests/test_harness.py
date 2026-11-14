"""Fast checks on the eval harness (no LLM calls)."""

from migrate_agent.harness import load_cases, run_tests


def test_cases_load():
    cases = load_cases()
    assert len(cases) >= 10
    for c in cases:
        assert c.before.exists() and c.reference.exists() and c.test.exists()


def test_reference_passes_and_before_fails_for_first_case():
    case = load_cases()[0]
    assert run_tests(case, case.reference.read_text()).passed
    assert not run_tests(case, case.before.read_text()).passed
