# Domain vocabulary

What you need in order to steer work on this solution. Each app README states the problem and the LangGraph mechanics that app exercises.

| Domain | What to understand | Where it shows up |
| --- | --- | --- |
| State schema and reducers | State is a `TypedDict` updated by returning deltas; reducers (`add_messages`) decide how deltas merge. Nodes are pure functions and never mutate state in place | `router/`, all apps |
| Edges: static, conditional, cyclic | A static edge is a fixed transition; a conditional edge is a routing function returning the next node; cycles are legal, so exit conditions to `END` must be explicit and bounded | `researcher/`, `triage/` |
| Tool binding | Tools bound to a model inside a node, with the tool call and its result flowing back through state rather than around it | `researcher/`, `builder/` |
| Checkpointers and durability | Persisted state per thread, so a run can dehydrate to disk and rehydrate later; the unit of resume is the thread, not the process | `gatekeeper/` |
| Interrupts and resume | `interrupt()` pauses mid-node and yields to a human; `Command(resume=...)` injects the answer back into state without blocking a thread | `gatekeeper/` |
| Subgraphs and state isolation | A compiled graph used as a node, with private state that does not leak into the parent schema | `builder/`, `triage/` |
| Multi-agent orchestration | Supervisor topology: one node routes, workers do the work; parallel branches accumulate into shared state | `triage/` |
