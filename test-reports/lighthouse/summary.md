# Lighthouse results

Lighthouse 13.5 (Chrome, headless) against the app running locally with seeded demo data, so every page shows a signed-in student. Mobile uses Lighthouse's default simulated slow-4G and 4x CPU throttling; desktop uses its desktop preset. Scores vary by 5 to 10 points between runs on the same machine.

Home, Skills Check, Results and Progress were re-run after the final fixes (HTML reports in this folder). The other six pages were measured earlier; the fixes since then were contrast, headings and tab titles, so their performance numbers are unchanged but their accessibility and contrast results may be slightly better than shown.

| Page | Mode | Run | Perf | A11y | Best practices | SEO | LCP | TBT | CLS | Contrast |
|---|---|---|---|---|---|---|---|---|---|---|
| home | mobile | final code | 48 | 84 | 100 | 82 | 17.2s | 0ms | 0.16 | pass |
| home | desktop | final code | 50 | 84 | 100 | 82 | 3.1s | 0ms | 0.33 | pass |
| career | mobile | earlier code | 46 | 87 | 96 | 82 | 17.1s | 0ms | 0.20 | pass |
| career | desktop | earlier code | 52 | 87 | 96 | 82 | 3.1s | 0ms | 0.29 | pass |
| roadmap | mobile | earlier code | 51 | 84 | 96 | 82 | 17.1s | 0ms | 0.12 | pass |
| roadmap | desktop | earlier code | 56 | 83 | 96 | 82 | 2.6s | 0ms | 0.33 | pass |
| assessment | mobile | final code | 55 | 86 | 96 | 82 | 17.2s | 0ms | 0.06 | pass |
| assessment | desktop | final code | 53 | 86 | 96 | 82 | 3.1s | 0ms | 0.27 | pass |
| results | mobile | final code | 43 | 86 | 96 | 82 | 17.1s | 417ms | 0.09 | pass |
| results | desktop | final code | 47 | 86 | 96 | 82 | 3.1s | 0ms | 0.41 | pass |
| coaching | mobile | earlier code | 49 | 84 | 96 | 82 | 17.1s | 0ms | 0.15 | pass |
| coaching | desktop | earlier code | 50 | 84 | 96 | 82 | 3.1s | 0ms | 0.36 | pass |
| weekly-plan | mobile | earlier code | 47 | 87 | 96 | 82 | 14.1s | 21ms | 0.18 | pass |
| weekly-plan | desktop | earlier code | 57 | 87 | 96 | 82 | 2.6s | 0ms | 0.32 | pass |
| progress | mobile | final code | 38 | 86 | 96 | 82 | 17.1s | 8ms | 0.35 | pass |
| progress | desktop | final code | 46 | 86 | 96 | 82 | 3.1s | 94ms | 0.46 | pass |
| profile | mobile | earlier code | 53 | 87 | 96 | 82 | 14.1s | 0ms | 0.09 | pass |
| profile | desktop | earlier code | 55 | 87 | 96 | 82 | 3.4s | 0ms | 0.26 | pass |
| ai-settings | mobile | earlier code | 55 | 87 | 96 | 82 | 17.6s | 14ms | 0.05 | pass |
| ai-settings | desktop | earlier code | 59 | 87 | 96 | 82 | 2.6s | 0ms | 0.27 | pass |

## What the failing audits are

| Category | Audit | Cause | Fixable here? |
|---|---|---|---|
| Accessibility | aria-allowed-attr (critical), list, listitem (serious) | Streamlit's own sidebar markup. The same findings appear in a minimal Streamlit app with none of this project's code; list and listitem appear once navigation is grouped into sections | No. Flat navigation would remove list and listitem |
| Best practices | valid-source-maps, errors-in-console | Streamlit's JavaScript bundle has no source maps; the console 404s are the framework asking for `/<page>/_stcore/health` when a page is opened by its URL (reproduced in a minimal app) | No |
| Performance | LCP, FCP, speed index, unused JavaScript and CSS, legacy JavaScript, render-blocking, total byte weight | Streamlit ships a large single-page front end; the app's own content is small | No |
| Performance | Cumulative layout shift 0.06 to 0.5 | The page is drawn progressively as Streamlit's server sends elements. Removing this project's layout CSS (padding and max width) changed it little (Progress stayed at 0.49), so the framework is the main cause | Not meaningfully |
| SEO | meta-description, robots.txt | Streamlit offers no hook for a page meta description, and serves its app shell for /robots.txt. Irrelevant for a local app that is not meant to be indexed | No |

Fixed since the first Lighthouse run: colour contrast on captions, step labels, badges, alert text and metric changes; heading levels; distinct page titles.
