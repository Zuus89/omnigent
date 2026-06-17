// Repo-level round-robin reviewer assignment (no org team needed).
//
// Acts as the "default" owner for PRs that CODEOWNERS did NOT already route:
// if a PR has no requested reviewer, assign one maintainer from a load-balanced
// pool. The pool is derived FROM .github/CODEOWNERS at runtime -- the union of
// per-area owner handles -- so maintainers who aren't assigned anywhere in
// CODEOWNERS are intentionally excluded from review rotation.
//
// Fairness is stateless: we pick the candidate with the fewest CURRENTLY open
// review requests (random tie-break), so load self-balances without a tracking
// file/issue.
//
// Invoked from auto-assign-reviewer.yml via actions/github-script.
module.exports = async ({ github, context, core }) => {
  const fs = require("fs");
  const { owner, repo } = context.repo;
  const pr = context.payload.pull_request;
  if (!pr) {
    core.info("No pull_request in payload; nothing to do.");
    return;
  }
  if (pr.draft) {
    core.info("Draft PR; skipping.");
    return;
  }

  // Don't pile on: if CODEOWNERS (or anyone) already requested a reviewer/team,
  // this default rotation stays out of the way.
  const already =
    (pr.requested_reviewers || []).length + (pr.requested_teams || []).length;
  if (already > 0) {
    core.info(`PR already has ${already} requested reviewer(s)/team(s); skipping default rotation.`);
    return;
  }

  // Build the pool from CODEOWNERS: handles on path rules only, excluding
  // org/team handles (which contain a "/") and the PR author.
  const text = fs.readFileSync(".github/CODEOWNERS", "utf8");
  const pool = []; // original-case logins, de-duped
  const seen = new Set();
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line.startsWith("/")) continue; // skip comments, blanks, and the `*` line
    for (const tok of line.split(/\s+/).slice(1)) {
      if (tok.startsWith("@") && !tok.includes("/")) {
        const login = tok.slice(1);
        const key = login.toLowerCase();
        if (!seen.has(key)) {
          seen.add(key);
          pool.push(login);
        }
      }
    }
  }

  const author = (pr.user && pr.user.login ? pr.user.login : "").toLowerCase();
  const candidates = pool.filter((u) => u.toLowerCase() !== author);
  if (candidates.length === 0) {
    core.info("No eligible candidates in the CODEOWNERS pool; skipping.");
    return;
  }

  // Current open-review load per candidate (stateless fairness signal).
  const openPRs = await github.paginate(github.rest.pulls.list, {
    owner,
    repo,
    state: "open",
    per_page: 100,
  });
  const load = Object.fromEntries(candidates.map((u) => [u.toLowerCase(), 0]));
  for (const p of openPRs) {
    for (const r of p.requested_reviewers || []) {
      const l = (r.login || "").toLowerCase();
      if (l in load) load[l] += 1;
    }
  }

  // Lowest load first; random tie-break within the lowest tier.
  const min = Math.min(...candidates.map((u) => load[u.toLowerCase()]));
  const lowest = candidates.filter((u) => load[u.toLowerCase()] === min);
  const pick = lowest[Math.floor(Math.random() * lowest.length)];

  try {
    await github.rest.pulls.requestReviewers({
      owner,
      repo,
      pull_number: pr.number,
      reviewers: [pick],
    });
    core.info(`Assigned @${pick} (open-review load ${min}; pool of ${candidates.length}).`);
  } catch (e) {
    core.warning(`Could not request @${pick}: ${e.message}`);
  }
};
