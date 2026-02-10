# Application Review - Agent Context

This file consolidates all essential references for application review. **Read this file ONCE at the start of a review.** Only read individual reference files if this consolidated context is insufficient for edge cases.

---

## Research Schema (Key Fields)

The research phase outputs JSON with this structure:

```
metadata:
  name, description, version, languages[], frameworks[], packageManager, repositoryUrl

dependencies:
  production[]: {name, version, purpose}
  development[]: {name, version, purpose}
  verification: <output from verify-all.sh>

integrations:
  databases[]: {type, evidence}
  apis[]: {name, type (REST|GraphQL|gRPC|SOAP|WebSocket), direction (inbound|outbound|both), evidence}
  messaging[]: {type, topics[], evidence}
  externalServices[]: {name, purpose, evidence}

configuration:
  configFiles[], environmentVariables[]: {name, description, sensitive}, secretsManagement

deployment:
  containerization: {hasDockerfile, baseImage, hasCompose, composeServices[]}
  orchestration: {type, manifests[], helmCharts[]}
  cicd: {platform, workflows[], stages[]}
  infrastructure: {hasIaC, iacTool, cloudProvider, resources[]}

testing:
  frameworks[], hasUnitTests, hasIntegrationTests, hasE2eTests, coverageConfig, testDirectories[]

codeMetrics:
  totalFiles, totalDirectories, linesByLanguage{}, directoryStructure[]

documentation:
  hasReadme, hasContributing, hasChangelog, hasApiDocs, additionalDocs[]

adrs:
  found, location, count, titles[]

securityIndicators:
  hasSecurityPolicy, hasDependabotConfig, hasCodeowners, authMechanism, sensitiveDataHandling[]
```

---

## Report Template Structure

The final report has exactly 7 sections (never add/remove/rename):

1. **Context View** - System boundaries, external actors, integration points
   - Requires: ASCII diagram + Mermaid diagram
   
2. **Functional View** - Capabilities, feature areas, business domain
   - No diagrams required
   
3. **Development View** - Tech stack, dependencies, code structure, build, testing
   - No diagrams required
   
4. **Deployment View** - Infrastructure, CI/CD, containers, environments
   - Requires: ASCII diagram + Mermaid diagram
   
5. **Architectural Perspectives** - Security, Performance, Reliability, Scalability
   - No diagrams required
   
6. **Technical Debt Analysis** - Issues, dependency health, missing practices
   - No diagrams required
   
7. **Compliance Summary** - ADR adherence, guidelines evaluation
   - No diagrams required (can be N/A if no ADRs)

---

## Diagram Patterns

### Node Naming Convention
| Type | Prefix | Shape Syntax |
|------|--------|--------------|
| User/Actor | `user_` | `user_x[["Label"]]` |
| Service/API | `svc_` | `svc_x([Label])` |
| Database | `db_` | `db_x[(Label)]` |
| Queue | `queue_` | `queue_x[/Label/]` |
| External System | `ext_` | `ext_x[[Label]]` |
| Container | `ctr_` | `ctr_x([Label])` |
| Infrastructure | `infra_` | `infra_x([Label])` |

### Context Diagram Template
```
ASCII (high-level, 5-7 external systems max):
                    +------------------+
                    |     Users        |
                    +--------+---------+
                             |
                     +-------v-------+
                     |  Application  |
                     +-------+-------+
                             |
            +----------------+----------------+
            |                |                |
      +-----v-----+    +-----v-----+    +-----v-----+
      | External1 |    | External2 |    | (+N more) |
      +-----------+    +-----------+    +-----------+

Mermaid (full detail):
flowchart TB
    user_main[["Primary User"]]
    
    subgraph system["Application"]
        svc_api([API])
    end
    
    ext_service[[External Service]]
    db_main[(Database)]
    
    user_main --> svc_api
    svc_api --> ext_service
    svc_api --> db_main
```

### Deployment Diagram Template
```
ASCII (high-level):
                    Internet
                        |
                +-------v-------+
                | Load Balancer |
                +-------+-------+
                        |
           +------------+------------+
           |                         |
    +------v------+          +-------v------+
    |   App Pod   |          |  Worker Pod  |
    +------+------+          +--------------+
           |
    +------v------+
    |  Database   |
    +-------------+

Mermaid (full detail):
flowchart TB
    user[["Users"]]
    
    subgraph cluster["Kubernetes"]
        infra_lb([Load Balancer])
        ctr_app([App Pods])
        ctr_worker([Workers])
    end
    
    subgraph data["Data"]
        db_main[(Database)]
        db_cache[(Cache)]
    end
    
    user --> infra_lb --> ctr_app
    ctr_app --> db_main
    ctr_app --> db_cache
```

### Diagram Rules
- Maximum 12 nodes per diagram
- ASCII shows high-level (5-7 external systems), Mermaid shows full detail
- Use `flowchart TB` (top to bottom) for both diagram types
- Label connections with short terms: REST, SQL, publish, consume, auth
- No colors or styling in Mermaid

---

## File Discovery Order

When researching a repository, examine files in this order:

1. **Root docs**: README.md, CONTRIBUTING.md
2. **Package manifests**: package.json, pom.xml, build.gradle(.kts), requirements.txt, go.mod, Cargo.toml
3. **Configuration**: .env.example, application.yml, appsettings.json, config/
4. **CI/CD**: .github/workflows/, Jenkinsfile, .gitlab-ci.yml
5. **Deployment**: Dockerfile, docker-compose.yml, k8s/, helm/, terraform/, nais/
6. **ADRs**: docs/adr/, .adr/, architecture/decisions/, doc/architecture/

---

## Extraction Patterns (Quick Reference)

### Package Manifests
| File | Name Field | Dependencies | Framework Detection |
|------|------------|--------------|---------------------|
| package.json | .name | .dependencies, .devDependencies | react, next, vue, express in deps |
| pom.xml | /project/artifactId | /project/dependencies | spring-boot in deps |
| build.gradle.kts | settings.gradle | implementation(), testImplementation() | spring boot plugin |
| go.mod | module path | require block | gin, echo, fiber in requires |
| Cargo.toml | [package].name | [dependencies], [dev-dependencies] | actix, rocket in deps |

### CI/CD Detection
| File/Dir | Platform | Extract |
|----------|----------|---------|
| .github/workflows/*.yml | GitHub Actions | job names, steps, deploy targets |
| .gitlab-ci.yml | GitLab CI | stages array, job definitions |
| Jenkinsfile | Jenkins | stage() blocks |
| azure-pipelines.yml | Azure DevOps | stages/jobs |

### Container Detection
| File | Extract |
|------|---------|
| Dockerfile | FROM (base image), EXPOSE (ports), HEALTHCHECK |
| docker-compose.yml | services keys → composeServices |
| k8s/*.yaml | Deployment replicas, Service ports, Ingress hosts |

---

## ADR Handling

1. **Search locations**: docs/adr/, .adr/, architecture/decisions/, doc/architecture/
2. **If found**: List in research JSON, evaluate compliance in Section 7
3. **If not found**: Ask user ONCE: "No ADRs found. Do you have external guidelines?"
4. **If user declines**: Output `> Not applicable - no ADRs or guidelines found`

---

## Technical Debt Indicators

### High Severity
- Known CVEs in dependencies
- Hardcoded secrets
- Missing authentication
- Deprecated packages with security implications

### Medium Severity
- Major version gaps (2+ versions behind)
- No TypeScript/type checking
- Low test coverage (<50%)
- No error handling patterns

### Low Severity
- Minor version gaps
- Missing optional tooling (prettier, husky)
- Documentation gaps
- TODO/FIXME comments

---

## Multi-Repository Reviews

When reviewing multiple repositories as a combined system:

1. **Run quick-scan.sh first** to inventory repositories
2. **Confirm scope with user** (all repos or selection)
3. **Run verify-all.sh once** with all confirmed repos
4. **Read files in parallel batches** (all READMEs together, all package.json together)
5. **Generate ONE combined report** with system-level context diagrams
6. **Include per-repo details** in Development View tables

---

## Output Rules

- **No emojis** in any output
- **Use tables** for structured data (deps, metrics, findings)
- **Keep paragraphs concise** (3-5 sentences max)
- **N/A marker format**: `> Not applicable - no evidence found for [topic]`
- **Save outputs**: `application-review-research.json` and `application-review-document.md`
