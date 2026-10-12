# Functional test results

34 browser tests: **34 passed**, **0 failed**, 0 skipped. Generated from pytest JUnit XML; each row is one test.

## Skills check, coach and weekly plan behaviour (browser)

| Test | Result | Seconds | Note |
|---|---|---|---|
| `test_wizard_counts_progress_keeps_answers_and_lists_the_unanswered` | pass | 22.1 |  |
| `test_a_stale_second_tab_catches_up_after_the_check_was_submitted_elsewhere` | pass | 65.0 |  |
| `test_reload_in_the_middle_of_a_check_resumes_the_same_attempt` | pass | 15.8 |  |
| `test_answers_given_before_a_reload_are_not_lost` | pass | 16.3 |  |
| `test_coach_chat_quiz_and_limits` | pass | 27.9 |  |
| `test_weekly_plan_ticks_budget_calendar_and_links` | pass | 27.5 |  |

## Whole student journeys, checked against the database (browser)

| Test | Result | Seconds | Note |
|---|---|---|---|
| `test_full_journey[devops_engineer-3-12]` | pass | 31.2 |  |
| `test_full_journey[mean_stack_developer-4-12]` | pass | 26.0 |  |
| `test_full_journey[java_backend_developer-5-12]` | pass | 25.5 |  |
| `test_full_journey[ai_developer-6-6]` | pass | 26.8 |  |
| `test_weak_result_leads_to_coaching_weekly_plan_and_progress` | pass | 27.4 |  |
| `test_recheck_after_a_baseline_shows_improvement` | pass | 35.7 |  |

## Every question displayed exactly as written (browser)

| Test | Result | Seconds | Note |
|---|---|---|---|
| `test_every_question_stem_and_option_is_displayed_exactly_as_written` | pass | 12.4 |  |

## Responsive layout and accessibility (browser)

| Test | Result | Seconds | Note |
|---|---|---|---|
| `test_no_sideways_scrolling_and_no_serious_accessibility_violations` | pass | 91.6 |  |

## Routes, hidden pages and hostile or invalid input (browser)

| Test | Result | Seconds | Note |
|---|---|---|---|
| `test_every_route_loads_without_errors[]` | pass | 5.4 |  |
| `test_every_route_loads_without_errors[profile]` | pass | 2.2 |  |
| `test_every_route_loads_without_errors[career]` | pass | 2.2 |  |
| `test_every_route_loads_without_errors[roadmap]` | pass | 2.2 |  |
| `test_every_route_loads_without_errors[assessment]` | pass | 2.3 |  |
| `test_every_route_loads_without_errors[results]` | pass | 2.2 |  |
| `test_every_route_loads_without_errors[coaching]` | pass | 2.3 |  |
| `test_every_route_loads_without_errors[weekly-plan]` | pass | 2.3 |  |
| `test_every_route_loads_without_errors[progress]` | pass | 2.3 |  |
| `test_every_route_loads_without_errors[ai-settings]` | pass | 2.3 |  |
| `test_unknown_route_does_not_break_the_app` | pass | 2.3 |  |
| `test_the_developer_page_is_hidden_by_default` | pass | 2.3 |  |
| `test_blank_display_name_is_refused_with_a_clear_message` | pass | 3.8 |  |
| `test_a_very_long_display_name_is_cut_to_the_limit` | pass | 3.8 |  |
| `test_unicode_display_name_works` | pass | 5.6 |  |
| `test_html_in_a_display_name_is_shown_as_text_and_never_runs` | pass | 8.7 |  |
| `test_sql_in_a_display_name_is_stored_as_plain_text` | pass | 8.7 |  |
| `test_free_text_career_cases` | pass | 26.4 |  |
| `test_changing_career_after_a_roadmap_is_blocked_with_a_clear_message` | pass | 13.9 |  |
| `test_a_display_name_that_looks_like_a_link_is_not_a_link` | pass | 7.2 |  |

## Route sweep: every route, signed out and signed in, at three sizes

Each cell is one page view in a real browser (Edge) at phone (390 px), tablet (820 px) and desktop (1440 px) width. A view is **ok** when it showed no error text, scrolled sideways by no more than 1 px, logged no console error other than the known Streamlit deep-link 404s, and raised no uncaught page error. The accessibility column counts axe-core findings other than Streamlit's own four (see security-and-accessibility.md); screenshots are in `data/screenshots/`.

| Route | Signed out (phone / tablet / desktop) | Signed in (phone / tablet / desktop) | Tab title |
|---|---|---|---|
| `(root)` | ok / ok / ok | ok / ok / ok | Placement Career Coach |
| `home` | ok / ok / ok | ok / ok / ok | Placement Career Coach |
| `profile` | ok / ok / ok | ok / ok / ok | Profile · Placement Career Coach |
| `career` | ok / ok / ok | ok / ok / ok | Career & Semester · Placement Career Coach |
| `roadmap` | ok / ok / ok | ok / ok / ok | Roadmap · Placement Career Coach |
| `assessment` | ok / ok / ok | ok / ok / ok | Skills Check · Placement Career Coach |
| `results` | ok / ok / ok | ok / ok / ok | Results · Placement Career Coach |
| `coaching` | ok / ok / ok | ok / ok / ok | Coaching Plan · Placement Career Coach |
| `weekly-plan` | ok / ok / ok | ok / ok / ok | Weekly Plan · Placement Career Coach |
| `progress` | ok / ok / ok | ok / ok / ok | Progress · Placement Career Coach |
| `ai-settings` | ok / ok / ok | ok / ok / ok | AI Settings · Placement Career Coach |
| `m1-preview` | ok / ok / ok | ok / ok / ok | Placement Career Coach (Hidden by default: shows the home page, no M1 link) |
| `does-not-exist` | ok / ok / ok | ok / ok / ok | Placement Career Coach (Falls back to the home page) |

**78 of 78 page views ok.**
