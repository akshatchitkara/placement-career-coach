from pcc.agents.validators.roadmap_validator import validate_roadmap


def _rules(errors: list[str]) -> set[str]:
    return {e.split(":")[0] for e in errors}


def test_template_passes(devops_template, devops_skill_ids):
    assert validate_roadmap(devops_template, devops_template, devops_skill_ids) == []


def test_t09_missing_month_rejected(devops_template, devops_skill_ids):
    short = devops_template.model_copy(update={"months": devops_template.months[:-1]})
    assert "V-RM-02" in _rules(validate_roadmap(short, devops_template, devops_skill_ids))


def test_t09_missing_semester_rejected(devops_template, devops_skill_ids):
    months = [m for m in devops_template.months if m.semester != 6]
    broken = devops_template.model_copy(update={"months": months})
    assert "V-RM-01" in _rules(validate_roadmap(broken, devops_template, devops_skill_ids))


def test_t10_reordered_skills_rejected(devops_template, devops_skill_ids):
    months = [m.model_copy() for m in devops_template.months]
    months[0], months[1] = (
        months[0].model_copy(update={"skill_id": months[1].skill_id}),
        months[1].model_copy(update={"skill_id": months[0].skill_id}),
    )
    swapped = devops_template.model_copy(update={"months": months})
    assert "V-RM-04" in _rules(validate_roadmap(swapped, devops_template, devops_skill_ids))


def test_unknown_skill_rejected(devops_template, devops_skill_ids):
    months = list(devops_template.months)
    months[0] = months[0].model_copy(update={"skill_id": "made_up_skill"})
    broken = devops_template.model_copy(update={"months": months})
    assert "V-RM-03" in _rules(validate_roadmap(broken, devops_template, devops_skill_ids))


def test_duplicate_skill_rejected(devops_template, devops_skill_ids):
    months = list(devops_template.months)
    months[1] = months[1].model_copy(update={"skill_id": months[0].skill_id})
    broken = devops_template.model_copy(update={"months": months})
    assert "V-RM-05" in _rules(validate_roadmap(broken, devops_template, devops_skill_ids))


def test_url_in_ai_field_rejected(devops_template, devops_skill_ids):
    months = list(devops_template.months)
    months[0] = months[0].model_copy(update={"deliverable": "Read https://example.com/guide"})
    broken = devops_template.model_copy(update={"months": months})
    assert "V-RM-08" in _rules(validate_roadmap(broken, devops_template, devops_skill_ids))


def test_blank_focus_rejected(devops_template, devops_skill_ids):
    months = list(devops_template.months)
    months[0] = months[0].model_copy(update={"focus": "  "})
    broken = devops_template.model_copy(update={"months": months})
    assert "V-RM-07" in _rules(validate_roadmap(broken, devops_template, devops_skill_ids))
