# DevOps Health Checker: Complete Project Guide

## 1. Project definition

DevOps Health Checker is a read-only, agentic DevOps assistant for checking
infrastructure health and finding troubleshooting guidance. It combines
provider integrations, a local runbook knowledge base, controlled tool
execution, an optional LLM agent, AIOps investigation, and deployment through
Docker and Kubernetes.

The project is a production-oriented prototype and learning platform. It is
not an autonomous remediation system: current workflows inspect systems and
propose actions, but do not change infrastructure.

## 2. The problem it solves

DevOps and SRE engineers commonly need to answer questions such as:

- Are Kubernetes nodes or pods unhealthy?
- Are AWS EC2 instances available and running?
- Is a GitHub repository reachable and healthy?
- What should be checked when a pod enters `CrashLoopBackOff`?
- Which infrastructure tool and runbook apply to a user question?
- Can an incident be investigated without allowing an AI model to make
  uncontrolled changes?

Without this service, an engineer may need to run several provider-specific
commands, interpret different response formats, and search separate runbooks.
This application provides a common interface and structured results.

## 3. What the system does

```text
User, CLI, REST client, or MCP client
                    |
                    v
        Tool registry and workflow layer
        validation | policy | audit | metrics
                    |
       +------------+-------------+-------------+
       |            |             |             |
       v            v             v             v
   Kubernetes      AWS         GitHub       Knowledge base
   health          EC2         repository   RAG search
                    |
                    v
          Structured result and source metadata
                    |
                    v
       CLI output, API response, or agent answer
```

The LLM is not given direct shell or cloud access. It can request a registered
tool, but the application validates the request and executes only the
registered function.

## 4. Main capabilities

### 4.1 Provider health checks

The provider tools return normalized health results with a status such as
`HEALTHY`, `WARNING`, `CRITICAL`, or `UNKNOWN`.

- Kubernetes checks nodes and pods.
- AWS checks EC2 instance health and state through `boto3`.
- GitHub checks repository information through the GitHub API.

Provider failures are kept separate from infrastructure findings. For
example, an AWS credential failure is not reported as proof that EC2 is
unhealthy.

### 4.2 Tool registry

The registry is the control plane for tool execution. Each tool has a name,
description, input schema, execution function, and policy flags including
`read_only` and `requires_approval`.

Current tools are:

```text
aws_ec2_health
github_repository
kubernetes_health
search_devops_knowledge
agentic_devops_review
aiops_investigate
```

All registered tools are currently read-only.

### 4.3 Validation and safety boundary

Tool calls are validated before execution. The validation layer checks tool
names, required arguments, argument types, and unexpected arguments. Approval
is controlled by the host application; a model cannot grant approval to its
own request.

Audit events record the UTC time, tool name, status, argument names, and error
information without recording argument values or secrets.

### 4.4 Local RAG knowledge base

Markdown runbooks are stored under `knowledge/` and loaded recursively.
Documents receive metadata containing their relative source path and category.
They are split into overlapping chunks and indexed locally with TF-IDF and
cosine similarity.

```text
knowledge/**/*.md
        |
        v
Document(content, source, category)
        |
        v
Overlapping DocumentChunk objects
        |
        v
Local TF-IDF vector index
        |
        v
Ranked results with source and category metadata
```

The current knowledge source is:

```text
knowledge/kubernetes/pod-troubleshooting.md
```

The search implementation is intentionally dependency-free and works without
an embedding API, model download, or network connection. Kubernetes aliases
such as `CrashLoopBackOff` and `OOMKilled` are normalized to improve lexical
matching.

This is a lexical baseline, not full semantic search. It may miss synonyms or
paraphrases and should eventually be replaced or supplemented with an
embedding-based persistent index for a large production knowledge base.

### 4.5 Agent workflow

The agent follows a controlled loop:

```text
User question
     |
     v
LLM chooses a registered tool or answers directly
     |
     v
Application validates the proposed tool call
     |
     v
Tool executes and returns structured data
     |
     v
Result is returned to the LLM for the final answer
```

The workflow records state, route, iteration count, tool results, errors, and
the final response. A maximum iteration count prevents an endless tool loop.
Tool failures remain structured results so the agent can explain what failed
instead of silently treating missing data as healthy.

For infrastructure questions, the intended behavior is to use live provider
results for current state and the knowledge base for troubleshooting guidance.
Knowledge results include the source path so answers can cite the runbook.

### 4.6 Agentic review

`agentic_devops_review` coordinates selected read-only checks and attaches
relevant local guidance. It is useful when one question needs both current
infrastructure state and operational context.

Example flow:

```text
Check Kubernetes
       |
       v
Find unhealthy pod
       |
       v
Search CrashLoopBackOff guidance
       |
       v
Return evidence and recommended investigation steps
```

### 4.7 AIOps investigation

`aiops_investigate` identifies unhealthy provider results, distinguishes
provider failures from real incidents, retrieves guidance, and emits
remediation proposals.

Every current proposal has:

```text
requires_approval: true
executed: false
```

No Kubernetes, AWS, or GitHub write operation is available through this
workflow. This is intentional: investigation and recommendation should be
validated before any future automation is enabled.

### 4.8 Multi-agent routing

The multi-agent coordinator routes a request to up to two deterministic
specialists: Kubernetes, AWS, security, or general SRE. Specialists reuse the
same registry and safety policy. Failures are isolated so one unavailable
provider does not discard other evidence.

This is a controlled specialist-router baseline, not yet a complex autonomous
multi-agent society.

### 4.9 MCP-style access

The project exposes a JSON-RPC, MCP-style interface with `initialize`,
`tools/list`, and `tools/call` methods over newline-delimited stdio. Calls use
the same registry, validation, and execution boundary as the CLI and API.

The current implementation is custom and MCP-compatible in shape. For broad
interoperability, it should later migrate to the official MCP SDK and its
transport conventions.

## 5. Interfaces and commands

Run commands from the `devops-health-checker` directory.

Install dependencies:

```bash
uv sync
```

List tools:

```bash
uv run devops-health-checker --list-tools
```

List input schemas:

```bash
uv run devops-health-checker --list-schemas
```

Run individual health checks:

```bash
uv run devops-health-checker --kubernetes
uv run devops-health-checker --aws
uv run devops-health-checker --github
uv run devops-health-checker --all
```

Search the knowledge base without an LLM:

```bash
uv run devops-health-checker --knowledge "CrashLoopBackOff pod"
```

Ask the LLM agent a question:

```bash
OPENROUTER_API_KEY=replace-me \
  uv run devops-health-checker --agent \
  "Why is my Kubernetes pod failing?"
```

Run a routed specialist assessment:

```bash
uv run devops-health-checker --multi-agent \
  "Check Kubernetes and explain unhealthy pods"
```

Run a safe AIOps investigation:

```bash
uv run devops-health-checker --aiops kubernetes,aws
```

Run the MCP-style stdio server:

```bash
uv run devops-health-checker --mcp-server
```

Run the HTTP API:

```bash
DEVOPS_API_TOKEN=replace-me \
  uv run devops-health-checker --api-server
```

## 6. HTTP API

The API provides:

```text
GET  /health
GET  /tools
POST /knowledge
POST /agent
```

`/health` is a process liveness endpoint. It does not prove that every cloud
provider or LLM dependency is available.

Protected POST endpoints accept a bearer token when `DEVOPS_API_TOKEN` is
configured:

```bash
curl -H "Authorization: Bearer $DEVOPS_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"CrashLoopBackOff pod"}' \
  http://127.0.0.1:18080/knowledge
```

An unauthorized response usually means the token is missing, empty, or does
not match the token loaded by the running process. When using Kubernetes,
retrieve the value from the active Secret and do not replace it with a
placeholder string.

## 7. Configuration and credentials

Project configuration is in `config.yaml`. It currently contains AWS region,
GitHub repository defaults, Kubernetes namespace, and LLM settings.

The LLM implementation currently uses OpenRouter environment configuration,
while the sample YAML still contains Gemini names. These settings should be
unified before production deployment so the configured provider and the actual
client cannot disagree.

Never commit:

- Cloud credentials
- API tokens
- Kubernetes Secret values
- Private repository credentials
- Generated reports containing sensitive infrastructure data

Use a secret manager such as AWS Secrets Manager, Vault, or External Secrets
Operator for production credentials.

## 8. Container and Kubernetes deployment

The Docker image runs as a non-root user and uses a read-only root filesystem
in the Kubernetes deployment. The deployment includes two replicas, health
probes, a ClusterIP service, dropped Linux capabilities, and a temporary
writable volume for runtime cache files.

Typical local deployment steps are:

```bash
docker build -t devops-health-checker:dev .
kind load docker-image devops-health-checker:dev \
  --name wisecow-cluster
kubectl apply -f deploy/kubernetes/secret.example.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl rollout status deployment/devops-health-checker
```

For production, publish an immutable versioned image or digest to a trusted
registry. Do not rely on `latest` as a release identifier.

## 9. Testing and validation

Run the test suite:

```bash
uv run pytest -v
```

The tests cover provider tools, schemas, validation, execution, RAG loading,
chunking, search, evaluation, agent behavior, APIs, MCP, security,
observability, multi-agent routing, and AIOps behavior.

Useful validation commands are:

```bash
git diff --check
kubectl get pods
kubectl get deployment devops-health-checker
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:18080/tools
```

The project has been validated with a complete passing test suite and a live
local Kubernetes deployment. These checks establish functional correctness;
they do not replace production load, security, disaster-recovery, or provider
integration testing.

## 10. Production readiness assessment

The current system is suitable for:

- Local development
- Demonstrations
- Training and portfolio work
- Read-only internal experiments
- Small controlled environments
- Building a foundation for an SRE assistant

Before production use, address the following:

1. Unify LLM provider configuration and add timeouts, retries, fallback
   models, and cost limits.
2. Use `load_incluster_config()` for Kubernetes workloads running inside a
   cluster and provide a least-privilege ServiceAccount and RBAC rules.
3. Replace the standard-library API server with a production ASGI service,
   ingress TLS, rate limiting, request IDs, and stronger authentication.
4. Export metrics and traces to Prometheus/OpenTelemetry and persist audit
   events in a protected logging system.
5. Replace in-memory TF-IDF storage with persistent semantic retrieval for a
   larger knowledge base; add document versioning, access control, and
   retrieval evaluation.
6. Add resource requests and limits, startup/readiness/liveness separation,
   PodDisruptionBudget, NetworkPolicy, image scanning, and image signing.
7. Add secret rotation and ensure sensitive provider data is redacted from
   logs and reports.
8. Add CI/CD that runs tests, builds the image, scans dependencies and the
   image, signs releases, and deploys only approved versions.
9. Add provider contract tests, failure-injection tests, load tests, and
   end-to-end tests with mocked cloud APIs.
10. Design an explicit approval service, dry-run preview, rollback mechanism,
    and emergency disable switch before adding write operations.

## 11. Suggested implementation order

### Immediate hardening

- Fix the LLM configuration mismatch.
- Add in-cluster Kubernetes authentication and RBAC.
- Add provider timeouts and retries.
- Use immutable image tags.
- Add CI for tests and image builds.

### Platform hardening

- Move to FastAPI/Uvicorn.
- Add Prometheus and OpenTelemetry.
- Persist audit logs.
- Add rate limits and request correlation IDs.
- Adopt the official MCP SDK.

### Knowledge and intelligence

- Add more reviewed runbooks.
- Add embeddings and a persistent vector store.
- Add retrieval and answer-quality datasets.
- Integrate logs, metrics, and incident history.

### Controlled automation

- Add dry-run remediation tools.
- Require explicit human approval.
- Show a change preview.
- Add rollback and complete audit trails.
- Enable automation only for narrowly scoped, low-risk operations.

## 12. What this project teaches

This project demonstrates practical skills across several areas:

- Python packaging, type hints, dataclasses, testing, and CLI design
- AWS, Kubernetes, and GitHub API integration
- Tool schemas, validation, execution boundaries, and failure handling
- RAG document loading, chunking, retrieval, metadata, and evaluation
- LLM tool calling and stateful workflow orchestration
- Prompt-injection awareness and approval-oriented governance
- Docker image construction and Kubernetes deployment
- Authentication, audit events, metrics, and operational reporting
- Safe AIOps design that investigates and proposes instead of mutating

The central architectural lesson is that an LLM should not be trusted as the
security boundary. The trusted application must own tool registration,
validation, permissions, execution, observability, and approval.

## 13. Roadmap status

The major roadmap areas have functional implementations:

```text
34D  Tool selection and provider failure handling       Implemented baseline
35   RAG and DevOps knowledge                           Implemented baseline
36   Workflow orchestration                             Implemented baseline
37   MCP                                                Implemented custom baseline
38   Agentic DevOps integration                         Implemented read-only
39   Security and governance                            Implemented baseline
40   Observability and evaluation                       Implemented baseline
41   Production deployment                              Implemented prototype
42   Multi-agent systems                                Implemented baseline
43   AIOps and autonomous operations                    Proposal-only baseline
```

“Implemented” here means the capability exists, is tested, and has been
integrated into the project. It does not mean every capability has received
enterprise-grade scaling, security review, persistence, or operational
hardening.

