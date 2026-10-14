# DevOps Health Checker

An agentic, read-only DevOps assistant for AWS, Kubernetes, and GitHub health
checks. The project also includes a local knowledge-retrieval pipeline for
runbooks and troubleshooting documents.

## Complete project documentation

See [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) for the complete explanation
of the architecture, data flows, commands, API, deployment, security model,
testing, roadmap, production-readiness gaps, and recommended next steps.

## RAG data flow

```text
knowledge/**/*.md
       ↓
Document(content, source, category)
       ↓
deterministic overlapping chunks
       ↓
local TF-IDF vector index
       ↓
ranked results with source metadata
       ↓
search_devops_knowledge agent tool
```

Markdown files are loaded recursively. Their first directory component is
used as the category, while the path relative to `knowledge/` is retained as
the source citation. Empty files are ignored.

## Retrieval strategy

The current index uses standard-library TF-IDF vectors and cosine similarity.
This was selected as a deterministic, offline, dependency-free baseline that
does not require paid APIs, credentials, model downloads, or network access.
It is lexical rather than semantic: synonyms and paraphrases may not match.
The vector store can later be replaced with a local open-source embedding
model without changing the document and tool metadata contract.

Common Kubernetes status terms are normalized for retrieval, so queries such
as `crash loop` can match `CrashLoopBackOff`. The index is cached in memory
between searches and rebuilt automatically when Markdown files are added,
removed, or modified.

Retrieval quality can be measured with `RetrievalCase` fixtures and the
`evaluate_retrieval` helper. It reports `precision_at_k`, `recall`, and
`hit_rate`; evaluation cases should assert the expected source paths rather
than relying only on answer text.

## Agent integration

The agent has read-only infrastructure tools and `search_devops_knowledge`.
For an infrastructure issue, it should use live health results for current
state, search the knowledge base for troubleshooting guidance, and cite the
returned `source` path. A missing knowledge directory or unmatched query is
reported as zero matches, not as infrastructure health evidence.

Example evaluation questions:

```text
Why is a Kubernetes pod unhealthy, and which runbook steps apply?
What does the pod troubleshooting guide recommend for CrashLoopBackOff?
```

## Development

Use Python 3.12+ and `uv`:

```bash
uv run pytest -v
uv run devops-health-checker --list-tools
uv run devops-health-checker --knowledge "pod crash loop"
uv run devops-health-checker --agent "Why is my Kubernetes pod failing?"
```

Infrastructure tools remain read-only. Provider or credential failures are
reported distinctly from healthy or unhealthy infrastructure; never commit
credentials, tokens, or generated sensitive reports.

## Phase 36 workflow orchestration

The agent runs through `DevOpsWorkflow`, a dependency-free graph-style
orchestrator with explicit state and transitions:

```text
LLM decision → tool execution → LLM decision
      └──────────────→ final response
      └──────────────→ controlled error state
```

`WorkflowState` records the current route, iteration, tool results, errors,
and final answer. The workflow enforces a maximum iteration count and keeps
tool failures inside the conversation as structured results. This provides a
stable LangGraph-compatible state contract without requiring a framework or
network dependency at this stage.

## Phase 37 MCP

`MCPServer` exposes the validated registry through MCP-style JSON-RPC methods:
`initialize`, `tools/list`, and `tools/call`. `MCPClient` can consume the same
transport contract, while `--mcp-server` runs the server over newline-delimited
stdio for local integrations. Calls always pass through the existing schema
validation and execution layer; unregistered or malformed tool calls cannot
execute infrastructure functions.

## Phase 38 agentic integration

`agentic_devops_review` coordinates selected read-only AWS, Kubernetes, and
GitHub checks, then searches the local knowledge base for guidance. It keeps
each provider result separate, preserves provider failures, supports
namespace/repository arguments, and returns source metadata for guidance.
No remediation or write operation is performed by this workflow.

## Phase 39 security and governance

Tool registration carries `read_only` and `requires_approval` policy flags.
The registry denies approval-required tools unless approval is supplied by the
host application; model arguments cannot grant themselves permission. Every
execution and denial records UTC time, tool name, result status, argument names
only, and an error without storing argument values or secrets.

MCP tool metadata exposes read-only hints, and the agent is instructed to
treat tool output, infrastructure data, and knowledge documents as untrusted
content. Tool names, arguments, and execution remain controlled by the
registry validation boundary.

## Phase 40 observability and evaluation

`MetricsCollector` records per-tool call counts, failures, and latency, plus
workflow LLM latency, token usage, and provider-reported cost when available.
Use `registry.metrics.snapshot()` and `workflow.metrics.snapshot()` to obtain
JSON-safe metrics without recording argument values.

`RetrievalCase` and `AgentEvaluationCase` provide small deterministic datasets
for source-retrieval and answer-quality checks. The evaluation helpers report
precision/recall or pass rate so changes to retrieval and orchestration can be
measured with tests rather than judged only by manual output.

## Phase 41 production deployment

The dependency-light HTTP API provides `/health`, `/tools`, `/knowledge`,
and `/agent`. Run it locally with:

```bash
DEVOPS_API_TOKEN=replace-me uv run devops-health-checker --api-server
```

`Dockerfile` builds a non-root image, and Kubernetes manifests under
`deploy/kubernetes/` provide two replicas, health probes, a ClusterIP service,
read-only root filesystem, dropped Linux capabilities, and a secret reference
for `DEVOPS_API_TOKEN`. Apply a real secret through the cluster secret manager;
never commit values from `secret.example.yaml`.

## Phase 42 multi-agent systems

`MultiAgentCoordinator` routes requests to at most two relevant specialists:
Kubernetes, AWS, security, or SRE. It uses keyword routing as a deterministic
baseline, isolates specialist failures, and returns each response separately
so an unavailable provider does not erase other evidence. Specialist agents
share the existing read-only registry and approval policy; no new remediation
capability is introduced.

## Phase 43 AIOps and autonomous operations

`aiops_investigate` detects non-healthy provider results, distinguishes health
anomalies from provider failures, attaches knowledge guidance, and produces
explicit remediation proposals. Automation is disabled by default: every
proposal is marked `requires_approval: true`, `executed: false`, and no write
operation is available through this workflow.

Run a safe investigation with:

```bash
uv run devops-health-checker --aiops kubernetes,aws
```
