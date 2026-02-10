# Compliance Summary Specification

The Compliance Summary evaluates adherence to Architecture Decision Records (ADRs) and organizational guidelines when available.

## Purpose

Answer: "Does this system follow established architectural decisions and guidelines?"

## ADR Detection

### Search Locations
Search for ADRs in order:
1. `docs/adr/`
2. `doc/adr/`
3. `.adr/`
4. `architecture/decisions/`
5. `doc/architecture/`
6. `docs/architecture/decisions/`

### ADR Formats
Common formats to recognize:
- **MADR** (Markdown Any Decision Records): `# [Title]` with Status, Context, Decision, Consequences sections
- **Nygard format**: Numbered files (0001-*.md) with Status, Context, Decision, Consequences
- **Y-statements**: "In the context of... facing... we decided... to achieve... accepting..."

### If ADRs Found
List discovered ADRs:

| ADR | Title | Status | Relevance |
|-----|-------|--------|-----------|
| 0001 | Use PostgreSQL for persistence | Accepted | Verified in deployment |
| 0002 | JWT for authentication | Accepted | Implemented in src/auth |
| 0003 | Monorepo structure | Proposed | Partially implemented |

**Status values:** Proposed, Accepted, Deprecated, Superseded

**Relevance:** Brief note on whether the codebase follows the decision

### If ADRs Not Found
Prompt user:
> No ADRs found in standard locations (docs/adr/, .adr/, architecture/decisions/). Do you have external guidelines or ADRs to evaluate against?

**If user provides reference:** Evaluate against provided guidelines
**If user declines:** Output the following:
> Not applicable - no ADRs or guidelines found in the repository, and no external guidelines were provided for evaluation.

## Required Elements (When ADRs/Guidelines Exist)

### 1. Compliance Description
Summary of compliance status:

**Example:**
> The codebase contains 5 ADRs documenting key architectural decisions. 4 of 5 decisions are implemented as documented. ADR-0003 (microservices architecture) shows partial implementation with some coupling between services.

### 2. ADR Adherence Section

For each relevant ADR:

**ADR-0001: Use PostgreSQL for persistence**
- **Status:** Compliant
- **Evidence:** docker-compose.yml defines postgres service; Prisma schema uses postgresql provider
- **Notes:** None

**ADR-0002: API versioning via URL path**
- **Status:** Partial
- **Evidence:** /api/v1/ routes exist, but some endpoints lack version prefix
- **Notes:** Legacy endpoints at /users should migrate to /api/v2/users

**ADR-0005: Event-driven communication between services**
- **Status:** Non-compliant
- **Evidence:** Direct HTTP calls between services in src/services/
- **Notes:** Kafka infrastructure exists but not used for inter-service communication

### 3. Guidelines Evaluation Section

If external guidelines provided:

**Evaluation against [Guideline Source]:**

| Guideline | Status | Evidence | Gap |
|-----------|--------|----------|-----|
| All APIs must be versioned | Partial | v1 routes exist | Some unversioned endpoints |
| JWT tokens must expire in 1 hour | Unknown | No token config found | Verify runtime config |
| All services must have health checks | Compliant | /health endpoint present | None |

## When Section Should Be Omitted

Output the N/A marker when:
1. No ADRs found in repository AND
2. User did not provide external guidelines when asked

**N/A Format:**
> Not applicable - no ADRs or guidelines found in the repository, and no external guidelines were provided for evaluation. This section documents compliance against architectural decisions and organizational standards. To include this section in future reviews, either:
> - Add ADRs to the repository (recommended: docs/adr/)
> - Provide external guideline documents during review

## Data Sources (from research.json)

- `adrs.found` → Whether ADRs detected
- `adrs.location` → Path to ADR directory
- `adrs.titles` → List of ADR titles
- User-provided guidelines → External input during review

## Compliance Status Values

| Status | Meaning |
|--------|---------|
| Compliant | Implementation matches decision |
| Partial | Some aspects implemented, gaps exist |
| Non-compliant | Decision documented but not followed |
| Unknown | Cannot verify from static analysis |
| Not applicable | Decision doesn't apply to this codebase |
