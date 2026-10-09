# Decision Log

Decisions A1-A16 and open items D1-D6 are carried from the blueprint (`00_PROJECT_BLUEPRINT.md`, Appendix A/B). New decisions made during execution are appended below, numbered onward from A16.

| # | Decision | Reason | Source |
|---|---|---|---|
| A17 | AI provider (Anthropic / OpenAI / NVIDIA NIM / custom OpenAI-compatible) is configurable from a UI Settings page and stored in a new `ai_provider_settings` SQLite table, instead of `.env`-only | User requirement: switch providers at runtime without editing `.env` or restarting | Execution planning session, 2026-10-09 |
| A18 | Non-Anthropic providers share one adapter (`openai_compatible_ai_client.py`) keyed by a configurable `base_url`, rather than one adapter per vendor | OpenAI, NVIDIA NIM, and most other hosted LLM APIs expose the same `/chat/completions` shape; matches the blueprint's "one adapter, swappable" principle (Section 7.1) without adding N bespoke clients | Execution planning session, 2026-10-09 |
| A19 | Git initialized locally (not global) with identity `Akshat Chitkara <akshatchitkara1@gmail.com>` | No git identity was configured on this machine | Execution planning session, 2026-10-09 |
| A20 | Build proceeds on the locally available Python 3.14 rather than blueprint's specified 3.11 | No 3.11 interpreter installed on this machine; no 3.11-only feature is in use yet | M0 implementation, 2026-10-09 |
| A21 | `AnthropicAiClient.generate()` no longer passes `temperature` to `Messages.create()`; the parameter stays on the `AiClient` interface as a documented no-op for this provider | The installed `anthropic==1.13.0` SDK removed `temperature` from that call entirely (confirmed via `inspect.signature` and a full source grep, not a version-pin issue) -- passing it crashed every live Anthropic call with a `TypeError` | M0 full test pass, 2026-10-09 |
| A22 | `Skill.career_id: str` was changed to `Skill.career_ids: list[str]` before any M1 content was authored | The blueprint's own skill maps (Section 2.3) reuse `git_version_control` (DevOps/MEAN/AI), `system_design_basics` (MEAN/Java), and `interview_preparation` (all four careers) across multiple roadmaps. A single-career field would force either duplicate skill_ids (rejected by the content validator's uniqueness rule) or duplicate skill definitions for the same skill | M1 implementation, 2026-10-09 |
| A23 | Added `Career.aliases` (careers.json) and `domain/career_resolver.py` for typed career input | FR-17/T-19 need free-text input matched to the catalog without AI; aliases keep the matching data-driven | M2 implementation, 2026-10-09 |
| A24 | In mock mode the roadmap agent skips the AI call and uses the template | Mock returns no roadmap, so calling it would only burn a repair attempt; result is identical and deterministic | M2 implementation, 2026-10-09 |
| A25 | Career re-selection is allowed from `ROADMAP_READY` (back to `CAREER_SELECTED`) until the first check starts | Lets a student change their mind in M2 without orphaning attempts; later states do not allow it | M2 implementation, 2026-10-09 |

Open decisions D1-D6 (blueprint Appendix B) remain at their stated defaults unless revisited.
