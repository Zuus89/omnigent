---
type: review
task: workspace-layer
title: "Workspace layer — vps-infra architecture ruling 2 (post-council)"
status: final
author_role: infra
created: "2026-07-16"
related_decisions: ["workspace-layer_vps-infra-ruling.md (ruling 1, partially superseded)", "workspace-layer.md (spec)", "workspace-layer_devils-advocate.md (review)"]
---

# Workspace layer — vps-infra ruling 2 (post-council)

Answers to the council's four follow-up questions. Grounded in a live read-only probe of
`omni-vps` run 2026-07-16 (box idle, `load average: 0.01`), not in recall.

**This ruling partially supersedes ruling 1.** Specifically: the threat model in ruling 1
section A was wrong (Q2 below), and the "keep the passwordless sudo" recommendation from
provisioning-defect #1 is withdrawn (Q1 below). Sections B1, C1/C2, D2, E1 stand unchanged.

## Measurements this ruling rests on

```
# host
Mem: 7940 MB total / 1411 used / 6528 available     nproc = 2      load 0.01

# containers (idle, zero active agent sessions)
code-server-code-server-1    807.4 MiB    0.97% CPU
omnigent-omnigent-1          190.2 MiB    0.17% CPU
omnigent-postgres-1           48.7 MiB    3.11% CPU

# who runs the editor plane
uid=1000(coder) gid=1000(coder) groups=1000(coder),100(users)

# live processes at probe time
coder  36355  claude
coder  36486  claude

# sudo posture  (/etc/sudoers.d/nopasswd, mtime Jul 11 19:43 = base image build date)
User coder may run the following commands on srv1802750:
    (ALL) NOPASSWD: ALL

# image tooling
useradd / adduser : NOT PRESENT in codercom/code-server:latest

# ownership
/home/coder/repos/*  ->  coder:coder (1000:1000) throughout

# omnigent host service
omnigent-host.service : disabled / inactive

# code-server compose
network_mode: host      (no mem_limit, no cpus — E2 still unapplied)
```

---

## Q1 — A2' (per-workspace Unix uids, single container): **adopt ONLY as an indivisible bundle with removal of the blanket sudo. Standalone, it is theatre — reject it.**

### Blocker 1 (decisive): `coder ALL=(ALL) NOPASSWD:ALL` voids the kernel boundary

Measured, in `/etc/sudoers.d/nopasswd`. Any process running as `coder` — including an
injected agent — runs `sudo cat /home/ws-clientb/.credentials/azure.json` and the uid
ceases to be a control. **The kernel denial the council wants as its observable trigger
never fires, because the read succeeds.**

A2' therefore *requires* deleting `NOPASSWD:ALL`. This is a precondition, not an
implementation detail. Two consequences the council must weigh together:

1. **This reverses an earlier recommendation of mine.** In provisioning-defect #1 I
   recommended *keeping* that sudoers rule ("upstream default; code-server is
   tailnet+password-gated, not public"). That was reasoned under the old threat model.
   Under the re-declared model (Q2) it is wrong. The two decisions are coupled — they
   cannot be voted on separately.
2. **Day-2 regression is real:** no more casual `apt install` from the container
   terminal. The base image is designed around that affordance.

### Blocker 2: the editor plane and the agent plane are the same uid, and the editor must read the files

code-server runs as `coder`. Its extension host runs as `coder`. The Claude Code
extension — **which is how this platform actually launches agents today**
(`claudeCode.claudeProcessWrapper` is set, and two `claude` processes were running as
`coder` at probe time) — runs as `coder`.

- If `repos/clientA` is `ws-clienta:ws-clienta 700`, **code-server cannot open the files
  at all.** The editor breaks. This kills the naive form of A2'.
- The only surviving layout: owner `ws-clienta`, **group `coder`**, dirs `750`, code
  `640`, and **secrets `600` owner-only**. The editor browses code; only the workspace
  uid reads that workspace's secrets. Cross-workspace agent reads fail with a kernel
  denial, because `ws-clienta` is not in `ws-clientb`'s group and hits `other` = `0`.
  This is coherent and is the only version worth costing.
- **But the agent only acquires the workspace uid if the launch path drops privilege.**
  The only lever is `claudeProcessWrapper`: it must become a script that resolves cwd →
  workspace and `exec sudo -u ws-clienta claude "$@"`. Plausible — but it places the
  entire security boundary on a wrapper that sits in the middle of the extension's
  pty/stdio/IPC. That is precisely the layer that broke twice in one month (the
  musl/glibc extension incident; the bind-mount incident). **If this wrapper is adopted,
  it is a security control and must be tested as one — not treated as a convenience.**
- Terminals: VS Code terminal profiles can be scoped per folder, so a terminal opened in
  clientA's folder can default to `sudo -u ws-clienta -i`. But any user can select a
  non-default profile and get a `coder` shell. That path stays convention-enforced —
  which is what A2' was meant to escape. Honest accounting: A2' hardens the *agent* path,
  not the *human terminal* path.

### Blocker 3 (cost, not correctness): the image lacks the tooling

`useradd`/`adduser` are **not present** in `codercom/code-server:latest`. A2' needs a
custom Dockerfile layer merely to create users. This merges with the already-planned E1
layer (bake `gh` + git identity), so the marginal cost is low. Per-workspace provisioning
becomes a script: create uid → chown tree → write narrow sudoers rule → create
`CLAUDE_CONFIG_DIR` owned by that uid → write the terminal profile.

### Cost comparison

| | RAM per workspace | Boundary depends on | Provisioning |
|---|---|---|---|
| **A2** (today) | 0 | nothing — there is no boundary | none |
| **A2'** | **~0** (uids are free) | the wrapper being correct **and** the blanket sudo being gone | custom image layer + per-ws script |
| **A1** | **~807 MiB measured** | the kernel, unconditionally | second compose stack per ws |

A2's ~0 MB cost is its decisive advantage over A1 on this hardware. A1's advantage is that
its boundary does not depend on a wrapper being written correctly.

### Day 2

- **Backups / updates:** run as root on the host. Root reads everything. Unaffected.
- **Shared repos across workspaces:** need a shared group — one hole punched by hand per
  shared repo. Manageable, but this is where the model erodes over time.
- **Host-side application:** `/opt/omnigent` is bind-mounted in, so its ownership is
  managed on the **host**. A2' must be applied host-side too, not only in-container.
- **Conflict with ruling 1 §B3:** B3 ruled the Anthropic credential stays global/shared
  because there is one operator. A `CLAUDE_CONFIG_DIR` per uid means **N logins** — the
  credential file is `600` owned by a uid and cannot be shared for free. The collaborative
  goal changes B3 anyway (each collaborator brings their own credential on their own
  host), but **the plan text must be made consistent**; today it is not.
- **`CLAUDE_CONFIG_DIR`:** accepted as verified by the product session. My probe
  (`strings` on the mounted binary → 0 hits) is **inconclusive, not a refutation** — it is
  a packaged SEA. The empirical test outranks the probe.

### Ruling

**A2' yes — indivisible: per-workspace uids + deletion of `NOPASSWD:ALL` + the launch
wrapper treated and tested as a security control. If the council will not remove the
blanket sudo, reject A2' outright:** it is then strictly worse than A2 — the same boundary
(none), more complexity, and a false sense of having one.

---

## Q2 — Threat model: **I was wrong. Re-declared to include prompt injection, effective today.**

Ruling 1 modelled **accident** ("you committing under the wrong identity"), not
**adversary**. An agent with web access is a third-party-controllable process. The council
is right; the correction is conceded without reservation.

Measured exposure under A2 as it exists right now:

| Measured fact | Consequence under injection |
|---|---|
| Agents run as `coder` | The injected agent holds the uid that owns everything |
| `coder ALL=(ALL) NOPASSWD:ALL` | …and is root in the container |
| `network_mode: host` | …and reaches the host's real loopback (`127.0.0.1:8000`) and the tailnet |
| `.claude/.credentials.json` `600 coder` | …and reads the Anthropic OAuth credential |
| `/root/repos` bind-mounted | …and touches all five repos |

**The council framed this as a binary. It is not — the answer is both.** The model is
re-declared (injection is in scope **today**, not in a future phase), **and** because the
mitigation (A2' + sudo removal) is not yet built, the plan states the exposure verbatim
until it is:

> *The default plane has no boundary against the platform's own daily activity. An agent
> that ingests hostile web content executes as `coder`, holds passwordless root in the
> container, shares the host's network namespace, and can read every workspace's
> credentials and the Anthropic OAuth token.*

That sentence is not an alternative to re-declaring the model. It is what gets written
down until the model's mitigation exists.

### Observable reopen trigger under pure A2: **none exists.**

Under A2 nothing is denied, so nothing is logged. The council's requirement is **unmet**
by A2 as specified. The options:

- **A2':** the kernel denial *is* the trigger. Free, precise, and preventive — it emits
  the signal as a side effect of blocking.
- **A2 + `auditd`:** a detective control built on the host (which shares the kernel with
  the container): `-w /home/coder/repos/clientA/.credentials -p r -k xread` logs
  *successful* reads with pid/exe/cwd. Real, but noisy and it is work — signal without
  prevention.
- **A2 alone: no trigger. Requirement unmet.**

This cuts against ruling 1 and is the strongest argument on the table for A2'.

---

## Q3 — Omnigent/Postgres stack: **stop-but-preserve.** Agreeing with the product read, on stronger grounds.

The reframe is legitimate, but the conclusion does not change — and the reason is not on
the council's list: **stopping it does not surrender the collaboration engine, because the
engine is a compose file plus a Postgres volume, not a running process.** Surrendering it
would be `down -v`. `docker compose stop` preserves everything and returns in ~10 s — the
original pilot did exactly this and it is on record as "reactivation ~10 s".

1. **The described collaborative model does not need the server up until a collaborator
   exists.** Each collaborator brings their own host and their own credentials; the server
   coordinates. Zero collaborators → zero function. It is not insurance; it is an idle
   daemon.
2. **Under the re-declared threat model, running it is a live liability.** `network_mode:
   host` on code-server means an injected agent as `coder` reaches `127.0.0.1:8000`
   **directly**. The `PUT mcp-servers → agents` table path the council names is precisely
   *a runtime secrets-persistence surface reachable from the injected plane*. Stopping the
   stack removes that surface while it is dormant. **This is the strong argument.**
3. **The registration is already stale:** `omnigent-host.service` is `disabled` +
   `inactive` (measured) and was 403-crash-looping before it was disabled. Re-registration
   is required whenever collaboration activates, regardless. Stopping loses nothing that
   is not already broken.
4. **The RAM argument is weak and this ruling does not lean on it:** 190 + 49 = 239 MB
   against **6528 MB available**. That is not a meaningful reclaim, and claiming otherwise
   would be selling smoke. The A1 valve is not RAM-starved by this stack.

**Action:** `docker compose stop` — **never `down -v`**. `omnigent-host.service` stays
disabled.

**Reopen condition:** when the collaboration phase actually starts, bring it up,
re-register the host, and **at that point re-examine the secrets-persistence path as a
design question** — because it is then serving real users and is a genuine multi-user
surface, not a dormant one.

---

## Q4 — A1 ceiling: **confirmed, ≤1. And A1 buys isolation, not capacity.**

Measured on an idle box: a single `code-server` instance = **807.4 MiB** with zero agents
running. A second A1 instance costs another ~800 MB of baseline before one agent starts.
Host: 7940 MB total, 1411 used.

**≤1 escalated workspace** — the shared A2 instance plus exactly **one** dedicated A1
instance. Never plural. Document it as `≤1`.

**This clause belongs in the plan verbatim,** because "escalate a workspace to A1" reads
like "give that client its own capacity", which is false:

> **The binding constraint is not RAM — it is the 2 vCPUs.** The 2026-07-15 hard-lock was
> ~13 Node processes on 2 cores. The concurrency ceiling (~3–4 concurrent Claude
> processes) is **global across both containers**, because they share the same two cores.
> A1 gives that workspace its own filesystem boundary while competing for the same CPU.

---

## Summary for the council

| Q | Ruling |
|---|---|
| 1 | **A2' adopt — but indivisible with deleting `NOPASSWD:ALL` + a tested launch wrapper. Otherwise reject.** RAM cost ~0; boundary is only as good as the wrapper. |
| 2 | **Threat model re-declared: prompt injection is in scope today. I was wrong.** Both: re-declare *and* write the exposure verbatim until mitigated. **Pure A2 has no observable reopen trigger — requirement unmet.** |
| 3 | **Stop-but-preserve** (`stop`, never `down -v`). Strong reason = the injected plane reaches `127.0.0.1:8000` via host networking; RAM is a weak reason. |
| 4 | **≤1. A1 = isolation, not capacity.** CPU (2 vCPU) binds before RAM. |

Unchanged from ruling 1: B1 (git `includeIf` scoping), C1/C2 (Omnigent server has no role
in the Workspace entity), D2 (defer physical separation; A1 escalation path is the design),
E1 (bake `gh` + identity — now also the natural home for the A2' `useradd` layer).

Still unapplied and now overdue: **E2** (`mem_limit: 4g`, `cpus: "1.5"` on code-server).
The probe confirms the compose still has neither. Under the re-declared threat model this
is also a containment control, not only a stability one.
