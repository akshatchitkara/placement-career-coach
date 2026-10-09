# Decision Log

Decisions A1-A16 and open items D1-D6 are carried from the blueprint (`00_PROJECT_BLUEPRINT.md`, Appendix A/B). New decisions made during execution are appended below, numbered onward from A16.

| # | Decision | Reason | Source |
|---|---|---|---|
| A17 | AI provider (Anthropic / OpenAI / NVIDIA NIM / custom OpenAI-compatible) is configurable from a UI Settings page and stored in a new `ai_provider_settings` SQLite table, instead of `.env`-only | User requirement: switch providers at runtime without editing `.env` or restarting | Execution planning session, 2026-10-09 |
| A18 | Non-Anthropic providers share one adapter (`openai_compatible_ai_client.py`) keyed by a configurable `base_url`, rather than one adapter per vendor | OpenAI, NVIDIA NIM, and most other hosted LLM APIs expose the same `/chat/completions` shape; matches the blueprint's "one adapter, swappable" principle (Section 7.1) without adding N bespoke clients | Execution planning session, 2026-10-09 |
| A19 | Git initialized locally (not global) with identity `Akshat Chitkara <akshatchitkara1@gmail.com>` | No git identity was configured on this machine | Execution planning session, 2026-10-09 |
| A20 | Build proceeds on the locally available Python 3.14 rather than blueprint's specified 3.11 | No 3.11 interpreter installed on this machine; no 3.11-only feature is in use yet | M0 implementation, 2026-10-09 |

Open decisions D1-D6 (blueprint Appendix B) remain at their stated defaults unless revisited.
