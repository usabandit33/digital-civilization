# Architecture Map

This map is a lightweight orientation guide, not a second source of truth. The authoritative details remain in the linked files and the code.

## System flow

```text
human approval
      |
      v
projects/ task queues  --->  core/ queue + API  --->  agents/ execution logic
      |                              |                    |
      v                              v                    v
journal/ decisions              memory/ records      inventions/ reusable tools
      |                              |                    |
      +------------------------------+--------------------+
                                     |
                                     v
                              services/ local interfaces
                                     |
                                     v
                              system/ deployment + health
```

## Directory responsibilities

| Area | Role | Start here |
|---|---|---|
| `constitution.md` | Binding safety and operating rules | Read before changing behavior |
| `identity.md` | Project identity, hardware, and role | Understand intended operating context |
| `objectives.md` | Long-term goals and Phase 1 priorities | Decide whether work is useful |
| `AGENT.md` | Session procedure and agent conduct | Follow the survey, test, and review workflow |
| `projects/` | Active work, planning, and task queues | Select one scoped task |
| `core/` | Queue and local API implementation | Trace task execution |
| `agents/` | Agent roles and execution logic | Understand orchestration |
| `memory/` | Structured persistent records and checks | Inspect durable state |
| `journal/` | Append-only project history and decisions | Read recent work before acting |
| `inventions/` | Tested reusable capabilities | Reuse before creating a new tool |
| `services/` | Local endpoints exposed to other agents | Check interfaces and bind assumptions |
| `system/` | Deployment, health, and host integration | Check runtime constraints |
| `experiments/` | Temporary or exploratory work | Treat as non-promoted work |

## Typical change path

1. Read the constitution, identity, objectives, and latest journal entries.
2. Choose one open task from `projects/project-backlog.md` or an approved published task.
3. Inspect existing code and open review branches before creating a duplicate.
4. Implement the smallest reversible change on a feature branch.
5. Add tests, documentation, and resource notes where applicable.
6. Run focused validation, then open a pull request for human review.
7. Do not merge or promote work without approval.

## Safety boundaries

- The repository is the system of record. Externalize decisions in journal entries.
- Prefer local, deterministic, standard-library solutions on the target laptop.
- Do not introduce credential handling, unrestricted network exposure, root access, or irreversible actions without explicit human approval.
- Treat tools as read-only unless a task explicitly requires a safe, documented mutation.
- Keep the map descriptive. If the structure changes, update this file in the same reviewed change.

## Related references

- [Constitution](../constitution.md)
- [Objectives](../objectives.md)
- [Agent guidance](../AGENT.md)
- [Project backlog](project-backlog.md)
- [Inventions catalog](../inventions/README.md)
- [Services catalog](../services/README.md)
