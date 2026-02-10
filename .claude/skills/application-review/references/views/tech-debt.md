# Technical Debt Analysis Specification

Technical Debt Analysis identifies areas where shortcuts, outdated practices, or accumulated issues may impact maintainability, security, or development velocity.

## Purpose

Answer: "What technical liabilities exist in this codebase?"

## Required Elements

### 1. Technical Debt Description
2-3 sentences summarizing:
- Overall debt level (low/medium/high)
- Primary debt categories observed
- Impact on development

**Example:**
> The codebase shows moderate technical debt primarily in dependency management and testing coverage. Several dependencies are outdated with known alternatives. Test coverage appears limited to happy-path scenarios.

### 2. Identified Issues Table

| Issue | Severity | Category | Evidence | Recommendation |
|-------|----------|----------|----------|----------------|
| Outdated React version | Medium | Dependencies | package.json: react@16.x | Upgrade to React 18 |
| No TypeScript strict mode | Low | Code Quality | tsconfig.json | Enable strict: true |
| Missing error boundaries | Medium | Reliability | No ErrorBoundary components | Add error boundaries |
| Moment.js usage | Medium | Dependencies | package.json | Replace with date-fns |
| No API rate limiting | High | Security | No rate-limit middleware | Implement rate limiting |

**Severity levels:**
- **High**: Security risk, blocks upgrades, or causes production issues
- **Medium**: Impacts maintainability or developer experience
- **Low**: Minor improvement opportunity, no immediate impact

**Category values:**
- Dependencies
- Code Quality
- Testing
- Security
- Documentation
- Architecture
- Performance
- Configuration

### 3. Dependency Health

Assess the health of key dependencies using **verified data** from the verification script.

**Run the verification script for factual file-existence data:**
```bash
bash scripts/verify-dependencies.sh /path/to/repo
```

**Dependency Red Flags Table:**

| Indicator | Verified | Details |
|-----------|----------|---------|
| Lock file present | [Yes/No] | [Actual files found, e.g., "yarn.lock"] |
| Dependency scanning configured | [Yes/No] | [dependabot.yml / renovate.json / .snyk] |
| Security policy | [Yes/No] | [SECURITY.md present] |
| Code owners | [Yes/No] | [CODEOWNERS present] |

**Note:** Deprecated/outdated package detection requires running package manager commands (`npm outdated`, `yarn outdated`, etc.) which is outside the scope of static analysis. Document this as "Not assessed - requires package manager execution" rather than guessing.

**What CAN be verified (file existence):**
- Lock files present
- Security tooling configured (dependabot, snyk, renovate)
- SECURITY.md / CODEOWNERS present

**What CANNOT be verified without running build tools:**
- Deprecated packages (requires `npm ls`, `yarn info`, etc.)
- Outdated versions (requires `npm outdated`, etc.)
- Type errors (requires `tsc`, `mvn compile`, etc.)
- Vulnerability counts (requires `npm audit`, etc.)

For items that cannot be verified, use: `> Not assessed - requires [tool] execution`

### 4. Missing Practices

Document standard practices that are absent:

**Development Practices:**
- [ ] TypeScript strict mode
- [ ] ESLint configuration
- [ ] Prettier formatting
- [ ] Pre-commit hooks (husky)
- [ ] Conventional commits

**Testing Practices:**
- [ ] Unit test coverage > 70%
- [ ] Integration tests
- [ ] E2E tests
- [ ] Test in CI pipeline

**Security Practices:**
- [ ] Dependency scanning
- [ ] SAST in CI
- [ ] Security policy (SECURITY.md)
- [ ] Code owners (CODEOWNERS)

**Documentation:**
- [ ] API documentation
- [ ] Architecture decision records
- [ ] Contributing guide
- [ ] Changelog

**Example output:**
> **Missing Practices:**
> - No pre-commit hooks configured (linting not enforced locally)
> - Test coverage reporting not configured
> - No SECURITY.md policy
> - API endpoints not documented (no OpenAPI/Swagger)

## Severity Assessment Guidelines

### High Severity
- Known CVEs in dependencies
- Deprecated packages with security implications
- Missing authentication/authorization
- Hardcoded secrets (even in non-production)
- No input validation on user data

### Medium Severity
- Major version gaps in frameworks (2+ major versions)
- No TypeScript/type checking
- Low test coverage (<50%)
- Missing error handling patterns
- Inconsistent code style (no linter)

### Low Severity
- Minor version gaps
- Missing optional tooling (prettier, husky)
- Documentation gaps
- Unused dependencies
- TODO/FIXME comments in code

## Data Sources (from research.json)

- `dependencies.production` → Dependency analysis
- `dependencies.development` → Dev tooling assessment
- `testing.*` → Testing practices
- `securityIndicators.*` → Security practices
- `documentation.*` → Documentation assessment

## When Information is Missing

If debt cannot be assessed in a category:
> **[Category]:** Assessment requires [specific information]. Static analysis provides limited insight into [specific aspect].

Example:
> **Performance Debt:** Cannot assess performance issues from static analysis. Runtime profiling and load testing required.
