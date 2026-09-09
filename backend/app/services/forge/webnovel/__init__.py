"""Webnovel Style Engine: Korean-webnovel identity as data, prompts and measurement.

- ``templates``   — subgenre templates (regression, hunter, tower, villainess…) that make a
                    blank Create Novel form still yield a genre-correct webnovel.
- ``detect``      — derive platform/subgenre/conventions from the source fingerprint + brief.
- ``render``      — prompt blocks for drafting, planning, critic and polish.
- ``conformance`` — deterministic per-chapter scorecard against the profile.
- ``service``     — persistence (singleton cards) and author directives.
"""

from app.services.forge.webnovel.conformance import measure_conformance
from app.services.forge.webnovel.detect import detect_profile
from app.services.forge.webnovel.render import render_for_critic, render_for_drafting, render_for_planning
from app.services.forge.webnovel.service import DirectiveService, WebnovelStyleService
from app.services.forge.webnovel.templates import SUBGENRE_TEMPLATES, template_for

__all__ = [
    "SUBGENRE_TEMPLATES", "DirectiveService", "WebnovelStyleService", "detect_profile", "measure_conformance",
    "render_for_critic", "render_for_drafting", "render_for_planning", "template_for",
]
