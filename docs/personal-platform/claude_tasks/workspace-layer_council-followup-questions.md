---
type: handoff
title: "Workspace layer — council follow-up questions for the vps-infra session (A2′ scoring)"
task: "workspace-layer"
status: final
created: "2026-07-16"
related_decisions: ["council/workspace-isolation-amendment.md", "workspace-layer_vps-infra-ruling.md"]
---

# Handoff — council follow-up for the vps-infra Data Architect

The council on the isolation-model amendment SPLIT its decision
(`council/workspace-isolation-amendment.md`): the Workspace↔Omnigent-server decoupling is
ready for human enactment, but the A2-as-default amendment is gated on scoring an option
absent from the original ruling's set, plus a threat-model restatement and one observable
trigger. Council missing-item 3 (CLAUDE_CONFIG_DIR full-state isolation) is now RESOLVED
empirically on the product side: a scratch config dir reports "Not logged in" — the CLI
does not see the global credentials; docs confirm `.credentials.json` lives under the
config dir on Linux. Cost: per-workspace login ceremony (isolation-positive).

The ready-to-paste prompt for the vps-infra session is mirrored in the pm's message to
the human (2026-07-16). Its asks, in summary:

1. Score **A2′ — per-workspace Unix uids inside the single code-server container** vs A2
   (convention) and A1-default: image/provisioning cost (user creation, dir ownership),
   the launch question (code-server runs as `coder`; how do agent processes run as
   `ws-<client>` — sudoers rules per workspace? wrapper?), whether kernel
   permission-denies give the council's required observable trigger, and day-2 ops.
2. Restate the threat model to include the resident prompt-injection vector (autonomous
   web-enabled agents run daily with the operator's uid) — or state plainly that plain
   A2's default plane has no boundary against the platform's own daily activity.
3. Rule on the Omnigent/Postgres stack (council MAJOR 8 vs de condition 3) — **context
   changed 2026-07-16:** the human declared collaboration a post-Phase-2 objective
   (`collaboration-vision.md`): a second user joins shared projects with their OWN
   harness credentials via their own registered host — which is exactly the machinery
   this stack provides (multi-user auth, session_permissions, live status, 11
   harnesses). Decommissioning is therefore no longer a neutral RAM reclaim; it
   forfeits the collaboration engine. Decide keep-vs-stop with that weight, plus the
   unchanged counterweights (runtime secret-persistence vector into the shared agents
   table; ~240MB idle on a box whose A1 valve needs RAM).
4. Confirm the A1 escalation capacity bound is documented as **≤1 escalated workspace**
   on current hardware.
