# Maintenance & privacy

## Authorized sources

The ingester uses only `https://api.github.com/users/abeperl/starred?per_page=100&page=N` with the star timestamp media type. It never calls `/user/starred`, never reads a viewer feed, and refuses redirects and foreign pagination URLs. The second guard requires `repo.private is False` and public visibility. Responses stay in runner memory, never raw files/logs/artifacts. A schema allowlist writes only public project metadata to `data/catalog.json`.

`config/public-lists.json` contains numeric public repository IDs from public Lists owned by the explicit user `abeperl`, filtered with `visibility == PUBLIC`. It is a dated manual snapshot, not a live daily claim. Update only via `user(login: "abeperl") { lists }`, ignore nonpublic Lists, paginate fully, and export only public repository IDs. Never use `viewer` or authenticated starred feeds. IDs only match repositories already passing public ingestion; no unmatched names are exposed.

The workflow uses its own short-lived `GITHUB_TOKEN` for public API rate limits. No personal access token, broad account token or copied account secret is needed. Do not add secrets. Data fields: public numeric ID, full name, GitHub URL, supplied description, topics, language, SPDX label, star count, updated/star timestamps, archived/fork flags, safe HTTP(S) website URL, categories/provenance, review flag and public dated review note. Descriptions are untrusted public text, escaped in HTML and Markdown.

## Fail closed

Fetches are sequential, capped at 100 pages. Request errors, malformed pagination, oversized pages, an empty result, or a count decrease greater than 20% fail the run before committing or deploying. Repositories are deduplicated by numeric ID. An upstream failure retains the previously committed catalog and deployed site; Actions exposes the failure. Concurrent refreshes are serialized. API pagination is not an atomic snapshot; repeated star changes can affect a collection run.

## CI and publication

`Directory CI` runs unit tests, live public fetch, static generation and Chromium browser checks on PRs. It uploads a sanitized website preview only after checks pass. No fork secrets or `pull_request_target` are used. Production runs daily at 06:17 UTC, manually, or on main source changes. It repeats tests and browser checks with read-only permissions and no persisted checkout credentials, then uploads the tested Pages artifact and deploys through GitHub Pages. Only after deployment succeeds, a separate write-scoped job commits `README.md` and `data/catalog.json`. Generated catalog commits use the Actions token and do not recursively invoke publication. A failed snapshot commit can temporarily leave repository metadata behind the deployed site; retry the workflow. Deployments require successful tests; build failure cannot replace the current website.

Actions are pinned to reviewed full commit SHAs. Browser test dependencies install only on hosted GitHub runners (Playwright + Chromium, below 1 GB expected). There are no runtime dependencies, trackers, external fonts or analytics. GitHub hosting and API still have their own platform policies/logs.

## Operations

Check the most recent Actions run and Pages deployment after changes. Use manual workflow dispatch to retry upstream failures. A large legitimate count reduction requires a reviewed change to the fail-closed threshold or baseline; never publish an empty baseline. Contributions and human review decisions go through PRs. No automatic external promotion, Search Console registration, or community submissions are configured. Search engine indexing and traffic are not guaranteed.

Production URL: https://abeperl.github.io/awesome-stars/
