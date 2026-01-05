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

**When the user says "let's land the plane"**, follow this clean session-ending protocol:

1. **File beads issues for any remaining work** that needs follow-ups
2. **Ensure all quality gates pass** (only if code change were made) - run tests, linters, builds as applicable. File P0 issues for any failures.
3. **Update Beads issues** - close finished work, update status
4. **Sync the isseu tracker carefully**: Work methodically to ensure both local and remote issues merge safely. This may require pulling, handling conflicts (sometimes accepting remote changes and re-importing), syncing the database, and verifying consistency. Be creative and patient - the goal is clean reconciliation where no issues are lost.
5. **Clean the git state**: - Clear old stashes and prune deap remote branches:

   ```bash
   git stash clear         # Remove old stashes
   git remote prune origin # Clean up deleted remote branches
   ```

6. **Verify clean state**: Ensure all changesa re committed and pushed, no untracked files remain.
7. **Choose a follow-up issue for next session**
   - Provide a promptyfor the use to give yo you in the next session.
   - Format: [Continue work on <issue id>: <short description>] [Brief context about what's been done and what's next]"

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
