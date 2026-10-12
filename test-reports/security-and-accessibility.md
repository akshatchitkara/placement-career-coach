# Security and accessibility findings

Local testing only, against the app running on this machine with throwaway databases. Nothing was sent to a live AI provider and no real secret was used.

## Security

### Tools run

| Check | Result |
|---|---|
| Bandit on `src`, `scripts` and `qa` | No high-severity findings. App code: 2 low (B311, `random` used for a seeded question shuffle, not for security: false positive). Test tooling: 1 medium (B314, parses this project's own JUnit file) and 1 low (try/except/pass in a QA script). Before the fixes the app code also had 4 low `assert` findings; they are now explicit errors |
| pip-audit on `requirements.txt` | No known vulnerabilities |
| Secret scan | No `sk-ant-` or `nvapi-` strings in tracked files. The local database (`data/runtime/pcc.db`) holds the saved AI key by design and is git-ignored |
| SQL injection | Every query is parameterised. A browser test enters `Robert'); DROP TABLE profiles;--` as a name and as a career; the table survives and the text is stored literally |
| Cross-site scripting | A display name of `<img src=x onerror="window.__xss=1"><script>…</script>` is shown as text and nothing runs (browser test). Pages that use raw HTML escape every value they insert |
| Free-text career input | Limited to 60 characters from an allow-list; markup and SQL are rejected with a clear message |
| Path traversal | Content files are read by career ids taken from the catalog, never from text the student typed |
| Authentication and authorisation | **Not applicable:** the app has no login and one role. A profile is a display name. What can be checked is isolation between profiles for the new features, and that is enforced and tested: another profile cannot read or write a check draft |

### Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| S1 | Medium | The AI Settings page sent the **saved API key back to the browser** on every page draw (as the value of the password box) | **Fixed.** The box now starts empty with "A key is saved; leave blank to keep it". A blank box reuses the saved key. Tested |
| S2 | Medium | A provider error shown after "Test connection" could **echo the key** (some providers quote it in a 401 message) | **Fixed.** The key is replaced by `***` in the message. Tested |
| S3 | Low | A display name was rendered as Markdown, so a name such as `[free prize](http://…)` became a **clickable link**. Escaping the characters was not enough: Streamlit still auto-links a bare address. This was caught by a real-browser test, not by the unit tests | **Fixed.** Names are escaped and an invisible zero-width space breaks web and e-mail address patterns. Tested in a browser |
| S4 | Low | Four `assert` statements were used to narrow types; they disappear under `python -O` | **Fixed.** Explicit errors |
| S5 | Low | A database connection on the AI Settings page could stay open if the page failed | **Fixed.** `closing(...)`; a `ResourceWarning` in the test run is gone |
| S6 | Accepted | The AI key is stored in plain text in the local SQLite file | Documented in the README as acceptable for a single-user local prototype and not for a shared deployment. Recommendation: use the operating system's credential store or an environment variable if this is ever deployed |
| S7 | Accepted | "Test connection" sends a request to whatever base URL the operator types (server-side request forgery risk in a shared deployment) | Not a risk for a single local user, who is the operator. Would need an allow-list if the app were hosted |
| S8 | Info | Python 3.14 on Windows: the Streamlit server process crashed twice with `Fatal Python error: _PySemaphore_Wakeup: parking_lot: ReleaseSemaphore failed`, with the stack in Streamlit's file-watcher threads (`watchdog`) | **Mitigated.** `.streamlit/config.toml` now sets `fileWatcherType = "none"`. Before the change 2 of about 5 full browser runs lost the server; in the 4 full runs after it none did. That is evidence, not proof of the cause. The crash is in the interpreter and is not specific to this app; using Python 3.12 or 3.13 is untested here |

### Not tested

Penetration testing beyond input fuzzing; denial of service and load; a hosted multi-user deployment (the app is built for one local user); dependency review of the npm tooling (used only for testing, not shipped).

## Accessibility

Measured with axe-core 4.14.0 on every page at three sizes (browser tests and the route sweep) and with Lighthouse.

### Fixed in this pass

| # | Severity | Finding | Fix |
|---|---|---|---|
| A1 | Serious | Colour contrast below 4.5:1 on captions, the signed-in line, step labels, difficulty badges, success banners and metric changes (several were Streamlit defaults) | Darker caption, alert and metric-change colours; the badges replaced by pills with 8:1 contrast or better (captions 6.2 to 6.7:1, alert text 13.5:1) |
| A2 | Moderate | Heading levels jumped from h1 to h3 (and h4 on Home) | Section titles are now h2 |
| A3 | Serious | The score trend chart scrolls sideways on a phone but could not be reached with the keyboard | The chart region is focusable and labelled |
| A4 | Moderate | Every page had the same browser-tab title | Each page has its own ("Roadmap · Placement Career Coach") |

### Remaining findings, all caused by Streamlit itself

| Rule | Impact | Where | Why it is not ours |
|---|---|---|---|
| aria-allowed-attr | critical | the sidebar element | Also reported on a minimal Streamlit app with none of this project's code |
| region | moderate | sidebar and page content | Same minimal app |
| list, listitem | serious | the sidebar navigation | Appear when navigation is **grouped into sections** (Plan, Assess, Improve, Account): Streamlit puts a `div` inside the `ul`. Confirmed on a minimal app with sectioned navigation. **Trade-off:** the grouping was an approved design choice. A flat list of ten links would remove these two findings; the decision is yours |

The browser accessibility test asserts there are no critical or serious findings **other than** these four rules inside the sidebar, so a new problem anywhere else fails the build.

### Lighthouse accessibility

83 to 87 on every page. The points lost are exactly the framework findings above. See `lighthouse/summary.md`.

### Not tested

Manual testing with a screen reader (NVDA, VoiceOver) and a full keyboard-only walkthrough: automated tools find only part of what a person would. Dark mode (the app has one light theme). Reduced-motion and zoom to 200%.
