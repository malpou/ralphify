# Chapter 24: The Agent Protocol Stack & Credential Security

> The protocol layer has converged faster than anyone expected. By December 2025, the Linux Foundation's Agentic AI Foundation (AAIF) unified MCP, A2A, AGENTS.md, and goose under one governance body — with AWS, Anthropic, Block, Google, Microsoft, and OpenAI as platinum members. Meanwhile, credential management has emerged as the single biggest operational security gap: AI-assisted commits leak secrets at 2x the baseline rate, and 53% of MCP servers still use static API keys.

## The Three-Protocol Stack

By March 2026, three complementary protocols define how agents interact with the world:

| Protocol | Direction | Purpose | Maturity |
|----------|-----------|---------|----------|
| **MCP** (Model Context Protocol) | Agent → Tool | Standardizes how agents access tools and data sources | Production (97M monthly SDK downloads) |
| **A2A** (Agent-to-Agent) | Agent ↔ Agent | Standardizes how agents delegate tasks and coordinate | Early production (150+ supported orgs, v0.3 with gRPC) |
| **AG-UI** (Agent-User Interaction) | Agent → User | Standardizes how agents connect to frontends | Emerging (16 event types, CopilotKit-backed) |

**MCP** is the plumbing — how an agent reads files, queries databases, calls APIs. It's universally adopted (every major AI provider) and defines the tool ecosystem ralph loops operate within. The June 2025 spec revision adopted OAuth 2.1 as the authorization framework with mandatory PKCE, resource indicators, and dynamic client registration.

**A2A** is the coordination layer — how agents delegate to each other. Google launched it in April 2025, donated it to the Linux Foundation in June, and by July it had 150+ supporting organizations. Key mechanism: **Agent Cards** (JSON at `/.well-known/agent.json`) enable discovery; **Tasks** with lifecycle states enable async delegation. The v0.3 update added gRPC support and signed security cards.

**AG-UI** is the presentation layer — how agents stream state to frontends. It provides typed handoffs, mid-flow pause/approve/edit/retry without losing state, and ~16 event types across lifecycle, text, tool calls, state management, and special events (approval pauses, custom needs). It complements A2A: AG-UI handles what the user sees, A2A handles what agents do behind the scenes.

### The AAIF Unification

On December 9, 2025, the Linux Foundation formed the Agentic AI Foundation (AAIF) with three founding projects: MCP (Anthropic), goose (Block), and AGENTS.md (OpenAI). The A2A protocol also joined the Linux Foundation earlier. This is significant: the competing companies that build frontier models have agreed on a shared infrastructure layer for agents. The implication for ralph loops: **RALPH.md files that reference MCP servers and A2A agent cards are building on standards with cross-vendor governance, not vendor lock-in.**

### How This Maps to Ralph Loops

Ralph loops already implement the core pattern:
- **MCP layer**: `commands` in RALPH.md are proto-MCP — deterministic data sources that feed the prompt. As MCP adoption grows, ralph commands could be replaced or supplemented by MCP server calls.
- **A2A layer**: Multi-ralph orchestration (via `ralph run --concurrent`) is proto-A2A. A ralph could delegate sub-tasks to specialized ralphs via A2A Agent Cards.
- **AG-UI layer**: The console emitter (`_console_emitter.py`) is proto-AG-UI. As agent UIs evolve, ralphify could stream structured events to dashboards.

The gap: ralphify currently uses none of these protocols natively. The opportunity is to adopt MCP first (largest ecosystem, most immediate value), then A2A for multi-ralph coordination.

## Credential Security: The Operational Gap

### The Scale of the Problem

GitGuardian's State of Secrets Sprawl 2026 report (March 17, 2026) quantifies the damage:

- **28.65 million** new hardcoded secrets on public GitHub in 2025 (34% YoY increase)
- **AI-assisted commits leak secrets at 2x the baseline rate** — Claude Code specifically at **3.2%** vs 1.5% baseline
- **AI-service credentials surging 81% YoY** (1.275 million AI API keys exposed)
- **64% of secrets leaked in 2022 remain unrevoked in 2026** — remediation doesn't keep up
- **24,008 unique secrets** found in MCP configuration files on public GitHub, **2,117 confirmed valid** (Astrix Security)

The root cause is structural: agents read `.env` files, hardcode API keys in generated code, and commit credentials without understanding what they are. Knostic security researchers found that Claude Code **automatically reads `.env`, `.env.local`, and similar files without user notification** — any commands the agent executes can access these secrets.

### The CVE Wake-Up Call

**CVE-2026-21852**: Check Point researchers showed that simply opening a malicious repository in Claude Code could exfiltrate API keys via manipulated `.claude/settings.json` hooks and `ANTHROPIC_BASE_URL` redirection. API calls with auth credentials were sent **before the trust dialog appeared**. This is the coding agent equivalent of a supply-chain attack — the repo IS the attack vector.

### Three Credential Architecture Tiers

Practitioners have converged on three tiers, from weakest to strongest:

**Tier 1 — Environment Variables (status quo, weakest)**
- API keys in `.env` files or shell environment
- The dominant pattern for Claude Code, Cursor, Codex today
- Vulnerable to: agent reading `.env`, hardcoding in generated code, committing to git, prompt injection exfiltration
- Mitigation: `.gitignore` + `permissions.deny` in `.claude/settings.json` — necessary but insufficient

**Tier 2 — Vault Integration (better)**
- Agent runtime fetches short-lived credentials from HashiCorp Vault, AWS Secrets Manager, Infisical, or 1Password
- Only vault access credentials are stored locally; actual secrets are fetched at runtime
- Infisical's pattern for Cursor Cloud Agents: store only Infisical machine identity in Cursor Secrets, fetch everything else at runtime
- Supports rotation: vault-managed credentials auto-rotate without agent awareness
- Vulnerability: agent still sees the credentials in memory during execution

**Tier 3 — Credential Injection Proxy (strongest, emerging standard)**
- A proxy **outside the agent sandbox** intercepts outbound HTTP requests and injects auth headers
- The agent **never sees the raw credentials** — not in environment, not in memory, not in files
- Vercel, GitHub, and NVIDIA independently converged on this architecture:
  - **Vercel**: Secret injection proxy overwrites headers on outbound requests; injected headers overwrite any agent-set headers
  - **GitHub**: Agent runs in container with firewalled network; LLM API keys live in separate proxy container; MCP credentials in separate gateway container; agent has **zero access to secrets**
  - **NVIDIA OpenShell**: Credentials in memory only, never on disk; kernel-level filesystem isolation via Landlock LSM

The proxy pattern has one limitation: it doesn't prevent misuse during active runtime. The agent can still make unexpected API calls using the injected credentials while running — it just can't exfiltrate the raw credential values.

### Keycard: Runtime Governance (March 19, 2026)

**Keycard** is the first dedicated runtime governance platform for coding agents, released March 19, 2026. It provides:

- **Identity-bound, task-scoped credentials**: Short-lived credentials cryptographically bound to the specific agent, developer, runtime environment, AND task. Credentials are injected in-memory, never touch disk or the agent's context window, and are gone when the session ends.
- **Point-of-execution governance**: Every tool an agent touches — shell commands, MCP servers, CLIs, APIs, and code the agent writes at runtime — is governed at the moment of execution, not at login or network boundary.
- **Full audit trail**: Every prompt, tool invocation, and policy decision is logged and attributed to a specific agent, developer, runtime, and task in near-realtime.
- **Cross-environment portability**: Agents configured once run across laptops, sandboxes, and CI without reconfiguration, using cryptographically attested runtime context.

Keycard's thesis: "Most agents fall back to human-in-the-loop workflows that require developers to approve every tool call, destroying all semblance of autonomy and exhausting users through consent fatigue." Runtime governance replaces approval fatigue with policy-based automation.

Keycard also acquired **Anchor.dev** (February 2026) to integrate certificate management — suggesting credential governance is expanding to include TLS, code signing, and supply chain verification.

### MCP Authentication: Standardized but Not Adopted

The MCP specification adopted OAuth 2.1 as its authorization framework (June 2025 revision). Key requirements:
- PKCE with S256 (mandatory)
- Authorization server separation (from MCP server)
- Resource Indicators (RFC 8707)
- Dynamic Client Registration

**The reality gap** (Astrix Security): 88% of MCP servers require credentials, but **53% rely on insecure static secrets** (API keys, PATs). Only **8.5% use OAuth**. The root cause: MCP tutorials encourage hardcoding API keys in `mcp.json`, and developers copy-paste into public repos.

Best practices for MCP auth:
- Use Token Exchange (RFC 8693) for downstream resources, not token passthrough
- Design MCP-specific scopes separate from main API scopes
- Implement step-up authorization (403 + scope negotiation) for sensitive operations
- Short-lived access tokens with refresh token support
- Never store tokens in URL parameters

### Token Rotation for Long-Running Loops

The unsolved tension: **short-lived tokens (security) vs. long-running autonomous loops (operational continuity)**. When an OAuth token expires mid-loop, the agent fails with auth errors and may leave work in a broken state (documented in Claude Code GitHub issue #12447).

Emerging patterns:
1. **Vault-managed auto-rotation**: HashiCorp Vault Agent keeps credential files fresh; agent reads from file/socket that Vault updates transparently
2. **Credential injection proxy**: Rotation is invisible to the agent since it never holds the credential
3. **Mid-task session resumption**: Save state, re-authenticate, resume (aspirational — few frameworks implement cleanly)
4. **Configurable TTL trade-offs**: Short tokens for supervised sessions (15 min), longer for overnight autonomous runs

## Implications for Ralphify

### RALPH.md as Permission Manifest (Enhanced)

Chapter 23 noted that RALPH.md already defines a permission manifest via `agent` + `commands`. The protocol and credential findings extend this:

1. **MCP server declarations**: RALPH.md could declare required MCP servers (`mcp: [github, database, monitoring]`), enabling the harness to provision and connect them with proper credentials before the loop starts.

2. **Credential scope declarations**: A `credentials` frontmatter field could declare what external access the ralph needs (`credentials: [github-api, aws-s3-readonly]`), enabling the harness to provision scoped, ephemeral credentials via injection proxy.

3. **A2A Agent Cards for ralphs**: Each RALPH.md could auto-generate an A2A Agent Card (`/.well-known/agent.json`) describing the ralph's capabilities, enabling other agents to discover and delegate to it.

### The Zero-Secret Ralph

The strongest credential posture for ralph loops:
- RALPH.md declares what access is needed (MCP servers, APIs, services)
- The harness provisions ephemeral credentials via injection proxy
- The agent never sees raw credentials — they're injected into outbound requests
- Credentials are task-scoped and session-scoped — they die when the loop ends
- All credential usage is audited per-iteration

This maps naturally to ralphify's architecture: the harness is already the control plane, and RALPH.md is already the configuration manifest.

### Protocol Adoption Roadmap

| Phase | What | Why |
|-------|------|-----|
| **Now** | MCP server support in RALPH.md | Largest ecosystem (97M downloads), replaces custom commands for many use cases |
| **Next** | Credential injection proxy | Eliminate the #1 security gap (3.2% leak rate) |
| **Later** | A2A for multi-ralph coordination | Enable ralph-to-ralph delegation via standard protocol |
| **Future** | AG-UI for dashboard streaming | Rich frontend for ralph loop monitoring |

### Key Insight for Ralph Loop Authors

**Declare dependencies, don't embed secrets.** A RALPH.md that says `credentials: [openai-api]` and lets the harness handle provisioning is fundamentally more secure than one where the agent reads `$OPENAI_API_KEY` from the environment. The same principle that makes ralph loops naturally sandboxable (Ch23) makes them naturally securable: the harness is the governance layer, not the agent.
