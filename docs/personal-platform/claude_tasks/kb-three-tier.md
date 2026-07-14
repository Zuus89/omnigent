---
type: spec
title: "Three-tier knowledge base (Global / Workspace / Project)"
task: "kb-three-tier"
status: draft
created: "2026-07-14"
related_decisions: ["plan.md §Phase 2 (three-tier KB, curator, promotion flow)", "silverbullet-access-layer (deep-research 2026-07-14)"]
---

# Three-tier knowledge base — spec (DRAFT, brief stage)

> **Lifecycle state:** Step 1 (Brief) captured and design direction approved by the human,
> 2026-07-14. This task runs the FULL 10-step lifecycle in its own session, blocked by the
> Workspace-layer task (the Workspace entity gives `kb-ws-<company>` its addressing). Steps
> 2–6 (data analysis, spec expansion, alpha test, reviews, freeze) are still pending — the
> sections below are the approved draft direction, not a frozen spec.

## Brief (Step 1 — human, 2026-07-14)

Three KB layers:

- **Global**: the most general knowledge — required repo structure, information
  architecture (how knowledge itself is stored), git conventions, etc.
- **Workspace**: workspaces map to companies (the user freelances for several). Everything
  about that company's configuration and context: Databricks accounts/environments/URLs/
  warehouses, Azure accounts, plus its data architecture — tables, business rules,
  important Confluence pages.
- **Project/repo**: local to each repo — its tasks, reviews, councils, learnings.

A curator agent (already planned) proposes tier upgrades: something learned in a repo may
deserve the workspace KB; something learned in a workspace may deserve global.

Human-access layer decision (same date, from the deep-research report): **SilverBullet**,
with Obsidian optional as a desktop-only editor over the git checkout.

## Approved design direction (pre-spec)

### One tier = one kind of git repo; SilverBullet is only the window

| Tier | Git home | Content | Hosted under |
|------|----------|---------|--------------|
| Global | Own repo `kb-global` (private) | Cross-cutting standards: repo structure, information architecture, git conventions, universal gotchas, the lifecycle | The user's personal identity |
| Workspace | One repo per company: `kb-ws-personal`, `kb-ws-<company>` | Non-secret workspace config (Databricks URLs, environment/warehouse names, Azure account identifiers), data architecture (catalogs/schemas/tables), business rules, Confluence link map, contacts | **That company's identity** (their Azure DevOps/GitHub) — client knowledge does not live in the personal GitHub |
| Project | Inside each repo, `docs/knowledge_base/` (existing pattern) | Task artifacts, learnings, codebase gotchas | Wherever the repo lives |

### Uniform note frontmatter (what makes the curator mechanical)

```yaml
---
tier: project | workspace | global
scope: <repo-or-workspace>
type: gotcha | rule | architecture | standard | link-map
status: active | superseded
promoted_from: <origin path, when promoted>
proposed_by: curator | human
---
```

### Promotion flow (never silent — per plan.md)

Curator detects a candidate → drafts a **generalized rewrite** for the higher tier (not a
verbatim copy) → proposal enters the review-panel queue → human accepts / rejects /
discusses → only on accept is the higher-tier note written, with `promoted_from`
provenance; the origin note gets an upward link. Applies equally to workspace → global.

### SilverBullet: one composed Space per workspace (Docker bind-mounts)

```
/space  (workspace "personal")
├── global/      ← READ-ONLY mount of kb-global
├── workspace/   ← RW mount of kb-ws-personal
└── projects/
    ├── omnigent/   ← mount of omnigent/docs/knowledge_base/
    └── ...
```

One URL per workspace; the isolation boundary holds (a Space never mixes workspaces).
SilverBullet's own coarse git-sync stays **off** — server-side agents/hooks own git.
Deployment config goes in `vps-infra`, per the repo-scope rule.

### Hard rule

The KB stores names, URLs and pointers — **never secrets** (Hard Rule 6; see the
`secrets-manager` task for where credentials actually live).

## Scope

TBD at Step 3 (after Step 2 data analysis).

## Out of scope

TBD at Step 3. Known already: the curator agent + review panel are the NEXT task
(depends on this one), not this one.

## Acceptance criteria

TBD at Steps 3–4. plan.md §Phase 2 verification is the seed: reject writes nothing;
accepting a project/workspace proposal writes only at that tier; accepting global writes
to `kb-global` and is readable read-only from a second workspace.

## Risks / open spikes

1. SilverBullet indexer behavior over a composed Space (bind-mounts, one read-only branch;
   where does its index live, what happens on attempted edit of `global/`). Needs a
   hands-on spike — flagged by the deep-research report, not resolvable by more research.
2. SilverBullet git library relocated to a single maintainer's personal repo (bus factor);
   mitigated: we don't use it (server-side git), and it's ~50 replaceable lines of Lua.
3. Multi-repo Space vs SilverBullet's one-directory assumption — the composed-mount design
   above is the chosen answer; the spike validates it.
