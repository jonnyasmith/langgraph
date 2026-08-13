# Solution Wide Instructions

## Routing — read only what the task needs, when it needs it

### Working targets

- Working on the local routing engine, `StateGraph` schemas, reducers, or static edges → `router/AGENTS.md`
- Working on the autonomous research loop, conditional edges, tool binding, or cycle exit conditions → `researcher/AGENTS.md`
- Working on the deployment approval gate, checkpointers, `interrupt()`, or resume semantics → `gatekeeper/AGENTS.md`
- Working on the modular application builder, subgraphs, or private state isolation → `builder/AGENTS.md`
- Working on the Kanban issue triage team, supervisor routing, or parallel worker nodes → `triage/AGENTS.md`

### This context

- Solution-wide vocabulary → docs/agents/domain.md
- System-wide decisions → docs/adr/
- Issue tracker (issues live as GitHub issues on `jonnyasmith/langgraph`, via the `gh` CLI) → docs/agents/issue-tracker.md
- Triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) → docs/agents/triage-labels.md
- Scoping which LangGraph app to build next, or what a numbered app must demonstrate → plan.md
