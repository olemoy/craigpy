# Context View Specification

The Context View shows the system's boundaries and its interactions with external actors and systems.

## Purpose

Answer: "What does this system interact with and why?"

## Required Elements

### 1. Context Description
2-3 sentences describing:
- What the system is
- Who uses it
- What it connects to

**Example:**
> The Order Management System processes customer orders from the web storefront. It integrates with payment providers for transactions and warehouse systems for fulfillment. Internal users access it via an admin portal.

### 2. Context Diagram (MANDATORY)
Follow [mermaid-patterns.md](../mermaid-patterns.md) Context Diagram Pattern.

Include:
- The system as a central subgraph
- All user types (human actors)
- External systems it calls (outbound)
- External systems that call it (inbound)
- Data stores

### 3. External Actors Table

| Actor | Type | Interaction | Notes |
|-------|------|-------------|-------|
| End User | Human | Web UI, REST API | Primary consumer |
| Admin | Human | Admin portal | Internal staff |
| Payment Gateway | System | Outbound REST | Stripe, via SDK |
| Analytics | System | Outbound events | Segment tracking |

**Type values:** Human, System, Service, Scheduled Job

**Interaction values:** Describe the interface (REST, GraphQL, UI, Events, etc.)

### 4. Integration Points
For each external integration, document:
- Name of external system
- Protocol/interface type
- Data exchanged (high level)
- Evidence (file where detected)

**Format:**
```
**Payment Processing (Stripe)**
- Protocol: REST via SDK
- Data: Payment intents, refunds, webhooks
- Evidence: package.json (stripe dependency), src/payments/
```

## Data Sources (from research.json)

- `integrations.apis` → External APIs
- `integrations.databases` → Data stores
- `integrations.messaging` → Message queues
- `integrations.externalServices` → Third-party services
- `deployment.containerization.composeServices` → Related services in compose

## When Information is Missing

If no external integrations are found:
> Not applicable - no external integrations detected. The application appears to be self-contained or integration points are not evident from static analysis.

For each missing element, use the N/A marker:
> Not applicable - no evidence found for [specific element]
