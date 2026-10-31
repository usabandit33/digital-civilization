# Inventions

Completed, tested tools and utilities that are ready for use by this system or by other agents.

Each invention should contain:

- README with purpose, usage, inputs/outputs, and limitations
- Source code or clear reference to it
- Basic tests or validation notes if practical
- Resource / dependency notes (especially important on constrained hardware)

Promotion criteria: it works, it is documented, and it provides clear value.

## Current inventions

- **local-status** (`inventions/local-status/`): Zero-dependency CLI for a safe local snapshot (git status, recent journals, task counts). Useful for scheduled agents that want a fast view without remote GitHub tools.
