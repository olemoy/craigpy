# Extraction Patterns

File-by-file patterns for extracting research data. Process files in the order listed.

**Note:** For dependency health metrics, use `scripts/verify-dependencies.sh` to get factual data. Script output takes precedence over inferred data.

## 1. Root Documentation

### README.md
Extract:
- Application name (first H1 heading or bold text)
- Description (first paragraph after title)
- Technology mentions (scan for framework/language keywords)
- Architecture overview if present
- Quick start instructions (reveals runtime requirements)

### CONTRIBUTING.md
Extract:
- Development setup requirements
- Testing instructions
- Build commands

---

## 2. Package Manifests

### package.json (Node.js)
```
metadata.name = .name
metadata.version = .version
metadata.description = .description
dependencies.production = .dependencies (key-value pairs)
dependencies.development = .devDependencies (key-value pairs)
metadata.packageManager = "npm" or "yarn" (check for yarn.lock)
testing.frameworks = look for jest, mocha, vitest, playwright in devDeps
metadata.frameworks = look for react, vue, angular, express, fastify, next in deps
```

### pom.xml (Maven/Java)
```
metadata.name = /project/artifactId
metadata.version = /project/version
metadata.description = /project/description
dependencies.production = /project/dependencies/dependency (exclude test scope)
dependencies.development = /project/dependencies/dependency[@scope='test']
metadata.frameworks = look for spring-boot, quarkus, micronaut in deps
```

### build.gradle / build.gradle.kts (Gradle)
```
metadata.name = rootProject.name or settings.gradle
dependencies = implementation, api, testImplementation blocks
metadata.frameworks = spring boot plugin, application plugin
```

### requirements.txt / pyproject.toml (Python)
```
dependencies.production = listed packages
metadata.frameworks = django, flask, fastapi, pytest
Look for setup.py, setup.cfg for metadata
```

### go.mod (Go)
```
metadata.name = module path
dependencies.production = require block
metadata.frameworks = gin, echo, fiber, chi
```

### Cargo.toml (Rust)
```
metadata.name = [package].name
metadata.version = [package].version
dependencies.production = [dependencies]
dependencies.development = [dev-dependencies]
```

---

## 3. Configuration Files

### .env.example / .env.sample
Extract environment variables:
```
For each line VAR_NAME=value or VAR_NAME=:
  configuration.environmentVariables.push({
    name: VAR_NAME,
    sensitive: name contains PASSWORD, SECRET, KEY, TOKEN, CREDENTIAL
  })
```

### application.yml / application.properties (Spring)
Extract:
- Database connections (spring.datasource.*)
- Server port (server.port)
- External service URLs
- Profile configurations

### appsettings.json / appsettings.*.json (.NET)
Extract:
- ConnectionStrings section → databases
- External API configurations
- Logging configuration

### config/*.yaml, config/*.json
Scan for:
- Database connection strings
- API endpoints
- Feature flags
- Environment-specific settings

---

## 4. CI/CD Configuration

### .github/workflows/*.yml
```
deployment.cicd.platform = "GitHub Actions"
deployment.cicd.workflows = list of .yml filenames
deployment.cicd.stages = extract job names and steps
```

Look for:
- Build commands → build system
- Test commands → testing.frameworks
- Deploy targets → deployment environments
- Secrets usage → security indicators

### Jenkinsfile
```
deployment.cicd.platform = "Jenkins"
deployment.cicd.stages = stage('name') blocks
```

### .gitlab-ci.yml
```
deployment.cicd.platform = "GitLab CI"
deployment.cicd.stages = stages: array
deployment.cicd.workflows = job definitions
```

### azure-pipelines.yml
```
deployment.cicd.platform = "Azure DevOps"
deployment.cicd.stages = stages/jobs
```

---

## 5. Container & Deployment

### Dockerfile
```
deployment.containerization.hasDockerfile = true
deployment.containerization.baseImage = FROM instruction
```

Look for:
- Multi-stage builds (multiple FROM)
- Exposed ports
- Health checks
- Build arguments

### docker-compose.yml
```
deployment.containerization.hasCompose = true
deployment.containerization.composeServices = services keys
```

Extract from services:
- Database containers → integrations.databases
- Redis/cache containers → integrations.externalServices
- Message queue containers → integrations.messaging

### k8s/*.yaml, kubernetes/*.yaml
```
deployment.orchestration.type = "kubernetes"
deployment.orchestration.manifests = list of files
```

Extract:
- Deployment specs → replicas, resources
- Service definitions → exposed ports
- ConfigMaps/Secrets → configuration approach
- Ingress → external access patterns

### helm/Chart.yaml, charts/*/Chart.yaml
```
deployment.orchestration.helmCharts = chart names
```

### terraform/*.tf
```
deployment.infrastructure.hasIaC = true
deployment.infrastructure.iacTool = "Terraform"
```

Extract:
- Provider → cloudProvider
- Resource types → resources array

---

## 6. ADR Detection

Search in order:
1. `docs/adr/`
2. `doc/adr/`
3. `.adr/`
4. `architecture/decisions/`
5. `doc/architecture/`
6. `docs/architecture/decisions/`

For each .md file found:
```
adrs.found = true
adrs.location = directory path
adrs.count = number of files
adrs.titles = extract from H1 or filename
```

---

## 7. Code Metrics

### File counts
```bash
find . -type f -name "*.ts" -o -name "*.js" | wc -l  # TypeScript/JavaScript
find . -type f -name "*.java" | wc -l                 # Java
find . -type f -name "*.py" | wc -l                   # Python
find . -type f -name "*.go" | wc -l                   # Go
```

### Directory structure
```bash
ls -d */ | head -20  # Top-level directories
```

### Lines of code (approximate)
```bash
wc -l **/*.{ts,js,java,py,go} 2>/dev/null | tail -1
```

---

## 8. Security Indicators

### SECURITY.md
```
securityIndicators.hasSecurityPolicy = exists
```

### .github/dependabot.yml
```
securityIndicators.hasDependabotConfig = true
```

### CODEOWNERS
```
securityIndicators.hasCodeowners = true
```

### Auth patterns
Scan for in dependencies and config:
- OAuth/OIDC libraries
- JWT handling
- Session management
- API key patterns

---

## 9. Verified Data Collection

**Always run the verification script for accurate file-existence data:**

```bash
bash scripts/verify-dependencies.sh /path/to/repo > verification.json
```

The script performs file existence checks only (no package manager commands):
- Lock file detection (package-lock.json, yarn.lock, pnpm-lock.yaml, bun.lockb, etc.)
- Package manager identification (by manifest + lock file presence)
- Security config detection (dependabot, snyk, renovate, CODEOWNERS, SECURITY.md)
- CI/CD detection (GitHub Actions, GitLab CI, Jenkins, Azure Pipelines, CircleCI)
- Container config detection (Dockerfile, docker-compose, k8s, helm)
- Documentation detection (README, CONTRIBUTING, CHANGELOG, ADRs)

**Store output in `application-review-research.json` under `dependencies.verification`**

**What the script does NOT check (requires build tool execution):**
- Deprecated packages
- Outdated versions
- Security vulnerabilities
- Type errors

For these, document as "Not assessed - requires [tool] execution" rather than guessing.
