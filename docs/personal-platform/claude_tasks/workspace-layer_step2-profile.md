# Workspace layer — Step-2 state profile (da)

- **Date:** 2026-07-14
- **Task:** workspace-layer
- **Status:** final
- **Author role:** da (Data / QA Analyst)
- **Method:** static read-only profiling of the fork at `/home/coder/repos/omnigent`, branch `main`, **HEAD `9e3942b8`** (verified via `git rev-parse HEAD`; the session-start git-status snapshot listing `9bc4d9c9` as top commit is stale — live HEAD is `9e3942b8`). Synthesis of 5 parallel reader passes (domain-model, identity-credentials, web-ui, git-binding, api-and-constraints), with three cross-reader contradictions re-verified directly (see "Contradictions" section). No live database or running server was exercised (see "Open unknowns").

---

## Summary (what exists today, one screen)

1. **There is no entity above a session.** The API/UI "session" is a row in the `conversations` table (`SqlConversation` / domain `Conversation`). There is no `projects`, `workspaces`, `folders`, `groups`, `org`, `tenant`, or `team` table, and no `project_id`/`folder_id`/`org_id`/`tenant_id`/`team_id`/`account_id` column anywhere (`grep` over `db_models.py`).
2. **"Project" is a label, not an entity.** A project exists only while ≥1 session carries a `conversation_labels` row with key `omni_project` (`PROJECT_LABEL_KEY = "omni_project"`). Grouping is purely user-defined; the design explicitly makes "no automatic grouping by repo/workspace/host" a NON-GOAL. Two sessions in the "same" project can point at different repos.
3. **"Workspace" has two unrelated meanings.** (a) `conversations.workspace` (`String(2048)`, nullable, immutable) = the absolute filesystem path one session's runner `cd`'s into — this is exactly the brief's "workspace = filesystem path per session." (b) `workspace_id` (`BigInteger`, leading member of every table's composite PK) = a **Databricks tenant partition key**, default `0`, **inert in this fork** (`workspace_scope()` is never called in the `omnigent/` package). Neither is a client-company identity/credential boundary.
4. **Identity is per-user and per-session, never per-workspace.** Multi-user by design: `users`, `account_tokens`, a `session_permissions` junction `(user_id, conversation_id) → level`, and `hosts.owner`. Sharing is per-session; there is no grouping of identity or credentials above the session.
5. **Credentials are process-global env vars + a per-user secret store.** Provider keys, `GIT_TOKEN`/`GIT_USERNAME`, etc. reach every harness as forwarded environment variables; the stored form is ambient env or the `omnigent` OS-keychain / `~/.omnigent/secrets.json` (0600). No credentials/secrets DB table exists. The backend **never** sets git author/committer identity.
6. **MCP grants are per-session-agent**, stored in the agent bundle spec (`tools/mcp/<name>.yaml`), not a persistent OAuth-grant store; secret headers/env are excluded from the safe API summary.
7. **The brief's premise is confirmed by every dimension** (backend, web UI, API, git binding, chronicle): Omnigent's "workspace" is a per-session path, and no Workspace-as-identity-boundary spanning multiple projects exists anywhere.

---

## Domain model

**Session storage.** An API/UI "session" and a "conversation" are the same object under two names — the API is `/v1/sessions`, the table is `conversations`.
- `omnigent/db/db_models.py:431` — `__tablename__ = "conversations"`; DB model `SqlConversation`, domain entity `Conversation`.
- Storage is SQLAlchemy; default is a single local SQLite file `<data_dir>/chat.db` (`data_dir` = `OMNIGENT_DATA_DIR` else `~/.omnigent`), with Postgres/MySQL/Cloudflare-D1 supported by the same models. `omnigent/cli.py:776-792` — `_default_db_uri()` → `f"sqlite:///{_local_data_dir() / 'chat.db'}"`; docstring "one local DB — and so one accounts admin — per machine." `omnigent/db/utils.py:224` — `is_sqlite = db_uri.startswith("sqlite")`.

**Session row fields.** `id` (str PK, e.g. `conv_…`), `created_at`/`updated_at`, `title` (`String(768)`, `db_models.py:444`), `kind` (default/sub_agent), spawn-tree pointers `parent_conversation_id` + `root_conversation_id` (`db_models.py:449-469`), `agent_id`, `runner_id`, `host_id`, per-session overrides (reasoning_effort, model_override, cost_control_mode_override, harness_override), `external_session_id`, `session_state`/`session_usage` JSON blobs, `terminal_launch_args`, `workspace` (`String(2048)`, nullable), `git_branch` (`String(255)`, nullable), `archived`.
- `omnigent/db/db_models.py:520` — `workspace: Mapped[str | None] = mapped_column(String(2048), nullable=True)`; L517-519 "Absolute path on the host where the runner cd's. Required when host_id is set… this is the worktree directory path."
- `omnigent/entities/conversation.py:191-216` — domain `Conversation` dataclass fields mirror these but carry **no** `workspace_id` at the domain layer.
- There is exactly **one** path/cwd field on a session: `workspace`. The only extra partition key on the row is `workspace_id`.

**No entity above session.** The domain-entity registry (`omnigent/entities/__init__.py:3-36`) exports Account, AccountToken, Agent, Comment, Conversation, ConversationItem, StoredFile, Policy, SessionPermission, SessionResourceView, Pagination — no Project/Workspace/Folder/Group.
- Full enumeration of `*_id` columns (`grep -nE '_id: Mapped' omnigent/db/db_models.py`) yields only: agent_id, conversation_id, external_session_id, host_id, parent_conversation_id, response_id, root_conversation_id, runner_id, sandbox_id, session_id, user_id, workspace_id — **no** project_id/folder_id/group_id/org_id/tenant_id/team_id/account_id (`grep -oiE 'project_id|folder_id|group_id|org_id|tenant_id|client_id|account_id|team_id'` → empty).
- Above-session structures are all **derived**: (1) the agent-spawn tree via `parent_conversation_id`/`root_conversation_id` (`db_models.py:375-382` — groups a root session with its sub-agent sub-sessions, not multiple user projects); (2) `host_id` (which machine); (3) the `workspace` path string (one directory per session).
- `conversation_labels` is **per-conversation** key/value metadata (`SqlConversationLabel`, `db_models.py:675-721` — "One row per (conversation, label-key) pair") — it labels individual conversations, it does not group them.

**Table inventory (12 tables).** `grep -n "__tablename__" omnigent/db/db_models.py`: agents, files, users, account_tokens, session_permissions, conversations, conversation_items, conversation_labels, comments, policies, hosts, user_daily_cost. No credentials/secrets table, no projects table.

---

## Identity & credentials today

**Server is multi-user by construction; single-user "local" is an explicit opt-in.**
- `users` table (`SqlUser`, `db_models.py:200-237`): `id` = email in header/OIDC modes, chosen username in accounts mode, or reserved `"local"` in single-user; plus `is_admin`, `password_hash`.
- `account_tokens` (`SqlAccountToken`, `db_models.py:240-298`): invite + magic-login tokens for self-serve registration / signing a CLI session into the web UI — **login tokens, not provider OAuth grants**.
- `session_permissions` (`SqlSessionPermission`, `db_models.py:301-352`): junction `(user_id, conversation_id) → level` (1=read, 2=edit, 3=manage; `level IN (1,2,3,4)`), plus a `"__public__"` sentinel for public read. **This is the only real sharing/tenancy boundary and it is per-user, per-session.**
- `user_daily_cost` per-user rollup; `hosts.owner` = the connecting user id (`db_models.py:942-944`).
- Auth: three providers via `OMNIGENT_AUTH_PROVIDER` — `header` (default, reads X-Forwarded-Email from a trusted proxy), `oidc`, `accounts` (username/password, first-user-is-admin, invite-only, the "OSS-CUJ-v2 default") (`omnigent/server/auth.py:4-20`). Header mode rejects unauthenticated requests **401 UNLESS** `OMNIGENT_LOCAL_SINGLE_USER=1` → reserved `"local"` user (`auth.py:11-14`, `46-58`; `_LOCAL_SINGLE_USER_ENV` set only by managed local-server spawn paths, "never by deployed multi-user servers").

**Config layering (the only per-scope config path).** Two layers merged, no named-identity dimension.
- Repo-root `config.yaml` is a 57-byte sample: `llm:\n  model: databricks-claude-haiku-4-5\n  profile: oss` (entire file) — not a credential store.
- `omnigent/config.py:11-13` — GLOBAL user config `~/.omnigent/config.yaml` (path overridable via `OMNIGENT_CONFIG_HOME`) + LOCAL project config `./.omnigent/config.yaml` (relative to CWD). `config.py:43-45` — `load_effective_config()` returns `{**load_global_config(), **load_local_config()}`, **local wins**. So a per-directory `.omnigent/config.yaml` can override provider selection per working directory — the only per-scope layer, and it is **per-CWD-directory, not a named identity**.
- Config stores **no secret values** — only references: `api_key_ref: env:<VAR>` or `keychain:<name>`, or inline `api_key: $VAR` (`omnigent/onboarding/provider_config.py:1-27`).

**Credentials reach harnesses as process-global env vars.**
- `omnigent/host/connect.py:424-441` — fixed allowlist `_BASE_HARNESS_CREDENTIAL_ENV_VARS`: `ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL, ANTHROPIC_BEDROCK_BASE_URL, AWS_BEARER_TOKEN_BEDROCK, CLAUDE_CODE_OAUTH_TOKEN, CODEX_ACCESS_TOKEN, OPENAI_API_KEY, OPENAI_BASE_URL, GEMINI_API_KEY, GIT_TOKEN, GIT_USERNAME`, plus `OMNIGENT_`-prefixed aliases, forwarded host→runner when present (`connect.py:405-423`: "these are credentials the host owner sets PRECISELY so their runners can use them… forwarding them is the intent").
- Stored form: ambient shell env, **or** the "omnigent secret store" — OS keychain (keyring service name `"omnigent"`) else `~/.omnigent/secrets.json` at mode 0600 (`omnigent/onboarding/secrets.py:11-23, 47-50, 110-125`), referenced from config by `keychain:<name>`.
- `omnigent/claude_native.py:326-333` — deliberately **refuses** a raw `ANTHROPIC_API_KEY` in the terminal env; "the credential must reach Claude Code via the helper, not the environment" (apiKeyHelper).
- `omnigent/claude_launcher.py:54-58` — `OMNIGENT_CLAUDE_LAUNCHER` selects a per-process wrapper launcher (e.g. `isaac`).
- Managed sandboxes: `omnigent/server/managed_hosts.py:44-46` — `env: [OPENAI_API_KEY, GIT_TOKEN]` lists **server** env var NAMES injected into **every** sandbox (server-global).
- Copilot: `omnigent/onboarding/copilot_auth.py:10-17` — `copilot: {github_token_ref: keychain:copilot | env:GH_TOKEN}`, resolved from the same secret store.
- **Everything is keyed per-user / per-host; nothing is keyed to a per-workspace / per-client identity.**

**MCP servers & OAuth grants — per-agent, no persistent grant store.**
- Declared per-agent inside the agent bundle as `tools/mcp/<name>.yaml` → `MCPServerConfig` (`omnigent/spec/types.py:914-923`): `name, transport ('http'|'stdio'), url, headers (repr=False), databricks_profile, command, args, env, description, timeout, retry`.
- HTTP auth = static headers (e.g. `Authorization: Bearer …`) or `databricks_profile`, which mints an OAuth bearer at connection time from a `~/.databrickscfg` profile — **no token persisted in YAML** (`spec/types.py:884-901`; `omnigent/tools/mcp.py:929-940`).
- stdio auth = an `env` dict overlaid on the parent process env: `omnigent/tools/mcp.py:1048-1052` — `env = strip_runner_auth_secrets(os.environ) | self.config.env` (inherits the full process environment plus author-declared vars like `GITHUB_TOKEN` via `${VAR}` refs).
- **No persistent MCP OAuth-grant store.** The only persistent token file, `~/.omnigent/auth_tokens.json` (`omnigent/cli_auth.py:1-4`), holds the omnigent **server** login (session JWTs / Databricks pointer records) keyed by server URL — not MCP grants.
- `omnigent/server/routes/session_mcp_servers.py:1` — session-scoped MCP management route edits the agent bundle spec, not a credential store.

**Git identity — backend sets none.**
- `rg -ni 'GIT_AUTHOR_NAME|GIT_AUTHOR_EMAIL|GIT_COMMITTER_NAME|GIT_COMMITTER_EMAIL|config user.(name|email)' omnigent/ --type py` → **no matches**. The backend never sets git author or committer identity.
- Git access credentials are left to the environment: `GIT_TOKEN`/`GIT_USERNAME` feed the sandbox host image's git credential helper (`omnigent/host/connect.py:414-419`) so the agent's own fetch/push authenticates — a server-global env-name allowlist, not per-project.
- The only git-identity refs in `omnigent/server/routes/auth.py:686,716` are the GitHub OAuth profile email used for **login**, not commits.

**No per-scope credential mechanism.** Confirmed by every reader: no credentials/secrets table; `workspace_id` scopes rows not credentials; `conversations.workspace` is a path carrying no identity; the nearest per-scope hook is the per-CWD `./.omnigent/config.yaml` (provider selection only, same global secret store) and per-agent `executor.auth` (`spec/types.py:481-548` — a per-AGENT provider/databricks/api_key pin resolving to the same global providers + secret store).

---

## Web UI structure (`web/src`)

**Sidebar session list — TanStack Query, not Zustand.**
- `web/src/hooks/useConversations.ts:238-240` — `useInfiniteQuery({ queryKey: ["conversations", searchQuery, includeArchived], … })` against `GET /v1/sessions`.
- The Zustand store (`web/src/store/chatStore.ts`) holds only per-conversation message/streaming state (`ActiveResponse` in `store/types.ts`); `ls web/src/store` → `chatStore.test.ts, chatStore.ts, terminalActivity.ts, types.ts` — no session-list store.
- Row model `Conversation` (`useConversations.ts:49-56`) "Mirrors the server's `SessionListItem` / `ConversationObject` shape": `id, object, title, labels: Record<string,string>, owner, host_id, workspace, agent_id, status, archived`, etc.

**Pinned = localStorage, independent of the server.** `web/src/shell/sidebarNav.ts:4` — `PINNED_CONVERSATION_IDS_STORAGE_KEY = "omnigent:pinned-conversation-ids"`; ordered by pin sequence not `updated_at` (`sidebarNav.ts:139-153`, `orderByPinnedSequence`); pinning floats a session **out of** its project into a flat Pinned section; pins outside the loaded page are backfilled via `GET /v1/sessions/{id}` (`usePinnedConversationBackfill`).

**"Project" is a NAME (label), never a path.**
- `web/src/hooks/useConversations.ts:664-670` — `PROJECT_LABEL_KEY = "omni_project"`, stored in `conversation_labels`.
- `web/src/shell/Sidebar.tsx:987-992` — groups by exact name match `c.labels?.[PROJECT_LABEL_KEY] === name`.
- `useConversations.ts:672-680` — `useProjects()` fetches `GET /v1/sessions/projects` returning a plain `string[]`; a project folder's members come from `GET /v1/sessions?project=<name>`.
- `openapi.json:7505` — "Projects are implicit: they exist while at least one session has a `conversation_labels` row with `key="omni_project"`."
- This is **separate** from `Conversation.workspace`, which IS a filesystem path: `useConversations.ts:62-68` — "Absolute path the runner cd's into… `null` for sessions not bound to a host workspace." A session has both a `workspace` (path) and, optionally, a `project` (name label); the sidebar grouping uses the name label, never the path.

**Background / sub-agent visibility exists (V1 finding CONFIRMED).**
- `web/src/shell/SubagentsPanel.tsx:48` imports `RunningDot`, renders it at `:523`; `web/src/components/RunningDot.tsx:3-11` is an animated `Loader2Icon animate-spin` (testid `running-dot`).
- Session activity computed from `session.status`: `SubagentsPanel.tsx:317-333` maps `launching`→Launching, `running`→Working, else Idle; `SessionStateBadge.tsx:37-41` renders the sidebar-row running dot.
- Right "Workspace" rail exposes a `subagents` tab: `web/src/shell/railTabs.ts:8` — `RightRailTab = "files" | "subagents" | "terminals" | "todos" | "browser"`; `SessionRail.tsx` lists the main thread plus each sub-agent/child session.

**No workspace/tenant/org switcher above projects.**
- Full sidebar hierarchy: a two-tab split ("mine" vs "shared") then flat sections Pinned / Projects(folders) / Sessions / Archived (`Sidebar.tsx:954-1009`). No entity groups projects.
- `grep -rniE '\btenant\b|\borg\b|workspace.?switch|switch.?workspace' web/src` → only auth "account" usages (`useMe.ts` "current account (GET /auth/me)", Settings "Account" section, MembersPage "every account on the server").
- `useRecentWorkspaces.ts:1-9` — localStorage recent **directory paths** keyed per `host_id` ("paths are host-specific… `host_id -> …absolute paths`").
- The only identity concept is "Account" = the current server user (`GET /auth/me`). Identity boundaries today are **per-host** (`host_id`) and **per-session** (`owner`, plus `/v1/sessions/{id}/permissions/{target_user_id}`). Brief's premise CONFIRMED for the web UI.

**Sidebar data sources.** Four HTTP endpoints + one WebSocket:
- `GET /v1/sessions` (cursor-paginated, 20/page, `order=desc sort_by=updated_at`, optional `search_query`, `include_archived`, `project=<name>` filter — `useConversations.ts:199-211`; `openapi.json:7440-7442`).
- `GET /v1/sessions/projects` (project name list).
- `GET /v1/sessions?project=<name>` (a project folder's members).
- `GET /v1/sessions/{id}` (single-session pin backfill).
- **Live updates:** `WS /v1/sessions/updates` (`web/src/lib/sessionUpdatesSocket.ts:1-4` — "Replaces the sidebar's 4 s HTTP poll of `GET /v1/sessions`"), patching the TanStack cache in place; on disconnect a 45s safety poll (`DISCONNECTED_STREAM_REFETCH_INTERVAL_MS`). Mutations `PATCH`/`DELETE /v1/sessions/{id}` invalidate `['conversations']`, `['projects']`, `['project-sessions']`.

---

## Git binding reality

**The binding is written entirely onto the conversation (session) row at create time — no project layer in the chain.**
1. `omnigent/server/schemas.py:1308-1322` — `SessionCreateRequest` carries `agent_id`, `host_id`, `workspace: str|None`, `git: SessionGitOptions|None`, `labels`, `host_type`, `parent_session_id` — **no project field**.
2. `omnigent/server/routes/sessions.py:14094,14153` — `POST /sessions` → `create_session` → `_create_session_from_existing_agent`.
3. `sessions.py:12389-12398` — `canonical_workspace = body.workspace`; when `host_id` is set, `_validate_session_workspace` canonicalizes it and boundary-checks it against the agent's `os_env.cwd` (`_workspace_validation.py:181-307`, rejecting if `not _is_subpath_of(canonical_workspace, canonical_boundary)` at L278 — a single-directory pick bounded by the agent's cwd, no grouping of repos).
4. `sessions.py:12425-12433` — when `body.git` is set, `_create_session_worktree` proxies `host.create_worktree` (host runs `git worktree add -b`); the worktree path **replaces** `canonical_workspace` and `git_branch = created_worktree.branch`.
5. `sessions.py:12480-12491` — `conversation_store.create_conversation(…, host_id=, workspace=canonical_workspace, git_branch=git_branch, …)` persists them.
6. DB columns: `workspace String(2048) NULL`, `git_branch String(255) NULL`, with `CheckConstraint("host_id IS NULL OR workspace IS NOT NULL", name="ck_conversations_workspace_required_for_host")` (`db_models.py:520,525,537-540`). `workspace` is "Immutable after creation" (`entities/conversation.py:160-170`).
7. `omnigent/runner/app.py:8613-8615` — the runner does **not** receive `workspace` in the POST body; it lazily fetches the session workspace from the server on first call and `cd`'s there.

**"Git bound per-chat not per-project" — BOTH V1 claims CONFIRMED.**
- Per-chat, not per-project: `workspace`/`git_branch` are columns on `conversations`, set per-session at create. No projects table, no `project_id` column anywhere. The only "project" is the `omni_project` label (`omnigent/stores/conversation_store/__init__.py:78-83` — `PROJECT_LABEL_KEY = "omni_project"`).
- Same project → different repos: the label is stored independently of `workspace`; nothing links them. `designs/SESSION_PROJECTS_SIDEBAR.md:41-42` lists as a NON-GOAL "No automatic grouping by repo/workspace/host — grouping is purely user-defined"; `:31` "One project per session. No nesting."; `:77-78` "A session is in a project iff it has a (key=\"omni_project\") row." So two sessions carrying `labels={omni_project:'Acme'}` may hold any two unrelated `workspace` paths — **definitional, not incidental**. (`SESSION_PROJECTS_SIDEBAR.md` is Status: Draft, but the label mechanism IS implemented: store constant, `list_session_projects` route at `sessions.py:14472`, web tests reference `PROJECT_LABEL_KEY`.)

**What git operations the backend performs — worktree lifecycle + read-only inspection only, never commit/push/diff.**
- Worktree lifecycle, **on the host** (server has no filesystem; proxies `host.create_worktree`/`host.remove_worktree`): `omnigent/host/git_worktree.py:392-397,453-461` — `git worktree add -b`, `worktree list --porcelain`, `worktree remove --force`, `branch -D`, plus `rev-parse`/`fetch`, `cwd = source repo`.
- Read-only change detection, **in the runner**, scoped to a `watch_path`: `omnigent/runtime/filesystem_registry.py:707,798,869-870` — `git status --porcelain --untracked-files=all`, `git status --porcelain -- <path>`, `git show HEAD:<path>`.
- No `commit`/`push`/`diff`/`add` in server or runtime — commits/pushes are the agent/harness's job via tools/MCP; `omnigent/policies/builtins/github.py` is a guardrail over the GitHub MCP push, not a backend git operation.

**Two sessions at the same directory share the filesystem view and on-disk files.**
- `omnigent/runner/app.py:8607-8635` — `_resolve_session_fs_registry` returns the **same** `FilesystemRegistry` for any session whose resolved workspace equals the runner's workspace, creating a distinct per-session registry only when the path differs.
- `omnigent/runtime/filesystem_registry.py:5-9` — `git status --porcelain` "reflects all working-tree changes (from any process, not just agent tool calls). Results are not scoped to a session." So two sessions in one directory see each other's uncommitted edits.
- `omnigent/host/git_worktree.py:381-382` — worktree mode refuses to reuse an existing worktree because "two sessions sharing one working tree would clobber each other." Nothing at the DB layer prevents two conversation rows from storing the same `workspace` path.

**Immutability.** `workspace` and `git_branch` are immutable after creation: `PATCH /v1/sessions` mutates reasoning_effort/model_override/cost_control/archived/labels but not `workspace` or `git_branch`.

---

## API surface & attach points (`openapi.json`, 3.2.0, 60 paths)

**12 top-level resource roots** (`grep` over paths block): `/api/version, /health, /v1/agents, /v1/harnesses, /v1/hosts, /v1/info, /v1/me, /v1/policies, /v1/policy-registry, /v1/runners, /v1/sessions, /v1/sharing`. There is **NO** `/v1/workspaces`, `/v1/credentials`, `/v1/identities`, or top-level `/v1/projects`.

**Session endpoints:** `GET /v1/sessions` (list, paginated); `POST /v1/sessions` (create, bound to an agent); `GET|PATCH|DELETE /v1/sessions/{session_id}`; `POST /v1/sessions/{source_id}/fork`; `GET|PUT /v1/sessions/{session_id}/agent`; `POST /v1/sessions/{session_id}/switch-agent`.

**Project endpoints:** `GET /v1/sessions/projects` (`list_session_projects…`, `openapi.json:7505` — "Return all project names for the authenticated user"; projects implicit); plus the `project` query filter on list (`openapi.json:7440-7454`).

**MCP / credential endpoints:** `GET|POST /v1/sessions/{session_id}/agent/mcp-servers` and `PUT|DELETE …/mcp-servers/{server_name}` — MCP servers (with secret headers/env) are **session-agent-scoped**. `MCPServerSummary` is the "Safe subset… Secret-bearing fields (`headers`, `env`) are intentionally excluded" (`openapi.json:1769-1771`).

**Host / filesystem (path-bearing):** `GET /v1/hosts`, `GET /v1/hosts/{host_id}`, `POST /v1/hosts/{host_id}/directories`, `GET /v1/hosts/{host_id}/filesystem[/{path}]`, `POST /v1/hosts/{host_id}/runners` (`launch_runner…`), `GET /v1/hosts/{host_id}/worktrees`. Session resource/env endpoints under `/v1/sessions/{session_id}/resources/environments/…`.

**Where the path/workspace dimension surfaces today** (the attach points, stated as fact):
- `SessionCreateRequest` (`schemas.py:1308-1322`, `1240-1246`) — `workspace: str|None`, "Required when host_id is set; the server validates that the path… falls within the agent's `os_env.cwd` boundary." **No** `workspace_id`/identity/credential-scope field on create.
- `LaunchRunnerRequest` (`openapi.json:1756-1765`) — **requires** `workspace`, "Absolute path on the host machine to use as the runner's working directory… When `git` is set, this is interpreted as the source repository directory."
- `SessionResponse` / `SessionListItem` (`openapi.json:4880-4890`) — `workspace`, "Absolute path on disk where the runner cd's."
- `SessionGitOptions` (`openapi.json:3491-3492`) — "Requires `host_id`… and therefore `workspace`, which is interpreted as the source repository directory."
- Every `/v1/hosts/{host_id}/filesystem[/{path}]`, `/directories`, `/worktrees` endpoint operates directly on host filesystem paths. **None** of these has a scope parameter above the filesystem-path level.

**`workspace_id` — dormant Databricks tenant partition, not in the API.**
- `db_models.py:42-46` — `DEFAULT_WORKSPACE_ID = 0` ("the single-workspace / unassigned sentinel"); `:56-68` — `_current_workspace_id: ContextVar[int]` default 0, `current_workspace_id()`.
- `db_models.py:48-52,119-126,433` — per-table comment "Tenant partition key: Databricks workspace id owning this row (0 = default). Part of the PK"; "OSS leaves this at the default (single-workspace 0); a multi-tenant deployment (e.g. universe) sets it per request from the authenticated context (via `workspace_scope` in middleware)."
- Migration `r1a2b3c4d5e6_add_workspace_id_to_all_tables.py:1-54` (Create Date 2026-07-07) — adds `workspace_id` to all twelve tables and extends each PK to `(workspace_id, <existing pk cols>)`. `_TABLE_PKS` lists: agents, files, users, account_tokens, session_permissions, conversations, conversation_items, conversation_labels, comments, policies, hosts, user_daily_cost.
- **Re-verified:** `grep -rn 'workspace_scope' omnigent/` → only the `def` (`db_models.py:72`), a re-export (`db/__init__.py:13,26`), and a comment (`db_models.py:52`). **No caller in the `omnigent/` package** (only `tests/db/test_workspace_scope.py`). Every row in this fork is stamped `workspace_id = 0`. Not exposed in the API (absent from `SessionCreateRequest`, `SessionResponse`; no `/v1/workspaces` endpoint).

**Where credentials/identity actually live (three unscoped-by-workspace layers).**
1. Provider API keys / model credentials = process env vars, server-global (`OMNIGENT_ANTHROPIC_API_KEY`, `OMNIGENT_OPENAI_API_KEY`, `OMNIGENT_CREDENTIAL` — `omnigent/harness_capabilities.py:73`; OIDC secrets, `DATABASE_URL`, cookie secret injected via env — `omnigent/server/server_config.py:13-18`).
2. MCP OAuth/secret grants = per-session-agent (route above; `MCPServerSummary` excludes secret fields).
3. `account_tokens` = invite/magic-login tokens only (`db_models.py:240-247`), carrying the same dormant `workspace_id = 0`.
- **No place today groups git identity + model credentials + MCP OAuth grants under one boundary spanning multiple projects.**

**Server boot config — all server-global (one server = one config).**
- CLI flags on `omnigent server` (`omnigent/cli.py:2758-2828`): `--host` (default 127.0.0.1), `--port/-p`, `--database-uri` (default `sqlite <data-dir>/chat.db`, "machine-global so `server` and `run` share one admin"), `--artifact-location`, `--config/-c` (YAML), `--execution-timeout`, `--agent` (repeatable), `--open/--no-open`, `--admin-password`.
- YAML config (`server_config.py:8-11,45-55`) from `OMNIGENT_CONFIG` env or `<data_dir>/config.yaml`: non-secret settings (admins, allowed domains, policy modules, artifact location, host/port, database URI). Secrets stay in env.
- Large env surface (`rg -no 'OMNIGENT_[A-Z_0-9]+|AP_[A-Z_0-9]+'` → 190+ names): per-provider credentials, auth/OIDC (`OMNIGENT_OIDC_CLIENT_SECRET`, `OMNIGENT_ACCOUNTS_COOKIE_SECRET`), storage (`OMNIGENT_DATABASE_URI`, `OMNIGENT_ARTIFACT_URI`), harness (`OMNIGENT_HARNESSES`), per-runner knobs (`OMNIGENT_RUNNER_ISOLATE_SESSION`, `OMNIGENT_RUNNER_ENV_PASSTHROUGH`, `AP_WORKSPACE`). All single-valued server-global today; no per-workspace override path exists.

---

## Documented constraints (from plan.md + chronicle)

**Chronicle V1 step-3 live-UI findings (verbatim, `docs/personal-platform/project_chronicle.md`).** These are ground-truth live-UI observations, taken verbatim from the chronicle (not re-verified against a running instance in this pass):
- Finding 1 (`:109-113`): "**Omnigent's \"workspace\" is our \"Project\", not our \"Workspace\".** It's a filesystem path on a session, not an identity/credential boundary spanning multiple projects. Project → Session grouping does exist in the live UI. Our Workspace layer (multiple projects under one identity — git/model/MCP credentials) does not exist anywhere in Omnigent — **Phase 2 is still fully needed**."
- Finding 2 (`:114-116`): "**Creating a new project from a tablet or phone is effectively not possible today** in the live UI."
- Finding 3 (`:117-123`): "**Git/repo binding lives on the chat/session, not on a persistent project entity.** Today two sessions under the \"same\" Omnigent workspace (= our project) can point at different repos. This contradicts Phase 3's core rule (\"every project always has a git connection, no exceptions\")… a Project must own its git binding, and every Session under it inherits that binding rather than choosing its own."
- Data-quality note: the V1 step-3 entry appears **twice** in the chronicle (`:75-97` truncated mid-sentence at ~L96 "always has a git" vs the complete copy `:98-133`) — duplication, not a semantic difference.

**Phase 2 constraints (locked, `docs/personal-platform/plan.md`, verbatim).**
- `:198-202` — "A **workspace** is a full identity context, not just a folder: its own git identity, its own Claude/model credentials, its own MCP OAuth grants, its own filesystem — isolated by container (or equivalent OS-level boundary). Nothing crosses this boundary by default. Today there is exactly one workspace (personal)."
- `:204-206` — "Inside a workspace, the hierarchy goes **Workspace → Project → Session**: a workspace holds several projects (repos), and each project holds many sessions (chats) — not one session per project."
- `:224-232` — KB three-tier (Global → Workspace → Project, narrowest wins): Workspace KB "shared across every project inside one workspace, but not visible to other workspaces"; Global KB "mounted read-only into every workspace… Written to **only** via the promotion flow… never auto-synced."
- `:210-214` — "**Background agent visibility** — a view of what's currently running elsewhere on the server, not just the session in front of you" (Phase 2 candidate).

**Phase 3 credential-vs-resource rule (locked, verbatim).**
- `:277-284` — "Every external connection (GitHub, Azure DevOps, Atlassian/Jira, Databricks, Microsoft 365, Tailscale, a tracker) splits into two layers… 1. **The credential/identity** (OAuth grant, token, account) — always **workspace**-scoped. Authenticated once, inherited by every project inside that workspace. 2. **The specific resource used through that connection** (which repo, which Jira project, which Databricks warehouse, which OneDrive folder) — always **project**-scoped, selected using the credential already inherited from the workspace."
- `:286-290` — "Git looks like an exception but isn't… `memory` is the one true exception: there's no shared credential involved, it's pure isolation, so it's project-scoped end to end with no workspace layer at all."
- `:267-273` — "every project always gets a git connection, no exceptions, only the remote host is a per-project user choice… `memory` (required, must be a **per-project isolated path**… never share one memory file across projects, that collapses isolation)."

---

## Contradictions between readers (checked)

No **substantive semantic** contradictions surfaced — all five readers corroborate the central claims (two unrelated "workspace" meanings; no project/workspace/group entity; label-based implicit projects; process-global credentials with no per-workspace boundary; `workspace_id` dormant at 0; backend sets no git identity). Three cross-reader discrepancies were re-verified directly:

1. **Design-doc existence — RESOLVED in favor of git-binding.** domain-model left `designs/SESSION_WORKSPACE_SELECTION.md` and `designs/SESSION_GIT_WORKTREE.md` as "cited but not read in this pass" (open); git-binding asserted they "do NOT exist." Re-checked: `ls designs/SESSION_WORKSPACE_SELECTION.md designs/SESSION_GIT_WORKTREE.md` → **"No such file or directory"** for both; `find designs -iname 'SESSION_*'` → only `designs/SESSION_PROJECTS_SIDEBAR.md` (13941 bytes, dated Jul 3). So the code repeatedly cites `SESSION_WORKSPACE_SELECTION.md` / `SESSION_GIT_WORKTREE.md` as SSOT, but **only the code implements them in this fork**; `SESSION_PROJECTS_SIDEBAR.md` is the one that does exist (Status: Draft). No real disagreement — git-binding was right, domain-model simply hadn't checked.

2. **HEAD commit — RESOLVED.** git-binding cited "HEAD 9e3942b8"; the session-start git-status snapshot listed `9bc4d9c9` ("record git push 403 root cause") as top commit. Re-checked: `git rev-parse HEAD` → **`9e3942b8`** ("capture Step-1 briefs — kb-three-tier + secrets-manager"). The live HEAD is `9e3942b8`; the session-start snapshot is stale/mismatched. Profiling was done against `9e3942b8`.

3. **Table count phrasing — not a contradiction.** domain-model says `workspace_id` is on "ALL 12 tables"; api-and-constraints/git-binding say "nearly every table." The migration's `_TABLE_PKS` enumerates exactly 12 tables and adds `workspace_id` to all of them — the count is 12, and all 12 receive it. Reconciled as identical.

---

## Open unknowns (merged, deduped)

1. **No live database / running server was exercised.** This is a static read of source at `/home/coder/repos/omnigent`, branch `main`, HEAD `9e3942b8`. No live `chat.db` exists on this host (`ls ~/.omnigent/` empty, `OMNIGENT_DATA_DIR` unset, `find ~ /opt /home/coder -name chat.db` → none). This box is the dev container holding the clone, not the running VPS (`/opt/omnigent` on `omni-vps`). All schema/field claims come from source + Alembic migrations, not from live rows. Runtime behavior (actual `WS /v1/sessions/updates` payloads, a real two-session-same-dir race, empirical confirmation that all live rows carry `workspace_id=0`) is inferred from code/docstrings, not observed.
2. **Live-state credential files not inspected.** Actual contents of `~/.omnigent/config.yaml`, `~/.omnigent/secrets.json`, `~/.omnigent/auth_tokens.json`, `~/.databrickscfg` were not read on this machine or the VPS — only the code paths that read/write them.
3. **VPS deployment config is out of scope and in a separate repo.** How `GIT_TOKEN` / provider keys are actually populated in the `srv1802750` (`/opt/omnigent`) deployment env lives in the separate `vps-infra` repo (per CLAUDE.md §9) and was not established here. A credential mechanism implemented outside the `omnigent/` Python package (e.g. in `deploy/` Docker entrypoints or `vps-infra`) would not be caught by the greps run here.
4. **The multi-tenant activation path is absent from this fork.** The code that would set a non-zero `workspace_id` (the Databricks/"universe" middleware calling `workspace_scope()`) exists only in comments/docstrings here. Its absence is confirmed; its real request-binding mechanism cannot be profiled from this tree.
5. **The two SSOT design docs the code cites are missing.** `designs/SESSION_WORKSPACE_SELECTION.md` and `designs/SESSION_GIT_WORKTREE.md` do not exist (verified above), so the full intended spec for workspace immutability, the validation steps, and worktree semantics could only be reconstructed from code + docstrings, not read directly. `designs/SESSION_PROJECTS_SIDEBAR.md` (Draft) does exist and was quoted.
6. **UI SDK state-dir path divergence not fully traced.** `sdks/ui/omnigent_ui_sdk/terminal/_config.py:49-60` `state_dir()` returns `Path.home()/'.omnigent'` and does **not** honor `OMNIGENT_CONFIG_HOME`, unlike `config.py`'s `global_config_path()`. Whether `auth_tokens.json` / `secrets.json` paths shift under a sandboxed `OMNIGENT_CONFIG_HOME` was not exhaustively traced across every writer.
7. **Runner co-location precondition not traced end-to-end.** Whether two **different top-level** conversations are ever actually co-located on one runner process (the precondition for sharing the same-path `FilesystemRegistry`) depends on runner-affinity/dispatch behavior (`runner_id` hard affinity) not traced here. Sub-agent children explicitly inherit the parent runner; cross-user / cross-top-level co-location was not confirmed.
8. **Under-documented OpenAPI operations.** `create_session` (`POST /v1/sessions`) and `list_session_projects` (`GET /v1/sessions/projects`) responses are documented as empty `{}` schemas (`openapi.json:7491,7511`); their wire shapes were profiled from the Python model `SessionCreateRequest` (`schemas.py:1195`) instead. The two agree, but the spec is under-documented at these operations. (Also: no JSON parser was available in the sandbox; `openapi.json` was parsed by grep/indentation, so a malformed-JSON edge case could in principle be missed — endpoint/operationId lists were cross-checked against the raw path dump.)
9. **Not every credential-cache surface enumerated.** `account_tokens` is confirmed to hold only invite/magic-login tokens; native-harness on-host credential caches (e.g. `OMNIGENT_CLAUDE_NATIVE_STATE_DIR` contents) were not inventoried — only DB tables, env vars, and MCP-server config paths were profiled.
