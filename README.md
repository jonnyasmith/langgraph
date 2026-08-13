# langgraph-apps

A collection of small LangGraph applications, each a standalone agentic graph.

| Directory | Project |
| --- | --- |
| [`router/`](router/) | Deterministic state machine that routes prompts between a local and a hosted model |
| [`researcher/`](researcher/) | Cyclic research loop that re-searches until its findings are sufficient |
| [`gatekeeper/`](gatekeeper/) | Deployment agent that pauses for human approval before destructive commands |
| [`builder/`](builder/) | Subgraph pipeline that generates and refines SvelteKit components |
| [`triage/`](triage/) | Multi-agent supervisor that triages incoming GitHub issues |

Each directory has its own README. Projects are independent; pick whichever you care about.

The progression is deliberate: each app adds one LangGraph mechanic on top of the last — schemas, then cycles, then persistence, then composition, then multi-agent orchestration. See [`plan.md`](plan.md) for what each app must demonstrate.

Nothing is implemented yet. Code will land in those directories as each project is built.
