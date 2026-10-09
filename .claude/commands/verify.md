---
description: Run the Meraki gate (backend pytest, frontend tests and build)
allowed-tools: Bash(cd backend*), Bash(cd frontend*), Bash(pytest*), Bash(npm test*), Bash(npm run build)
---
Run in order and stop at the first failure:

1. `cd backend && pytest`
2. `cd frontend && npm test`
3. `cd frontend && npm run build`

Report pass/fail per step with failing output verbatim.
