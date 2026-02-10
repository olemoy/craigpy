---
name: application-review
description: >
  Analyze IT application repositories to produce structured architectural documentation.
  Generates a comprehensive report with Context View, Functional View, Development View,
  Deployment View, Architectural Perspectives, Technical Debt Analysis, and Compliance Summary.
  Use when asked to review an application, analyze a repository's architecture, create
  architectural documentation, or assess technical health of a codebase. Produces consistent,
  repeatable output with mermaid diagrams for Context and Deployment views.
allowed-tools: Read View Bash(grep:*) Bash(find:*) Bash(wc:*) Bash(head:*) Bash(cat:*) Bash(ls:*) Bash(bash:*)
---

# Application Review Skill

Produce a structured architectural review of an application repository with consistent, repeatable output.

## Output Format Rules

**Strict template adherence required:**
- Copy [report-template.md](assets/report-template.md) verbatim
- Fill placeholders with findings
- Never add, remove, or rename sections
- Use N/A markers for missing information: `> Not applicable - no evidence found for [topic]`

**Style constraints:**
- No emojis in output (keep headers plain text)
- Use tables for structured data (dependencies, metrics, findings)
- Keep paragraphs concise (3-5 sentences max)
- Both ASCII and Mermaid diagrams required for Context View and Deployment View
- ASCII diagrams are high-level overviews; Mermaid diagrams show full detail

## Workflow

Execute in four steps with minimal file reads and user interactions.

### Step 1: Load Context (ONE file read)

Read [assets/agent-context.md](assets/agent-context.md) which contains all specifications consolidated.

**Do NOT read individual reference files** (views/*.md, diagram-patterns.md, extraction-patterns.md) unless agent-context.md is insufficient for an edge case.

### Step 2: Scope Confirmation (ONE user interaction)

**For single repository:**
- Proceed directly to Step 3

**For multiple repositories or directory of repos:**
1. Run quick-scan to inventory:
   ```bash
   bash scripts/quick-scan.sh /path/to/repos
   ```
2. Present the repository list to user
3. Ask ONCE: "Found N repositories. Review all as a combined system, or select specific ones?"
4. Proceed with confirmed list

### Step 3: Research Phase

**A. Run batch verification (ONE script call for all repos):**
```bash
# Single repo
bash scripts/verify-dependencies.sh /path/to/repo

# Multiple repos - use verify-all.sh
bash scripts/verify-all.sh repo1 repo2 repo3
```

**B. Read files in parallel batches** (minimize sequential reads):
- Batch 1: All README.md files across repos
- Batch 2: All package manifests (package.json, build.gradle.kts, pom.xml)
- Batch 3: All Dockerfiles and CI configs
- Batch 4: All deployment configs (nais/, k8s/, helm/)

**C. Save research output:**
Save findings to `application-review-research.json` in the target directory.

### Step 4: Report Generation

Transform research JSON into the final report. Save to `application-review-document.md`.

**Generate each section using data from research.json** - all specifications are in agent-context.md.

For multi-repo reviews:
- Context View shows the combined system architecture
- Development View includes per-repo technology tables
- Single combined report (not one per repo)

## Section Specifications

All section specifications are consolidated in [assets/agent-context.md](assets/agent-context.md).

| Section | Diagrams Required |
|---------|-------------------|
| Context View | ASCII + Mermaid |
| Functional View | No |
| Development View | No |
| Deployment View | ASCII + Mermaid |
| Architectural Perspectives | No |
| Technical Debt Analysis | No |
| Compliance Summary | No |

**Reference files** (read only if agent-context.md is insufficient):
- [references/views/](references/views/) - Detailed view specifications
- [references/diagram-patterns.md](references/diagram-patterns.md) - Full diagram syntax
- [references/extraction-patterns.md](references/extraction-patterns.md) - File-by-file extraction rules

## ADR/Guidelines Handling

1. The quick-scan and verify scripts detect ADR directories automatically
2. Search locations: `docs/adr/`, `.adr/`, `architecture/decisions/`, `doc/architecture/`
3. If not found in repos, ask user ONCE: "No ADRs found in standard locations. Do you have external guidelines or ADRs to evaluate against?"
4. If user provides reference, read it and use for Compliance Summary
5. If user declines, output: `> Not applicable - no ADRs or guidelines found or provided`

## Validation Checklist

Before completing, verify:

- [ ] All 7 sections present in output
- [ ] Context View contains both ASCII and Mermaid diagrams
- [ ] Deployment View contains both ASCII and Mermaid diagrams
- [ ] No sections added beyond the 7 defined
- [ ] No section headers renamed
- [ ] `application-review-research.json` created with valid structure
- [ ] `application-review-document.md` created in target directory
- [ ] Tables used for dependencies and metrics
- [ ] No emojis used anywhere in output
- [ ] Verification scripts run (verify-all.sh for multi-repo, verify-dependencies.sh for single)

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `quick-scan.sh` | Inventory repositories in a directory | `bash scripts/quick-scan.sh /path/to/repos` |
| `verify-all.sh` | Batch verification for multiple repos | `bash scripts/verify-all.sh repo1 repo2 repo3` |
| `verify-dependencies.sh` | Single repo verification | `bash scripts/verify-dependencies.sh /path/to/repo` |

**Script outputs are JSON** - parse and include in research.json under `dependencies.verification`.

## Verified Data Collection

The verification scripts perform actual file system checks rather than relying on LLM interpretation:
- Lock file existence (package-lock.json, yarn.lock, pnpm-lock.yaml, etc.)
- Security config presence (dependabot, snyk, renovate, CODEOWNERS, SECURITY.md)
- CI/CD config detection (GitHub Actions, GitLab CI, Jenkins, etc.)
- Container config detection (Dockerfile, docker-compose, k8s, helm)
- ADR directory detection

**Note:** Deprecated/outdated package detection is NOT included as it requires running package manager commands which vary by ecosystem.

Always prefer script output over inferred data when available.
