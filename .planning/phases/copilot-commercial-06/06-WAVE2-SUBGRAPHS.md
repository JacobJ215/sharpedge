# Wave 2 — LangGraph subgraphs (deferred)

**Wave 2** is the follow-up milestone after Wave 1 ships: replace the env-only soft router with **LangGraph subgraph** boundaries when metrics justify the refactor.

**Phase 6 follow-up:** promote from soft router to **separate compiled subgraphs** (Sports, PM, Portfolio, optional AppGuide) when:

- Flat tool count or median latency exceeds agreed SLO (define in prod metrics).
- Soft router (`COPILOT_ROUTER_FOCUS`) proves insufficient — e.g. repeated wrong-domain tool calls in eval set.

**Subgraph design sketch:** shared `MessagesState` + parent checkpoint `thread_id`; child graphs invoke with subgraph namespace in checkpoint config (LangGraph docs). **Executor:** implement only after Wave 1 ships and metrics justify the refactor.
