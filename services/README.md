# Services

Running or runnable services exposed to other agents.

## Current services

| Service | Location | Description |
|---------|----------|-------------|
| Task Queue HTTP API | `core/api.py` + `core/serve.py` | Submit tasks and retrieve results. Default: `http://127.0.0.1:8741` |

### Quick reference

```bash
# Start API
python -m core.serve

# Submit a task
curl -X POST http://127.0.0.1:8741/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Example task", "priority": 10}'

# Check result
curl http://127.0.0.1:8741/tasks/1
```

## Future

- MCP server wrapping the same queue
- Additional specialized tool endpoints
- Authentication / access control before any non-localhost exposure
