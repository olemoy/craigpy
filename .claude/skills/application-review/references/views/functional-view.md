# Functional View Specification

The Functional View describes what the system does at a high level - its capabilities, feature areas, and business domain alignment.

## Purpose

Answer: "What does this system do and what business capabilities does it provide?"

## Required Elements

### 1. Functional Description
2-3 sentences summarizing:
- Primary purpose of the system
- Key user workflows supported
- Business value delivered

**Example:**
> The application provides inventory management capabilities for retail operations. Users can track stock levels, manage suppliers, and generate purchase orders. It supports both single-store and multi-location retail businesses.

### 2. Capabilities Table

| Capability | Description | Evidence |
|------------|-------------|----------|
| User Authentication | Login, registration, password reset | src/auth/, AuthService |
| Order Processing | Create, update, cancel orders | src/orders/, OrderController |
| Reporting | Generate sales and inventory reports | src/reports/, report-templates/ |

**How to identify capabilities:**
- Top-level source directories (src/users, src/orders, etc.)
- Controller/handler files
- README feature lists
- API route definitions
- Database table names (if schema visible)

### 3. Feature Areas
Group related capabilities into logical feature areas:

**Example:**
```
**User Management**
- Registration and onboarding
- Profile management
- Role-based access control

**Order Lifecycle**
- Cart management
- Checkout flow
- Order tracking
- Returns and refunds

**Reporting & Analytics**
- Sales dashboards
- Inventory reports
- Export to CSV/PDF
```

### 4. Business Domain
Describe the business domain the application serves:
- Industry vertical (e-commerce, healthcare, fintech, etc.)
- Core domain concepts (orders, patients, transactions, etc.)
- Bounded contexts if DDD patterns are evident

**Example:**
> The application operates in the **e-commerce** domain, specifically B2C retail. Core domain concepts include Products, Orders, Customers, and Inventory. The codebase shows separation between order management and inventory management bounded contexts.

## Data Sources (from research.json)

- `metadata.description` → System purpose
- `codeMetrics.directoryStructure` → Feature areas from directory names
- `documentation` → README for feature lists
- Directory and file names → Capability evidence

## Inference Guidelines

Since functional capabilities are not always explicit:

1. **Directory names** → Often map to feature areas
   - `src/auth` → Authentication
   - `src/payments` → Payment processing
   - `api/v1/users` → User management

2. **Dependency purposes** → Hint at capabilities
   - `stripe` → Payment processing
   - `nodemailer` → Email notifications
   - `pdf-lib` → Document generation

3. **README sections** → Feature descriptions
   - "Features" section
   - "What it does" section
   - Getting started examples

## When Information is Missing

If functional areas cannot be determined:
> Functional capabilities could not be fully determined from static analysis. The codebase structure does not clearly indicate feature boundaries. Manual inspection or documentation review recommended.

For each missing element:
> Not applicable - no evidence found for [specific element]
