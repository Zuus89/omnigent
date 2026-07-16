---
type: review
task: workspace-layer
title: "Workspace layer — vps-infra architecture ruling"
status: final
author_role: infra
created: "2026-07-16"
related_decisions: ["workspace-layer.md (spec)", "workspace-layer_de.md (review)", "workspace-layer_devils-advocate.md (review)", "workspace-layer_vps-infra-questions.md (handoff)"]
---

# Workspace layer — vps-infra architecture ruling

Answers to `workspace-layer_vps-infra-questions.md`, grounded in this VPS's real,
measured state (2 vCPU / 7.8 GB, `omni-vps`) and this session's own incident history
(`omnigent-host.service` crash-loop + root-owned files, the 3-agent + 10-subagent
hard-lock, the code-server bind-mount/extension incidents on 2026-07-15). Decide A
first — B, C, E follow from it.

## A — Topology: **A2 (single code-server, convention-based isolation), with a
documented escalation path to A1 per-workspace, not a redesign**

**Ruling: A2 by default. A1 reserved as an escalation for a specific workspace that
earns it (contract requirement or materially higher trust risk) — not the baseline.**

Reasoning:

- **The resource math forecloses A1 as a default outright.** Live measurement right
  now, zero active agent sessions: `code-server` alone already uses ~789 MB idle
  (extension host + language servers), Omnigent server 190 MB, Postgres 49 MB — ~1 GB
  baseline out of 7.8 GB. The 2026-07-15 hard-lock happened with **3 top-level agents +
  a ~10-subagent workflow** (≈13 concurrent Claude Code processes) inside that *same*
  single container. A full second `code-server` instance per workspace (its own VS
  Code server + extension host + language servers, before a single agent even runs)
  costs a comparable ~800 MB–1 GB baseline *each*, before any Claude session opens.
  Two workspaces active at once under A1 already approaches the exact ceiling that hard
  -locked the box with only one. This isn't a tuning problem — 7.8 GB genuinely cannot
  hold N kernel-isolated editor stacks at any N > 1–2, and the 2 vCPU count means CPU
  contention (context-switching ~13 Node processes) was very likely as much a cause of
  the lock as RAM was.
- **The actual threat model here is self-inflicted cross-contamination, not a hostile
  co-tenant.** The original "isolate by container, nothing crosses by default" language
  in `plan.md` was written when Omnigent's own multi-tenant collaboration model (share
  with external, less-trusted collaborators) was still in view. That direction is
  parked — this VPS is personal-only, one operator (you), across several clients. The
  risk to defend against is *you* accidentally committing under the wrong identity, or
  an agent in Client B's folder reading Client A's credentials by mistake — not a
  malicious session escaping its container. A2's weaker, convention-enforced boundary
  is proportionate to that actual risk; A1's kernel boundary defends against a threat
  that isn't present today.
- **MAJOR 4 in the devils-advocate review already names this exactly**: the
  volume-isolation acceptance criterion is void on the plane you actually use. Agree
  with that finding without reservation — it's the same conclusion from a different
  angle.
- A3 (multiplexed editor-in-container) doesn't change this math — it's A1 with extra
  steps and a worse editor experience (no native `code-server` browser access per
  workspace without more plumbing). Not worth the complexity over A1 if you ever do
  need the stronger boundary for one workspace.

**What A2 actually looks like:** one `code-server` container (as today), workspaces
separated by **filesystem convention** (`/home/coder/repos/<workspace>/<project>/`) +
**git `includeIf` scoping** (B1) + **credential files scoped by path, never
container-wide env vars** (B2) + **a product-layer registry** (`workspaces.yaml`, C2)
that's the source of truth for which folder belongs to which workspace. The boundary
is real but is enforced by discipline + file permissions, not the kernel — that's the
trade this box's resources force, and it's proportionate to the actual risk.

**Escalation path (design now, use later):** when a specific workspace justifies it
(D2 — a contract requires physical separation, or the trust bar for that client is
meaningfully higher than the rest), stand up a **second, dedicated `code-server`
instance** for *that workspace only*, same pattern as today's, on its own port/volume.
Everything else stays on the shared A2 instance. This is a per-workspace opt-in, not a
platform-wide switch — keeps the common case cheap and gives the rare case a real
kernel boundary when it's actually earned.

## B — Credentials and injection into the code-server plane

### B1 — Git identity + token per workspace: **solvable at the git-config layer, no A1 needed**

Git's `includeIf "gitdir:..."` scopes more than `[user]` — it can also scope
`[credential]`. Structure:

```
# ~/.gitconfig (baked into the image, E1)
[includeIf "gitdir:/home/coder/repos/clientA/"]
    path = ~/.gitconfig-clientA
[includeIf "gitdir:/home/coder/repos/clientB/"]
    path = ~/.gitconfig-clientB
```

Each `~/.gitconfig-clientX` sets `user.name`/`user.email` **and** its own
`credential.helper` (e.g. `store --file=~/.git-credentials-clientA`, a workspace-scoped
PAT file, gitignored, permissions `600`). This gives a genuinely different GitHub/Azure
DevOps *account* per workspace, not just a different name/email on the same token.

Caveat: `gh auth login` itself is a single global login per machine (one `gh` identity
at a time) — it doesn't scope by folder. If a client's git remote needs its own GitHub
*account* (not just its own repo under your account), don't route that workspace
through `gh` — use the scoped `credential.helper`/PAT-file pattern above directly,
bypassing `gh` for that workspace only.

### B2 — Cloud credentials (Azure/Databricks): **path-scoped files, never container-wide env vars**

This is the one place A2's weaker boundary genuinely bites, and MAJOR 5 in the
devils-advocate review already flags the mechanism this rules out: don't inject client
cloud credentials as **container-level environment variables** — every process in a
single-container A2 setup (any terminal, any agent, in any folder) inherits container
env vars unconditionally, so an env-var credential for Client A is silently readable
from a Client B session. There is no path-scoping for env vars.

Instead: **credential files under each workspace's own path**
(`~/repos/clientA/.credentials/azure.json`, gitignored, `600`), and the tooling that
needs them (an agent's CLAUDE.md instructions, an MCP server config, a script) reads
the file **explicitly by its workspace-scoped path** — never a blanket env var an agent
could inherit regardless of which folder it's working in. Databricks already has the
right shape for this natively: `~/.databrickscfg` **profiles** are already
per-identity, not global — one profile per client, referenced by name per-project, no
new mechanism needed there, just discipline about which profile a given project's
tooling points at.

This is enforced by convention, not the kernel — same trade as A2 overall. If a
specific client's cloud-credential sensitivity crosses the line, that's exactly the
signal to escalate that one workspace to a dedicated A1 container instead of trying to
harden the shared container further.

### B3 — Anthropic provider key: **stays global, no separation needed**

You are the one operator across every workspace on your own subscription — there's no
identity boundary to enforce here. Ruling: shared/global OAuth login, unchanged. Revisit
only if a specific client ever provides their own Anthropic key for cost-attribution
reasons — that would be a **project**-level override at that point (per the
credential-vs-resource split already established in `plan.md`), not a workspace-wide
change.

## C — Role of the Omnigent server

### C1/C2 — **No role. The Workspace entity is a code-server-plane + product-registry
construction, full stop.**

Agree without reservation. `omnigent-host.service` is disabled (this session, root
cause of 3 of the 5 reported provisioning defects), the Omnigent server authorizes by
owner (not workspace — confirmed in your own message: all your workspaces share one
owner, so its control plane provides zero isolation regardless of anything built on top
of it), and the V1 decision already on record is that this project doesn't use
Omnigent's own UI day to day. There's nothing left for the Omnigent server to
contribute to the Workspace concept. Workspace = filesystem convention + git/credential
scoping (A2/B) + a product-owned registry (`workspaces.yaml` or equivalent) that maps
workspace → folder prefix → identity files. No dependency on the Omnigent server's
session-dispatch, auth, or data model.

**Follow-on, not part of this ruling — flagging for a separate decision:** given C1,
the Omnigent server + Postgres containers (190 MB + 49 MB idle, plus whatever CPU
overhead) are now running for zero functional benefit — the VS Code extension that
would talk to them was already left non-functional by decision in V1. Worth a future
call on whether to stop that stack entirely and reclaim the RAM/CPU headroom (relevant
to E2), separate from today's workspace-layer decision — don't block Step 6 on this.

## D — Data at rest

### D1 — Claude Code session transcripts: **same convention-based scoping as B2, not a separate mechanism**

Transcripts live under `~/.claude/projects/<path-encoded-cwd>/` today, in the single
`coder` user's home — readable across all workspaces in an A2 setup, same soft boundary
as credentials. Ruling: this needs the same discipline as B2 (workspace-scoped
awareness, not a blanket "everything's fine because it's all mine" assumption), but not
a separate isolation mechanism — if a workspace's transcript confidentiality ever needs
a harder guarantee than filesystem convention gives, that's the same signal as D2: escalate
that workspace to its own A1 container, where its transcripts genuinely live in a
different filesystem, not just a different folder. I'm not confident from the infra
side alone whether Claude Code supports scoping its own config/transcript directory
per-invocation (e.g. a `CLAUDE_CONFIG_DIR`-style override) — that's a product-layer
question to verify against the actual CLI, not an infra one; flag it back to the
product session to check before assuming either way.

### D2 — Physical separation for a future client contract: **confirmed — defer, but the A1 escalation path (A) is exactly the design that avoids a rewrite when it's needed**

Agreed: no current client requires this, don't build it now. The reason this ruling
spends real design effort on the A1 escalation path in section A (rather than just
picking A2 and moving on) is precisely so that when a contract *does* require it, it's
"stand up one more container for this workspace," not "redesign the isolation model."

## E — Previously pending items (#4-5 from the provisioning-defects report)

### E1 — Bake `gh` + git identity into the image, persist `~/.config/gh`: **proceed, unchanged by this ruling**

Independent of A/B/C — this is baseline image hygiene regardless of topology. One
addition given B1: the baked identity becomes the **default/fallback** `~/.gitconfig`
(for anything not under a workspace-specific path), with each workspace's
`includeIf`-scoped config overriding it. Complementary, not conflicting. Still not
implemented — queued next.

### E2 — `mem_limit`/`cpus` + concurrency guidance: **concrete numbers, grounded in live measurement**

Since A2 keeps everything in one container (no per-workspace multiplication), this
doesn't get harder as workspaces are added — good news, but the box was still already
proven insufficient for careless concurrency once.

- **`mem_limit: 4g`, `cpus: "1.5"` on the `code-server` service.** Baseline idle usage
  is ~800 MB, leaving real headroom for normal editing + a few agents, while capping
  the blast radius: if something runs away, Docker OOM-kills *that container* (restarts
  cleanly, per the existing `restart: unless-stopped`) instead of exhausting the whole
  VM and hard-locking the host the way the 2026-07-15 incident did. This is a circuit
  breaker, not a capacity increase — 4 GB was not enough to survive the 13-process
  incident and isn't meant to be; it's meant to fail into "container restarts" instead
  of "SSH goes dark, manual reboot required."
- **Concurrency ceiling: ~3-4 concurrent Claude Code processes total on this box at any
  one time** (interactive sessions + any Workflow's own `agent()` fan-out, summed) —
  not the ~13 that caused the lock. This is a CPU-bound limit as much as a memory one:
  2 vCPUs servicing 13 concurrent Node processes causes severe scheduling contention
  independent of whether RAM ever actually runs out.
- **Large multi-agent Workflows (the ~10-subagent kind) don't belong on this box at
  all.** Treat `omni-vps` as the always-on, lightweight, persistent editor — not
  compute capacity for wide fan-out. Run heavy research/review Workflows from wherever
  has real headroom (the notebook, or a temporary higher-tier environment), not from a
  terminal inside this `code-server` container.

## F — Operational consent

### F1 — Ephemeral local Omnigent server for a security probe: **moot, per C — declining**

Per C1/C2, the Omnigent server has no role in the Workspace design going forward, so
there's nothing left for this probe to verify. Not authorizing it — if C is later
overturned for some reason not visible from the infra side, revisit then.

---

**Summary for Step 6:** re-center the spec on the code-server plane (A2 default + A1
escalation), drop the Omnigent-host-plane isolation architecture entirely (it protects
nothing you use), and treat credential/transcript isolation as filesystem-convention +
git `includeIf` + path-scoped credential files — never container-wide env vars. This
should resolve devils-advocate BLOCKER 1 and MAJOR 4/5 directly; BLOCKER 2 (the
`/council` process question on Ruling 1) is a lifecycle-governance call for the product
session, not something answered from the infra side.
