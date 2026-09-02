# Wayback worker — operational lessons

## Persisting new archive-result concepts

`archive-result` files are normally created as previously untracked files. A persistence check based on `git diff --quiet` before staging is therefore incorrect: plain `git diff` ignores untracked files and can report a clean tree even after the drain wrote valid results.

The worker must stage `knowledge/wayback/results/` first and inspect the index (`git diff --cached --quiet`). This failure mode was observed on run `33691730643`: the post-drain OKF check saw `archived=4`, but the old persistence step discarded the two new result files because it treated them as absent.

This is an infrastructure failure of the worker, not a failure of Internet Archive and not evidence for editorial `archive_failure`.
