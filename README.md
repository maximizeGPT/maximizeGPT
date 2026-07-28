# Mohammed Wasif

Forward-deployed AI consultant and CPA. In 42 business days at a 1,000+ employee SaaS company, shipped 17 production agent automations that eliminated 1,091 annual hours of manual finance work and surfaced $1.5M in revenue exposure.

Now extending that model to a second enterprise engagement, and shipping the open-source tooling that makes it repeatable.

---

## Things I've built

**[Supervisor](https://github.com/maximizeGPT/supervisor)** (Swift, MIT)
A macOS app that supervises Claude Code and Codex sessions after you step away. It answers the questions they stop to ask, reading the repo for context, nudges idle sessions back toward their objective, and pauses destructive commands with a one-sentence reason. Signed and notarized by Apple, runs on your own API key, nothing leaves the machine. The portable subset ships as an Agent Skill for people who aren't on a Mac.

**[netsuite-saved-search-mcp](https://github.com/maximizeGPT/netsuite-saved-search-mcp)** (Python, on PyPI)
NetSuite saved-search exports carry a `.xls` extension but are XML SpreadsheetML underneath, so Excel opens them and pandas trips on them. Seven MCP tools over a parser that handles the format's real quirks: entity-encoded text, empty cells flagged with `ss:Index`, column layouts that drift between searches. Broken cells come back as structured warnings instead of crashing the run.

**[claude-eval-harness](https://github.com/maximizeGPT/claude-eval-harness)** (Python)
Regression-diff eval harness for tool-use agents. YAML suites, self-contained JSON runs, and a diff that compares two runs case by case, surfacing drift in LLM-judge reasoning even on cases that still pass.

**[prompt-guard](https://github.com/maximizeGPT/prompt-guard)** (TypeScript)
Ingests your past agent sessions into a local SQLite corpus and reads your project context files, then asks the clarifying questions that ate iteration cycles the last time you sent a vague prompt.

**[ArchTrack](https://github.com/maximizeGPT/Archtrack)** (TypeScript)
Open-source employee desktop tracker and admin dashboard for small businesses. Real-time activity, role-aware productivity scoring, multi-tenant. Live at [archtrack.live](https://archtrack.live).

## What I'm working on now

- Internal skill and slash-command marketplaces across four Claude surfaces (Code, Desktop, Terminal, Computer)
- Memory architecture and intent layers for long-running enterprise agents, targeting 30–50% token efficiency gains
- Automation and AI tooling work across a second enterprise engagement

## Earlier ventures

| | What | Outcome |
|---|---|---|
| **dAIcor** | AI-assisted interior design platform | 482 customers · 40% EBITDA · $0 marketing spend |
| **Sumer** | Consumer fintech | $250K raised · $1M valuation · 2,200 customers |

## Background

Senior Associate at The Siegfried Group, forward-deployed to enterprise clients. CPA. Former Senior Accountant at Deloitte. Co-founder of dAIcor and Sumer. University of Toronto.

## What I'm interested in

Forward-deployed AI engineering. Agents in SOX-regulated and enterprise environments. Skill architectures and MCP servers. The gap between AI prototype and production system: what it takes to make agent output audit-ready and institutionally defensible.

---

[LinkedIn](https://www.linkedin.com/in/mohammed-wasif-cpa-147078145) · rayedwasif@hotmail.com · San Francisco, CA
