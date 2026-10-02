# skillspector-open — the skill supply-chain scanner

English | [简体中文](README.zh-CN.md)

Your agent loads skills. Skills are unsigned code that runs with your API
keys. This repo is building the open, deterministic, static-only scanner
that grades them — **and publishes its own false-positive audit**, because
a scanner that won't admit when it's wrong is a scanner you can't trust.

## Status: pre-v1, honest

What exists today:

1. **`slop-scan.py`** — the first check module. Heuristic, stdlib-only,
   deterministic, CI-safe: near-duplicate code blocks, leftover debug
   hooks, unimplemented stubs shipped as code, TODO density, placeholder
   ellipses, oversized files. Exit `1` if any HIGH finding, else `0`.
2. **`docs/methodology.md`** — a complete, real, adjudicated security
   assessment of a live skill-style repo (134 scanner findings manually
   adjudicated down to 0 true positives, with per-category false-positive
   analysis). This is the methodology doc and the report template the full
   scanner is being built toward.

What doesn't exist yet: the full multi-check scanner, the report-card
format, the weekly leaderboard. That's the roadmap — see the issues
labeled `help wanted`. We'd rather ship the audit trail first and the
scanner second than the other way around.

## 60-second demo

```bash
curl -o slop-scan.py https://raw.githubusercontent.com/empire-mind/skillspector-open/main/slop-scan.py
python3 slop-scan.py examples/sample-project   # fires HIGH on purpose-built slop
python3 slop-scan.py --json path/to/skill-repo
```

Expected output on the sample project is documented in
[examples/README.md](examples/README.md) — verify the scanner fires what
we claim, or open a bug.

## Design principles (non-negotiable)

- **Static-only default.** No LLM in the loop, no API keys, runs in CI in
  seconds. A scanner that needs your OpenAI key is a scanner labs won't
  touch.
- **Deterministic.** Same repo + same scanner version = same report, every
  time. Version-pinned, reproducible grades.
- **FP audit shipped with the code.** Every finding class documents its
  known false positives next to the check, following `docs/methodology.md`.

## Development

```bash
python3 -m pytest tests/    # offline, stdlib + pytest only
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

**Every issue and external PR gets a first response within 7 calendar
days.** `good first issue` items are scoped for one evening — new check
ideas are especially welcome (propose the check + its FP audit together).
Full funnel in [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see the
org [SECURITY.md](https://github.com/empire-mind/.github/blob/main/SECURITY.md).

## Attribution

Heuristic design inspired by the evaluation thinking in
[garrytan/gstack](https://github.com/garrytan/gstack) (MIT © 2026 Garry
Tan); implementation is original. The assessment methodology was validated
with SkillSpector v2.12.0 (NVIDIA).

## License

MIT — see [LICENSE](LICENSE).
