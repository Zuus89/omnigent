---
type: review
title: "Workspace layer — DE Step-5 feasibility review (executed probes)"
task: "workspace-layer"
status: final
created: 2026-07-16
reviews_head: 88c188e8
---

# Workspace layer — DE Step-5 feasibility review

Executed feasibility review of `workspace-layer.md` (Step-3 spec + 7 human rulings) against the
real code at HEAD `88c188e8`. All probes are **code-analysis** verdicts: per the read-only
constraint (no consent for ephemeral server/host/runner processes on this 2vCPU/7GB box), no
omnigent server/host/runner/docker process was started. Where only a live run could close a
question, it is marked **LIVE-PROBE PENDING**. Evidence is `file:line` at HEAD `88c188e8`.

Evidence keys: `connect` = `omnigent/host/connect.py`; `htunnel` =
`omnigent/server/routes/host_tunnel.py`; `rtunnel` = `omnigent/server/routes/runner_tunnel.py`;
`hlaunch` = `omnigent/server/routes/_host_launch.py`; `sessions` =
`omnigent/server/routes/sessions.py`; `mhosts` = `omnigent/server/managed_hosts.py`; `models` =
`omnigent/db/db_models.py`; `mcp_route` = `omnigent/server/routes/session_mcp_servers.py`.

---

## Verdict: FEASIBLE-WITH-CHANGES

The verified upstream mechanisms the spec rides are **real and behave as the spec assumes on
the plane they cover**: an externally-run `omnigent host` container, a named volume, a
per-container env file, a Docker network, and `_build_runner_env` sourcing **only** the host
container's own `os.environ` (`connect:526-532`, called with `os.environ` at `connect:1060`).
Stage 1 touches zero files under `omnigent/` — confirmed achievable; every mechanism is
configuration + `vps-infra`, not fork code. The credential strip is safe: the server needs no
provider or git credential for default operation (below).

But three technical facts require spec changes before freeze:

1. **The server's isolation axis is `owner`, not `workspace`, and every workspace in this
   design shares one owner.** Owner-scoping — the only authorization the shared server
   enforces — is therefore a no-op *between* workspaces. This is decisive for probe (a) and is
   proven from code, not inferred.
2. **The runtime MCP-edit route writes agent bundles straight into the commingled DB**, so the
   spec's "lint the `agents` table" guard, scoped as a git-time file lint, does not cover the
   vector it names.
3. **Probe (b) as written targets a code path outside the chosen topology** and would pass
   vacuously; the real forwarding path is elsewhere (and is clean).

None of these is fatal to Stage 1's stated container/registry/gitconfig deliverables. They are
scope/criterion corrections plus one binding-trigger call (human ruling 3).

---

## Probe verdicts

### (a) Host-tunnel blast radius — **the narrow question passes; the architectural question FAILS**

**Narrow claim (as literally worded): a host's tunnel token cannot enumerate or act on other
hosts' sessions.** CONFIRMED by code:
- The host tunnel is a *host→server control channel*. The host process is a passive executor:
  the server sends it `launch_runner`/`stop_runner` frames and the host reports results
  (`htunnel:434-472`). The host has no path to query, enumerate, or act on the sessions table —
  it only ever handles runners the server explicitly told it to launch.
- A server-managed launch token is scoped to exactly one `host_id`: `managed.host_id != host_id
  → close 4004` (`htunnel:149-152`). A leaked managed token cannot register or reach any other
  host.
- Cross-owner host takeover is refused before `accept()` (`htunnel:178-203`) with the
  `IntegrityError` on the UNIQUE `host_id` as backstop.
- Runner listing/status are owner-scoped so other users' runners are invisible
  (`rtunnel:240,266-273`).

**Architectural question (the one the spec's risk section and Stage 2b actually care about):
does the shared server prevent a session for workspace A from being placed on / reading across
workspace B?** NO — and this is the load-bearing finding. Session-create authorizes the target
host through exactly one gate:

```
# _host_launch.py:74-79  (resolve_host_owner)
host = host_store.get_host(host_id)
if host is None: raise 404
if user_id is not None and host.owner != user_id: raise 403 "not your host"
return host
```

called from the create path at `sessions:6192-6208`. There is **no workspace dimension** in
this check — only `owner` equality. In the workspace-layer design every host (personal,
client-A, client-B) is owned by the **same** human identity, so `host.owner == user_id` is true
for *all* of them. A raw `POST /v1/sessions` can bind a "personal" session's runner to the
client host, or vice-versa, and the server will not stop it. Kernel isolation still holds
*physically* — a runner on host-B genuinely cannot mount host-A's volume — so the failure mode
is **wrong-identity placement** (a session runs with the wrong workspace's credentials / git
identity / filesystem), not cross-kernel exfiltration. AC2 ("client host cannot read personal's
volume") stays green while the boundary it implies (a session *stays on* its workspace's host)
is unenforced.

Worse: `resolve_host_owner` **skips the owner check entirely when `user_id is None`**
(`hlaunch:63-64,77` — "When user_id is None (auth disabled) the check is skipped"). If the VPS
runs single-user / auth-disabled (`OMNIGENT_LOCAL_SINGLE_USER=1`, or no auth provider), *any*
session binds *any* host with zero control-plane check — "convention" becomes "nothing at all."

**Conclusion:** Per human ruling 3 ("If Step-5 probe (a) fails: Stage 2b is pulled into the
immediate successor task"), the architecturally-relevant reading of probe (a) **fails** — the
control plane provides no cross-workspace isolation among same-owner hosts. Stage 2b should be
pulled forward.

**LIVE-PROBE PENDING:** which auth mode the production VPS runs (`OMNIGENT_AUTH_PROVIDER` /
`OMNIGENT_LOCAL_SINGLE_USER` in the `vps-infra` deploy env — profile open-unknown 3). This
decides whether the residual control-plane guard is "owner-only (weak but present)" or "absent."
It cannot be established from this repo; it must be read from `vps-infra` or a live
`GET /v1/info` before freeze.

### (b) Allowlist env forwarding — **CONFIRMED clean, but the spec probes the wrong file**

`_build_runner_env` (`connect:487-538`) is an **allowlist** over `base_env`, forwarding only
`_RUNNER_ENV_ALLOWLIST` + prefix matches + `HARNESS_CREDENTIAL_ENV_VARS` + operator-named
`OMNIGENT_RUNNER_ENV_PASSTHROUGH` extras (`connect:520-532`). Its `base_env` is the host
process's own `os.environ` (`connect:1060`). For the chosen topology — an externally-run host
container holding one workspace's env file — this means a workspace runner inherits **only that
container's** environment. There is **no server-global leak path** into a workspace runner.
CONFIRMED per-container.

However, the spec's probe (b) text says "verify no server-global leak via `managed_hosts.py`
env injection." `mhosts` (`:43,49,54,65` etc.) injects **server** env-var *names* into
**server-managed sandboxes** — the `host_type="managed"` provision path where the server spawns
the sandbox. The chosen architecture uses **external** host containers registered against the
shared server, not managed sandboxes, so that injection code never runs for these workspaces.
Probe (b) as written inspects a path outside the deployment topology and passes vacuously. The
substantively correct probe is `_build_runner_env`, done here, and it is clean. (This matches
devils-advocate MINOR 8, with the resolution that the real path is verified-good.)

**LIVE-PROBE PENDING:** a live `env` dump inside a running workspace runner would prove the
allowlist actually filters as analyzed (no ambient inheritance via a misconfigured
`docker run`/compose `environment:` block that bypasses `_build_runner_env`). Code cannot see
the compose file (it lives in `vps-infra`).

### (c) `workspace_scope()` read-side filtering — **CONFIRMED wired at the store layer; fails-open as the panel found**

The read-side filtering the spec wants for Stage 3 **is implemented** and would work if
activated. Every partitioned store filters on `current_workspace_id()`:
`conversation_store/sqlalchemy_store.py` has 70 such filter sites (`:637,840,922,964,1031,…`);
`host_store.py:239-240,278,365`; and policy/comment/file/permission/agent stores likewise. The
mechanism is a `ContextVar` bound by `workspace_scope()` (`models:71-83`), read via
`current_workspace_id()` (`models:61-68`).

The gap is exactly as the design panel ruled: (1) nothing in the `omnigent/` package ever calls
`workspace_scope()` — it is bound only by tests, so the request middleware that would set a
non-zero id does not exist in this fork; (2) the default is `0` (`models:46,56-58`) and every
existing row is stamped `0`, so activating filtering without first migrating personal off `0`
and rejecting `0` leaks silently (fail-open). So Stage-3 read filtering is **feasible in
principle** — the per-store enforcement is real and pervasive — but requires the middleware +
the id-0 migration as hard preconditions, matching the spec's Stage-3 gate.

**LIVE-PROBE PENDING (per spec, and I concur):** a live smoke test — bind `workspace_scope(1)`,
write, then read under `workspace_scope(2)` and confirm zero rows — has never executed in this
fork. Static analysis confirms the SQL predicate is present at every read; only a run proves no
unfiltered read path (e.g. a raw `session.get` on a non-partition key, or a join that drops the
predicate) leaks across. This is out of scope for Stage 1 and correctly deferred.

---

## Findings ranked by severity

**CRITICAL-1 — Owner-scoping is not workspace-scoping; the shared server enforces neither
control-plane nor data-plane isolation between same-owner workspaces.** Evidence: `hlaunch:77`
(host auth = owner equality, skipped when `user_id is None`); session listing is owner-scoped
and all workspaces share one owner + `workspace_id=0` (`models:46`), so `GET /v1/sessions`
returns every workspace's sessions commingled. The isolation the server *does* provide (owner)
is orthogonal to the isolation the spec *needs* (workspace). This is the single most important
technical fact for the whole task and it is why AC2 can be green while the goal ("nothing
crosses that boundary by default") is unmet at the server layer. Kernel isolation of
volumes/env/networks is genuine and holds; the *control plane that decides which kernel
boundary a session lands in* is owner-blind. → pull Stage 2b forward (ruling 3).

**MAJOR-2 — The runtime MCP-edit route persists secrets into the commingled `agents` table; the
spec's lint does not cover it.** Evidence: `mcp_route` supports `source: "inline"` (`:48`) and
`_mutate_bundle` (`:185-250`) rewrites the bundle, `artifact_store.put` + `agent_store.update`
(`:249-250`) — a live API write into the DB-backed agent store, which carries `workspace_id=0`
(commingled). `expand_env=agent.session_id is None` (`:100,257`) keeps `${VAR}` refs unexpanded
for *session* agents, but nothing stops a caller inlining a **literal** secret into
`headers`/`env`. The spec's guard (`spec:80-84`) is a git-time **file** lint over filesystem
bundles; this vector is a runtime write straight to the DB. The guard as scoped is
after-the-fact at best. (Confirms devils-advocate MAJOR 5 with the exact write path.)

**MAJOR-3 — Probe (b) is mis-targeted for the chosen topology.** As above: `managed_hosts.py`
injection is the managed-sandbox path, unused by external host containers. If left as the
freeze-blocking probe, it certifies a code path the deployment never exercises. Re-scope it to
`_build_runner_env` + the actual compose `environment:`/`env_file:` wiring in `vps-infra`.

**MINOR-4 — The credential strip (AC3) is feasible; the server needs no provider/git
credential by default — but note two live-only holders.** The only server-side LLM caller,
smart routing, is opt-in: gated on `OMNIGENT_SMART_ROUTING=1` **and** a configured `server_llm`
(`cli.py:3040`). Title synthesis is pure string manipulation, no LLM (`entities/conversation.py:
264-`). So stripping provider keys and `GIT_TOKEN` from the server env does not break default
operation. Two caveats: (i) enabling `OMNIGENT_SMART_ROUTING` later would re-introduce a
server-held provider credential (workspace-neutral, but present); (ii) the strip must **not**
remove server-infra secrets the server does need — `DATABASE_URL`, OIDC/cookie secrets — which
are out of the "provider credentials / git tokens" scope but must be named explicitly so the
`vps-infra` change does not over-reach. **LIVE-PROBE PENDING:** the actual server env on the VPS
(which of these vars are set) lives in `vps-infra` and was not read here (profile open-unknown 2).

**MINOR-5 — AC1 "≤30 min, alpha test literally performs this" has a build-dependency and an
execution-locus problem.** "Copy compose stanza + create env file" is trivial only if
deliverable #1 ships *parameterized templates* (compose stanza, env-file, registry entry) — and
templating is an acceptance property, not stated as a construction requirement of #1
(`spec:95` vs `spec:129`). If #1 ships a personal-specific stanza, "copy + adapt" is the
non-trivial work whose triviality is asserted. Separately, the templates live in `vps-infra`
and the "no restart of the shared server" execution needs the live VPS — which this repo cannot
drive and which has a load-hang history. Feasible, but the templating must be named as a
construction requirement and the alpha test's execution locus (which box, whose access) settled.
(Confirms devils-advocate MAJOR 7.)

**INFO-6 — Validate script (AC6) is implementable against the real API surface.** It would
read `GET /v1/hosts` (host id + owner + online) and `GET /v1/sessions` (host_id per session) —
both exist and are owner-scoped, so a single owner-token run sees all workspaces' rows, which is
correct for a drift check. Cross-check registry `host_id`/session bindings against live state,
fail non-zero on mismatch. No blocker. To also cover MAJOR-2 it would additionally need to scan
`agents`-table bundle blobs for literal secrets — which the spec does not currently state.

**INFO-7 — Compose/volume/env architecture fits the 7GB box; concurrency is the real limit.**
The `host` Dockerfile target exists (`deploy/docker/Dockerfile:188`), and the deploy pattern
(server + postgres + volumes in `deploy/docker/docker-compose.yaml`) extends cleanly with a
per-workspace host service. An **idle** host container is cheap (host process only). The 7GB
ceiling is set by concurrently **active runners** (harness processes), which the design caps
only per-container via `mem_limit` — there is no cap on total cross-workspace runner
concurrency. Given the MEMORY.md load-hang history, the escalation doc should state a
concurrent-runner budget, not just per-container limits.

---

## Confirms / contradicts vs devils-advocate

- **BLOCKER 1 / MAJOR 4 (isolation protects the omnigent-host plane, not the code-server plane
  the user actually uses):** CONFIRMED from the code side. `_build_runner_env`
  (`connect:487-538`) and the volume/env/network isolation are real and correct **for the
  runner plane**. My CRITICAL-1 is the server-layer companion: even *on* the omnigent plane, the
  control plane that assigns sessions to hosts is owner-blind. Both point at the same root — the
  isolation built is orthogonal to the isolation the goal needs. I do not adjudicate the
  code-server workflow question (that is architecture/scope, not feasibility), but the code
  confirms the premise: nothing in `omnigent/` governs the code-server process, and code-server
  spanning `/opt/work/*` is one Unix user over all volumes.
- **MAJOR 5 (env-refs lint misses the runtime MCP write):** CONFIRMED and sharpened — see
  MAJOR-2 with the exact `_mutate_bundle` → `artifact_store.put` → `agent_store.update` path
  and the `expand_env` nuance.
- **MINOR 8 (probe b may be a no-op):** CONFIRMED — see MAJOR-3 — with the resolution that the
  substantively-correct path (`_build_runner_env`) is verified clean, so the credential-strip
  substance holds even though the named probe is vacuous.
- **MAJOR 7 (triviality circular / unprovable where the review sits):** CONFIRMED — see
  MINOR-5.
- **MAJOR 6 (ruling 6 vs Stage-3 id-0 contradiction):** this is a governance/logic
  contradiction, not a feasibility question; I do not re-adjudicate it. Code note only: it is
  real that every existing row is `workspace_id=0` (`models:46`; confirmed by the store filters
  all defaulting to `0`), so both statements bind the same rows — the contradiction is
  well-founded.
- **On the specific items the prompt flagged:** (i) the user's real workflow plane being
  code-server rather than omnigent hosts — the *code* is consistent with that (nothing in
  `omnigent/` touches code-server; the isolation is entirely on the host/runner plane); (ii) the
  runtime MCP route into the `agents` table — CONFIRMED as a live, DB-persisting, commingled
  write path (MAJOR-2).

---

## Required spec changes (before freeze)

1. **Re-scope probe (a)'s success criterion.** State that the host *tunnel token* is not the
   blast-radius vector (verified inert); the vector is same-owner control-plane session
   placement (`hlaunch:77`). Under ruling 3 this reading fails → pull Stage 2b into the
   immediate successor task, and record the VPS auth-mode as a freeze-blocking LIVE-PROBE
   (owner-only vs check-absent).
2. **Re-scope probe (b)** from "`managed_hosts.py` env injection" to "`_build_runner_env` +
   the actual `vps-infra` compose `environment:`/`env_file:` wiring," since the chosen topology
   uses external hosts, not managed sandboxes.
3. **Close MAJOR-2:** either forbid `source: "inline"` MCP writes for workspace sessions, or
   make the guard scan `agents`-table bundle blobs at runtime (not a git-time file lint), or
   name it an accepted residual risk under the data-at-rest gate. As written the guard does not
   cover the vector it names.
4. **AC1:** name per-workspace *templating* (compose stanza, env-file, registry entry) as a
   **construction** requirement of deliverable #1, and settle the alpha test's execution locus
   (which box, whose access) given this repo cannot drive the live VPS.
5. **AC3 (credential strip):** explicitly enumerate what stays (server-infra secrets:
   `DATABASE_URL`, OIDC/cookie) vs what goes (provider keys, `GIT_TOKEN`), and note that
   enabling `OMNIGENT_SMART_ROUTING` would re-introduce a server-held provider credential.
6. **Escalation doc:** add a total concurrent-runner budget for the 7GB box, not only
   per-container `mem_limit`.
