# Agent Instructions

This project uses **bd** (Beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready                         # Find available work
bd show <id>                     # View issue details (requirements live here)
bd update <id> --status in_progress  # Claim work
bd update <id> --notes "..."     # Record validation/results
bd close <id>                    # Complete work
bd sync                          # Sync issues <-> git
```

## Working Agreement (Beads-First)

Beads issues are the source of truth. Before implementation starts, the issue should include:

- Goal/context and scope/non-goals
- Acceptance criteria (testable)
- Likely files to touch
- Validation commands to run
- Dependencies (use Beads deps so `bd ready` is accurate)

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT  
complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. File issues for any follow-ups
2. Run quality gates (tests/lint/build) for changed code
3. Update Beads issue status/notes
4. Push to remote:

   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```

5. Verify working tree is clean and branch is up to date

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
