# Architectural Perspectives Specification

Architectural Perspectives are cross-cutting quality attributes that span multiple views. Each perspective evaluates how well the system addresses a specific quality concern.

## Purpose

Answer: "How well does this system address non-functional requirements?"

## Required Perspectives

### 1. Security Perspective

Evaluate security posture from static analysis:

**Authentication & Authorization:**
- Authentication mechanism (JWT, sessions, OAuth)
- Authorization patterns (RBAC, ABAC, none evident)
- Evidence files (auth middleware, permission checks)

**Secrets Management:**
- How secrets are handled (env vars, vault, k8s secrets)
- Sensitive data in config files (flag if found)
- .gitignore coverage for sensitive files

**Dependency Security:**
- Dependabot/Renovate configured
- Known vulnerability scanning in CI
- Lock files present and committed

**Code Security Indicators:**
- Input validation patterns
- SQL injection protection (parameterized queries, ORM)
- CORS configuration

**Example output:**
> **Authentication:** JWT-based authentication via Auth0 integration (evidence: src/middleware/auth.ts)
> **Secrets:** Environment variables with .env.example template. No secrets in committed files.
> **Dependencies:** Dependabot enabled for npm packages. Lock file (package-lock.json) committed.
> **Concerns:** No rate limiting evident in API routes.

### 2. Performance Perspective

Evaluate performance considerations:

**Caching:**
- Cache implementations (Redis, in-memory)
- Cache invalidation patterns
- CDN usage

**Database:**
- Connection pooling
- Query optimization hints (indexes in migrations)
- N+1 query prevention (data loaders, eager loading)

**Async Processing:**
- Background job processing
- Message queues for heavy operations
- Async/await patterns

**Example output:**
> **Caching:** Redis used for session storage and API response caching (evidence: src/cache/, docker-compose.yml)
> **Database:** Prisma ORM with connection pooling. Migrations include index definitions.
> **Async:** Bull queue for background email processing (evidence: src/jobs/)
> **Concerns:** No pagination evident in list endpoints.

### 3. Reliability Perspective

Evaluate resilience and fault tolerance:

**Error Handling:**
- Global error handlers
- Structured error responses
- Error logging

**Health Checks:**
- Health endpoint implemented
- Liveness/readiness probes in k8s
- Dependency health verification

**Graceful Degradation:**
- Circuit breaker patterns
- Retry logic with backoff
- Fallback mechanisms

**Example output:**
> **Error Handling:** Global error middleware with structured JSON responses (evidence: src/middleware/error.ts)
> **Health Checks:** /health endpoint implemented. Kubernetes readiness probe configured.
> **Resilience:** No circuit breaker pattern detected for external service calls.

### 4. Scalability Perspective

Evaluate scaling readiness:

**Horizontal Scaling:**
- Stateless design (no local state)
- Session externalization
- Shared-nothing architecture

**Data Scaling:**
- Database read replicas
- Sharding strategy
- Event sourcing patterns

**Infrastructure:**
- Auto-scaling configuration
- Load balancer setup
- CDN for static assets

**Example output:**
> **Horizontal Scaling:** Application appears stateless. Sessions stored in Redis.
> **Infrastructure:** Kubernetes HPA configured for API deployment (min: 2, max: 10)
> **Data:** Single database instance. No read replica configuration found.

## Data Sources (from research.json)

- `securityIndicators.*` → Security perspective
- `integrations.databases` → Performance (caching)
- `integrations.messaging` → Reliability (async)
- `deployment.orchestration` → Scalability
- `configuration.*` → All perspectives

## Evaluation Format

For each perspective, provide:

1. **Summary** - 1-2 sentence overall assessment
2. **Positive Indicators** - What's done well
3. **Concerns** - Gaps or risks identified
4. **Evidence** - File paths or config references

## When Information is Missing

If a perspective cannot be evaluated:
> **[Perspective]:** Cannot be fully evaluated from static analysis. [Specific limitation]. Manual review recommended for [specific area].

Common limitations:
- Performance: "Actual performance characteristics require runtime analysis"
- Security: "Full security audit requires dynamic testing and penetration testing"
- Reliability: "Failure modes require chaos engineering or production observation"
