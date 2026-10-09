import pytest

from pcc.content.content_loader import load_careers
from pcc.domain.career_resolver import resolve_career

CAREERS = load_careers()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("DevOps Engineer", "devops_engineer"),
        ("  devops  ", "devops_engineer"),
        ("SRE", "devops_engineer"),
        ("mean stack", "mean_stack_developer"),
        ("Java Developer", "java_backend_developer"),
        ("Machine Learning Engineer", "ai_developer"),
        ("I want to be a devops person", "devops_engineer"),
    ],
)
def test_matches_catalog_names_and_aliases(text, expected):
    result = resolve_career(text, CAREERS)
    assert result.status == "matched"
    assert result.career.career_id == expected


@pytest.mark.parametrize("text", ["Doctor", "Chartered Accountant", "Pilot", "Chef"])
def test_t19_non_cs_career_is_unsupported_with_supported_list(text):
    result = resolve_career(text, CAREERS)
    assert result.status == "unsupported"
    assert result.career is None
    assert "not supported yet" in result.message
    assert all(c.name in result.message for c in CAREERS)


@pytest.mark.parametrize("text", ["", "   ", "x" * 61, "devops <script>", "a; DROP TABLE profiles"])
def test_invalid_input_rejected(text):
    assert resolve_career(text, CAREERS).status == "invalid_input"
