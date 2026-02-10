# Development View Specification

The Development View covers the technical implementation: technology stack, dependencies, code structure, build system, and testing approach.

## Purpose

Answer: "How is this system built and what technologies does it use?"

## Required Elements

### 1. Development Description
2-3 sentences summarizing:
- Primary language and framework
- Build/package management approach
- Development workflow indicators

**Example:**
> The application is built with TypeScript and React for the frontend, with a Node.js/Express backend. It uses npm for package management and follows a monorepo structure. Development workflow includes hot reloading and integrated testing.

### 2. Technology Stack Table

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Language | TypeScript | 5.0 | Strict mode enabled |
| Runtime | Node.js | 20.x | LTS version |
| Framework | Express | 4.18 | REST API |
| Frontend | React | 18.2 | With hooks |
| Database | PostgreSQL | 15 | Via Prisma ORM |
| Cache | Redis | 7.x | Session storage |

**Layer values:** Language, Runtime, Framework, Frontend, Backend, Database, Cache, Queue, Build Tool, Test Framework

### 3. Key Dependencies Table

List top 10-15 most significant dependencies:

| Dependency | Version | Purpose | Risk |
|------------|---------|---------|------|
| express | ^4.18.0 | HTTP server framework | Low |
| prisma | ^5.0.0 | Database ORM | Low |
| stripe | ^12.0.0 | Payment processing | Low |
| lodash | ^4.17.0 | Utility functions | Medium - large bundle |
| moment | ^2.29.0 | Date handling | High - deprecated |

**Risk assessment:**
- **Low**: Active maintenance, stable, widely used
- **Medium**: Large bundle size, limited maintenance, or better alternatives exist
- **High**: Deprecated, known vulnerabilities, or unmaintained

### 4. Code Structure
Show top-level directory structure:

```
project-root/
├── src/           # Application source code
│   ├── api/       # REST API routes
│   ├── services/  # Business logic
│   ├── models/    # Data models
│   └── utils/     # Shared utilities
├── tests/         # Test files
├── config/        # Configuration files
├── scripts/       # Build and utility scripts
└── docs/          # Documentation
```

Include brief description of each major directory's purpose.

### 5. Build System
Document:
- Package manager (npm, yarn, pnpm, maven, gradle)
- Build commands (npm run build, mvn package)
- Output artifacts (dist/, target/, build/)
- Notable build configurations

**Example:**
> **Package Manager:** npm (v9.x)
> **Build Command:** `npm run build` → TypeScript compilation + bundling
> **Output:** `dist/` directory with compiled JavaScript
> **Configuration:** tsconfig.json with strict settings, webpack.config.js for bundling

### 6. Testing Approach Table

| Test Type | Framework | Coverage | Notes |
|-----------|-----------|----------|-------|
| Unit | Jest | 75% | src/**/*.test.ts |
| Integration | Supertest | Partial | tests/integration/ |
| E2E | Playwright | Limited | tests/e2e/ |
| Linting | ESLint | N/A | Enforced in CI |

**Test Type values:** Unit, Integration, E2E, Contract, Performance, Security, Linting, Type Checking

## Data Sources (from research.json)

- `metadata.languages` → Primary languages
- `metadata.frameworks` → Frameworks
- `metadata.packageManager` → Package manager
- `dependencies.production` → Runtime dependencies
- `dependencies.development` → Dev dependencies
- `testing.*` → Testing setup
- `codeMetrics.directoryStructure` → Code structure

## When Information is Missing

For minimal codebases:
> Development view is limited due to minimal project structure. Key technologies identified but detailed build and test configurations not present.

For each missing element:
> Not applicable - no evidence found for [specific element]
