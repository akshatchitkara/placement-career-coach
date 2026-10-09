from tests.conftest import ScriptedAiClient

from pcc.agents.roadmap_agent import generate_roadmap


def _run(template, ids, client):
    return generate_roadmap("DevOps Engineer", template, ids, client)


def test_no_ai_client_uses_template(devops_template, devops_skill_ids):
    result = _run(devops_template, devops_skill_ids, None)
    assert result.roadmap.generation_source == "template"
    assert not result.used_fallback


def test_t15_ai_unavailable_falls_back_to_template(
    devops_template, devops_skill_ids, unavailable_ai
):
    result = _run(devops_template, devops_skill_ids, unavailable_ai)
    assert result.roadmap.generation_source == "template"
    assert result.used_fallback and "unavailable" in result.message


def test_t16_empty_or_malformed_response_falls_back(devops_template, devops_skill_ids):
    for bad in ("", "{}", "not json", '{"months": "x"}', "[]"):
        result = _run(devops_template, devops_skill_ids, ScriptedAiClient(bad))
        assert result.roadmap == _run(devops_template, devops_skill_ids, None).roadmap
        assert result.used_fallback


def test_valid_personalisation_is_accepted(devops_template, devops_skill_ids, roadmap_response):
    def reword(months):
        months[0]["focus"] = "Hands-on Linux for deployment engineers"

    result = _run(devops_template, devops_skill_ids, ScriptedAiClient(roadmap_response(reword)))
    assert result.roadmap.generation_source == "ai_personalised"
    assert result.roadmap.months[0].focus == "Hands-on Linux for deployment engineers"
    assert result.roadmap.skill_ids_in_order() == devops_template.skill_ids_in_order()


def test_t10_ai_reordering_skills_is_rejected(devops_template, devops_skill_ids, roadmap_response):
    def swap(months):
        months[0]["skill_id"], months[1]["skill_id"] = months[1]["skill_id"], months[0]["skill_id"]

    client = ScriptedAiClient(roadmap_response(swap))
    result = _run(devops_template, devops_skill_ids, client)
    assert result.roadmap.generation_source == "template"
    assert result.used_fallback
    assert client.calls == 2  # first try + exactly one repair attempt


def test_t09_ai_dropping_a_month_is_rejected(devops_template, devops_skill_ids, roadmap_response):
    client = ScriptedAiClient(roadmap_response(lambda months: months.pop()))
    result = _run(devops_template, devops_skill_ids, client)
    assert result.roadmap.generation_source == "template"


def test_t14_url_from_ai_is_rejected(devops_template, devops_skill_ids, roadmap_response):
    def add_url(months):
        months[2]["deliverable"] = "Follow https://evil.example/tutorial"

    result = _run(devops_template, devops_skill_ids, ScriptedAiClient(roadmap_response(add_url)))
    assert result.roadmap.generation_source == "template"


def test_repair_attempt_can_succeed(devops_template, devops_skill_ids, roadmap_response):
    def swap(months):
        months[0]["skill_id"], months[1]["skill_id"] = months[1]["skill_id"], months[0]["skill_id"]

    client = ScriptedAiClient(roadmap_response(swap), roadmap_response())
    result = _run(devops_template, devops_skill_ids, client)
    assert result.roadmap.generation_source == "ai_personalised"
    assert client.calls == 2
