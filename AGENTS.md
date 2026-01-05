# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd list               # List issues
bd show <id>          # View issue details
bd create             # Create a new issue
bd edit <id>          # Edit issue fields in $EDITOR
bd comments <id>      # Add/view implementation notes
bd dep                # Manage dependencies (blocks/blocked-by)
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Vibe Coding Workflow (Planning → Implement → Handoff)

This repo treats **Beads issues as the single source of truth** for work planning, handoff, and completion.

### Agents

- **Planning agent**: turns an idea into Beads issues with acceptance criteria and dependencies.
- **Handoff agent**: ensures the next issue is *actually implementable* (tight scope, clear tests, unblocked).
- **Implement agent**: claims 1 ready issue and lands it end-to-end (code + validation + Beads updates).

Custom agent specs live in:

- `.github/agents/Planning.agent.md`
- `.github/agents/Handoff.agent.md`
- `.github/agents/Implement.agent.md`

### Beads-first handoff contract

For any issue that should be “implement-ready”, capture (in the issue’s description/design/notes):

- **Goal / context** (what + why)
- **Scope / non-goals** (what NOT to do)
- **Acceptance criteria** (bulleted, testable)
- **Likely files** to touch
- **Validation commands** (e.g. `pytest tests/test_fetchers.py`)
- **Dependencies** (use Beads `blocks` links so `bd ready` is accurate)

### Typical loop

1. **Plan** (Planning agent)
   - Create/update issues and dependencies.
   - Ensure each implementable issue has acceptance criteria + validation steps.

2. **Select next work** (Handoff agent)
   - Choose a `bd ready` issue (usually highest-priority, smallest scope).
   - If underspecified, tighten the issue before implementation.

3. **Implement** (Implement agent)
   - `bd update <id> --status in_progress`
   - Make code changes + run relevant tests
   - Record validation results in the issue notes
   - `bd close <id>` when done

4. **Repeat**
   - Any new follow-ups discovered during implementation become new Beads issues.


## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT  
complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```

5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
