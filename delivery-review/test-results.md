# Test results

Run on 12 October 2026 on the developer's Windows machine (Python 3.14, Edge for the browser tests). Every number below comes from a run in this review.

| Suite | Command | Result |
|---|---|---|
| Unit, integration, headless UI | `pytest` | **483 passed, 35 skipped** (the 35 skipped are the browser tests, which need `PCC_E2E=1`) |
| Lint | `ruff check .` | clean |
| Type check | `mypy` (strict on `pcc.domain` and `pcc.workflow`) | clean (27 source files) |
| Content validation | `scripts/validate_content.py` | clean |
| Security scan | Bandit | two findings, both false positives (`bandit.txt`) |
| Dependencies | pip-audit | no known vulnerabilities |
| Real browser | `PCC_E2E=1 pytest tests/e2e` | **35 tests: 32 passed, 3 failed in the full run; the 3 passed when rerun on their own** |

## The browser run, stated exactly

The full run (`e2e-results.xml`) took 5 h 47 min instead of the usual few minutes. The machine was suspended or lost its network during it. One test spent 14,293 s in its body, another 5,779 s in setup. The three failures were:

1. `test_recheck_after_a_baseline_shows_improvement`: the page did not load within 30 s (`Page.goto` timeout), during the stall.
2. `test_the_full_path_check_reaches_industry_ready_in_the_browser`: the test treats any browser console error as a failure, and Chrome logged `ERR_NETWORK_CHANGED` while fetching an icon from Google Fonts, an effect of the network change.
3. `test_a_stale_second_tab_catches_up_after_the_check_was_submitted_elsewhere`: a 20 s wait for "Question 10 of 12" timed out (172 s test, run while the machine was slow).

I reran exactly those three, unchanged, and all passed (`e2e-results-rerun-failed.xml`, 3 passed in 149 s). So there is no single clean 35-test run on record; there is one run with three environment-affected failures and one run showing those three pass. The third failure is the one I cannot fully attribute to the environment, and it could be a timing weakness in the test or in the app under load. The first run also stalled (`e2e-results-run1-stalled.xml`).

## What the tests prove, and do not
- Proved: scoring and level thresholds on both sides of each boundary, all four careers, all four levels, the weakest-skill and roadmap agreement for 56 cases, AI failure fallbacks (seven modes), input handling, and the browser journey.
- Not proved: live AI output (only DevOps was checked live, earlier), behaviour on a phone or Safari/Firefox (only Edge/Chrome), load or many users, the quality of the questions.
- Coverage (98%) covers the scoring, weekly-plan and progress modules only.
