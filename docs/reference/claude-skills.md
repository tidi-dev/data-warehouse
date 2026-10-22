# Claude Code Setup

This project uses Claude Code with two kinds of helpers that do **different
jobs**:

```text
Superpowers (plugin)          → ENGINEERING workflow
  Requirement → Brainstorm → Plan → Implement → Test → Review → Verify

Project agents (.claude/agents) → DATA WAREHOUSE learning and correctness
  Business question → Understand data → Choose grain → Model facts/dimensions
  → Transform → Test data → Analyze
```

Superpowers keeps the *code* disciplined. The project agents keep the
*warehouse* correct and make sure *you* do the learning.

```text
Data Warehouse Tutor     → teaches
Data Modeling Reviewer   → checks warehouse design
Data Quality Reviewer    → checks data reliability
Superpowers              → engineering workflow
```

---

## Superpowers

| | |
|---|---|
| **Source** | https://github.com/obra/superpowers (by Jesse Vincent / Prime Radiant), distributed through Anthropic's official marketplace `claude-plugins-official` |
| **Installation method** | Official plugin marketplace, **project scope**: `claude plugin install superpowers@claude-plugins-official --scope project` (in a session: `/plugin install superpowers@claude-plugins-official`). This wrote `enabledPlugins` into [`.claude/settings.json`](../../.claude/settings.json). No files were copied from the repository. |
| **Version** | **6.4.1** — the version the official marketplace pins (commit `5bf4e78`). GitHub `main` was at **6.4.2** on 2026-10-05; the only differences are a leaner `writing-plans` skill and doc cleanups. We stay on the marketplace-pinned version; it will update when the marketplace does. |
| **Why used** | It turns "write code" into a repeatable loop — design before code, small plans, tests first, evidence before claiming success. That matches this project's rule: *don't claim it works unless it was verified.* |

### Security review (done before installing, 2026-10-05)

Source read: the plugin manifest, `hooks/hooks.json`, `hooks/session-start`,
`hooks/run-hook.cmd`, every `SKILL.md`, and every helper script.

- **No install-time code, no MCP servers, no declared permissions, no
  credentials, no changes to global config.**
- **One hook** (SessionStart on startup/clear/compact): reads
  `skills/using-superpowers/SKILL.md` and injects it into the conversation
  (~3 KB of instructions). No network access, writes nothing.
  The injected text is assertive ("if there is even a 1% chance a skill
  applies, you must invoke it") — so `CLAUDE.md` states that the
  educational safety rule takes precedence. Superpowers itself documents
  that user instructions (CLAUDE.md) beat skills.
- **Network:** only optional features — brainstorming's local "visual
  companion" web server (127.0.0.1, random token; its page loads a logo from
  primeradiant.com that reports the plugin version — disabled here with
  `SUPERPOWERS_DISABLE_TELEMETRY=1` in project settings), and
  `diagnosing-superpowers` (can file GitHub issues after approval — denied
  here).
- **Repository writes:** specs/plans under `docs/superpowers/`, workspace
  state under `.superpowers/` (git-ignored here). Several skills assume a
  **git** repository (commits, branches, worktrees).
- **Verdict:** low risk; the real cost is process weight, which we reduce by
  allowing only the skills below.

### How the skill subset is enforced

A plugin installs as a whole — Superpowers has no per-skill switch. Claude
Code's documented mechanism for blocking individual skills is a permission
**deny rule**, `Skill(<plugin>:<skill>)`, which we put in the shared
[`.claude/settings.json`](../../.claude/settings.json). Denied skills can't be
invoked by Claude.

---

## Selected Superpowers Skills

| Skill | Purpose | When to use | Why selected |
|---|---|---|---|
| `using-superpowers` | Bootstrap: tells Claude how to find and use skills | Automatically at session start (hook) | Required by the plugin; can't usefully be removed |
| `brainstorming` | Clarify intent, compare 2–3 approaches, agree a design before code | Start of each implementation phase (e.g. "set up the dbt project") | Forces "design before code"; *for learning-critical design decisions, you decide — Claude facilitates* (CLAUDE.md) |
| `writing-plans` | Turn an agreed design into small, checkable steps | After brainstorming, before touching code | Keeps each phase small and reviewable — no racing ahead |
| `executing-plans` | Carry out a plan inline, step by step, in this session | When implementing a plan | You can watch and question every step (chosen over subagent-driven-development) |
| `test-driven-development` | Write a failing test, then the code | Python code (generator, loader, utilities); the same idea later for dbt data tests | Our tests protect our assumptions about the data |
| `systematic-debugging` | Root cause before fix | A failing test, a wrong number, a Docker problem | Data bugs (fan-out, wrong status filter) look like "plausible numbers"; guessing doesn't find them |
| `verification-before-completion` | Run the command and read the output before saying "done" | Before claiming anything works | Directly implements the brief's "do NOT claim something works unless actually verified" |
| `requesting-code-review` | Ask a reviewer subagent to check the finished work | End of each phase / plan | General code review; complements our *data*-specific reviewers; `executing-plans` uses it for its final review |

## Project Agents

Defined in [`.claude/agents/`](../../.claude/agents/).

| Agent | Responsibility | When to use |
|---|---|---|
| **data-warehouse-tutor** | Teaches. Intuition first, then terms; asks you to reason; reviews your answers; gives hints, not solutions, for learning-critical decisions; never edits files; doesn't race ahead of the current phase | Any time you're learning: checkpoint questions, exercises, "explain X". Best as your main session: `claude --agent data-warehouse-tutor` |
| **data-modeling-reviewer** | Read-only review of warehouse **design**: grain, fact vs dimension, keys, cardinality/fan-out, double counting, measure additivity, date dimension, SCD/history | After you propose a model or write fact/dimension models or analytical joins (Phase 3 onward). Ask: "use the data-modeling-reviewer on my fact_sales design" |
| **data-quality-reviewer** | Read-only review of data **reliability**: nulls, duplicates, referential integrity, accepted values, row counts, freshness, idempotency, incremental correctness, schema drift, test coverage — always with the business consequence | After changing loaders/models/tests, after a load, or when a number looks wrong (most useful from Phase 5) |

Boundaries: the tutor never reviews code; the modeling reviewer never
checks freshness or nulls; the quality reviewer hands design questions to
the modeling reviewer; Superpowers' code review covers code quality, not
warehouse semantics. Docker/README accuracy is covered by
`verification-before-completion` + `requesting-code-review` — infrastructure
is secondary, so it gets no agent of its own.

---

## Considered But Not Used

| Skill / Agent | Reason |
|---|---|
| `subagent-driven-development` | **Low educational value.** Hands each task to a fresh subagent and reviews in loops — fast, but the work happens out of your sight. `executing-plans` does the same job inline. Also requires git worktrees. |
| `dispatching-parallel-agents` | **Unnecessary.** Our phases are small and sequential. |
| `using-git-worktrees` | **Unnecessary / conflicts with Docker-only rule.** Isolation is overkill for a solo learning repo, and its setup step auto-runs dependency installs (e.g. `pip install`) on the host. |
| `finishing-a-development-branch` | **Unnecessary.** Merge/PR workflow for feature branches; you'll commit directly. Can be enabled later if you use branches and PRs. |
| `receiving-code-review` | **Duplicate / low value here.** Mostly about responding to PR review threads; the verification and debugging skills already cover "check feedback before acting". |
| `writing-skills` | **Unrelated.** For authoring new skills. |
| `diagnosing-superpowers` | **Unrelated + security concern.** Meta-debugging of Superpowers itself; writes under `~/.superpowers` and can file GitHub issues. |
| Separate "Docker/infra reviewer" agent | **Duplicate.** Covered by verification + code review; infra is secondary to warehouse correctness. |
| Separate "SQL exercise" agent | **Duplicate.** The tutor already gives and reviews exercises. |

To re-enable a skill, remove its line from `permissions.deny` in
`.claude/settings.json`.

---

## Verify the setup yourself

```bash
claude plugin list            # superpowers@claude-plugins-official … scope project
claude --agent data-warehouse-tutor
```

Inside a session, `/agents` lists the three project agents.

What we verified on 2026-10-05 (headless session in this folder): Claude
found all three project agents; invoking `superpowers:writing-skills` was
refused with "Skill execution blocked by permission rules"; invoking
`superpowers:verification-before-completion` worked. Note that denied
skills still **appear** in Claude's skill list — the deny rule blocks
*using* them, not seeing them.

> **Note:** Superpowers' brainstorming and planning skills commit their
> specs and plans with git. This folder is not a git repository yet — run
> `git init` and make a first commit when you're ready.
