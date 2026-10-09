"""Roadmap fallback: the curated template, always available for the launch careers."""

from pcc.domain.schemas.roadmap_schemas import Roadmap


def template_roadmap(template: Roadmap) -> Roadmap:
    return template.model_copy(update={"generation_source": "template"}, deep=True)
