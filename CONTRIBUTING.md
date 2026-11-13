# Contributing & editorial policy

Corrections, useful categorization and accessibility improvements are welcome through issues or pull requests. Do not submit confidential material or credentials. Do not submit promotional mass additions or paid placements.

## Two distinct collections

- **Collected:** public repositories starred by abeperl; inclusion is automatic, not endorsement or recommendation.
- **Reviewed Awesome list:** initially empty. A human maintainer must check documentation and basic usability, project purpose, maintenance and archived status, licensing, obvious safety concerns, and relevance. A dated public review note must explain evidence and limitations. This is not a security audit. No fabricated testing or automated recommendations.

An explicit `reviewed: true` with a public `review_note` starting `YYYY-MM-DD: ` followed by at least 20 characters of evidence and limitations in `config/overrides.json` is required to mark a project reviewed. Human review acceptance is required before merging any such change. Key entries by numeric public GitHub repository ID, not credentials. Optional `categories` override the inferred categories. Use existing category names only.

Public GitHub List mappings are a dated public-only snapshot, **not** editorial reviews. Metadata rules can yield multiple tags. Unclear projects remain **Needs Review**. Missing descriptions use “No description supplied”; contributors must not invent upstream claims. Ask for classification corrections rather than claiming all projects are vetted.

## Development

All tests, generation, browser checks and builds run through GitHub Actions. Do not generate site output or install build dependencies on the server. Open a PR, wait for `Directory CI`, inspect the preview artifact, and merge only after successful checks. PRs use read-only permissions and never deploy. Production refresh and deployment occur only from main.

Site code is MIT licensed. Preserve attribution. Repository licenses and trademarks remain with their owners; this directory does not relicense projects.
