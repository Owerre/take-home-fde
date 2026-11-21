# Architecture and implementation state

At M1 only the solid profiling path below exists. No DuckDB artifact, app, agent,
evaluation harness or Anthropic integration has been built. The dashed paths
are specified future work, contingent on M1 approval.

```mermaid
flowchart LR
    CSV["Private unchanged CSV"] --> PROFILE["scripts/profile_data.py — stdlib"]
    PROFILE --> REPORT["docs/data_quality.md — aggregates"]
    CSV -. after M1 .-> RAW["DuckDB raw + lineage"]
    SEEDS["Versioned aliases / prices / FX"] -.-> STG
    RAW -. set-based SQL .-> STG["Typed deduplicated staging"]
    STG -.-> AUDIT["Rejects / duplicates / flags"]
    STG -.-> MARTS["Invoices + account snapshots; no emails"]
    Q["CLI question"] -.-> AGENT["QueryAgent / Anthropic — metadata only"]
    AGENT -. validated MetricRequest .-> COMPILER["MetricCompiler — allowlisted templates"]
    COMPILER -. bound SQL .-> MARTS
    MARTS -. read-only bounded query .-> ANSWER["Local result / SQL / evidence / caveats"]
```

Planned module boundaries: `app/config.py`, `models.py`, `errors.py`,
`pipeline.py`, `metrics.py`, `agent.py`, `cli.py`, `evaluations.py`, with SQL in
`sql/`, seeds in `seeds/`, fixtures/reference SQL/case definitions in `evals/`.
Entry points remain thin. The builder owns writable connections and artifact
replacement; query execution opens short-lived restricted read-only connections.
No frontend, vector store, deployment, API, cache or speculative infrastructure.
