# Part 4: Contract Template System

## Contract System Overview

| Document | Description |
|:---|:---|
| **SOR** (Statement of Requirements) | Written by client, describes business goals and requirements |
| **SOW** (Statement of Work) | Written by vendor, defines scope, deliverables, timeline |
| **MSA** (Master Service Agreement) | Legal master contract, defines general terms |
| **PCR** (Project Change Request) | Manages scope changes |
| **Quote** | Fee structure, payment terms |

---

## 1. Statement of Requirements (SOR) Template

**[Client Company] AI Agent Service Requirements**
- Document ID: [SOR-YYYYMMDD-XXX]
- Version: V1.0
- Date: [YYYY-MM-DD]

### 1. Project Overview
- **1.1 Background:** (Project context, current pain points)
- **1.2 Objectives:** (Quantifiable goals, e.g., "Reduce response time from 5min to 30sec")
- **1.3 Scope:** (Core work content and boundaries)

### 2. Requirements Detail

**2.1 Functional Requirements**
- **Core Feature 1:** (e.g., NLU & Intent Recognition)
  - Description: ...
  - Acceptance Criteria: Intent accuracy ≥ 95%

**2.2 Non-Functional Requirements**
- **Performance:** Avg response < 1s, concurrency > 100 QPS
- **Security:** TLS 1.3, sensitive data masking
- **Availability:** Core service > 99.9%

### 3. Existing Systems & Environment
- Hardware, Software, Integration requirements

### 4. Delivery Requirements
- Deliverables list, milestones

### 5. Budget & Constraints

---

## 2. Statement of Work (SOW) Template

**[Vendor Company] AI Agent Implementation SOW**
- Project: [Client] AI Agent Implementation
- SOW ID: [SOW-YYYYMMDD-XXX]
- Related SOR: [SOR-YYYYMMDD-XXX]

### 1. Scope
- **1.1 Objectives**
- **1.2 Scope Overview**
- **1.3 Exclusions** ⚠️ (What is NOT included)

### 2. Methodology & Activities
- **2.1 Methodology:** (Agile/Waterfall)
- **2.2 Phases:**
  - Phase 1: Requirements & Design (X weeks)
  - Phase 2: Development & Testing (Y weeks)
  - Phase 3: Deployment & Go-live (Z weeks)

### 3. Deliverables & Acceptance
- Deliverables list per phase
- Acceptance criteria (quantifiable, testable)

### 4. Timeline (Gantt chart or table)

### 5. Team & Governance
- Roles & responsibilities
- Communication cadence
- Risk management

### 6. Fees & Payment (Reference quote)

### 7. Assumptions & Dependencies

### 8. Signatures

---

## 3. MSA Core Clauses

| Clause | Key Points |
|:---|:---|
| **Services** | Define scope, reference SOWs |
| **Payment** | Method, cycle, currency, late penalties |
| **IP** | Custom work → client; framework → vendor |
| **Confidentiality** | Mutual NDA on trade secrets |
| **Data & Security** | Ownership, usage, GDPR/CCPA compliance |
| **SLA** | Uptime (99.9%), response times, remedies |
| **Warranties** | Both parties warrant authority to execute |
| **Liability** | Cap (typically ≤ contract value) |
| **Term & Termination** | Duration, early termination conditions |
| **Governing Law** | Applicable law, dispute resolution |

---

## 4. Project Change Request (PCR) Template

**PCR ID:** [PCR-YYYYMMDD-XXX]
**Related SOW:** [SOW-YYYYMMDD-XXX]
**Requestor:** [Client/Vendor]
**Date:** [YYYY-MM-DD]

| Change Description |
|:---|
| (Detailed reason and content) |

| Impact Analysis |
|:---|
| **Scope Impact:** |
| **Timeline Impact:** (Delay/advance by X days) |
| **Cost Impact:** (Increase/decrease by $X) |

| Approval |
|:---|
| Vendor PM: Approve/Reject | Signature: | Date: |
| Client PM: Approve/Reject | Signature: | Date: |

---

## 5. Development Project Quote Template

**[Vendor Company] Project Quote**
- Client: [Client Company]
- Quote ID: [QT-YYYYMMDD-XXX]
- Date: [YYYY-MM-DD]
- Valid: 30 days

| Service | Description | Rate (USD) | Qty (person-days) | Total (USD) |
|:---|:---|:---|:---|:---|
| **Development** | | | | |
| | Requirements & Design | $800 | 10 | $8,000 |
| | AI Model Integration | $1,000 | 20 | $20,000 |
| | Backend API | $800 | 30 | $24,000 |
| | Frontend UI | $800 | 25 | $20,000 |
| | QA & Testing | $600 | 15 | $9,000 |
| **Other** | | | | |
| | PM Fee (10%) | | | $8,100 |
| **Total** | | | | **$89,100** |

### Payment Schedule
- **Milestone 1 (Contract signing):** 40% - $35,640
- **Milestone 2 (UAT passed):** 40% - $35,640
- **Milestone 3 (Go-live):** 20% - $17,820
