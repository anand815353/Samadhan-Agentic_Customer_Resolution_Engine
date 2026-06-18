# Samadhan Demo Seed Data Template (T-013)

This folder defines the **Excel workbook contract** for fake demo seed data. T-016 populates `users` and `customers` sheets; lending and other phases arrive in T-017+.

## Workbook location

```text
data/seed/master_excel/samadhan_demo_seed_data.xlsx
```

Regenerate workbook (headers + T-016 demo users/customers):

```bash
uv run python scripts/generate_seed_workbook.py
```

Canonical persona rows: `app/seed/demo_personas.py` (aligned with `app/core/demo_catalog.py`).

Machine-readable contract: `app/seed/template_spec.py`  
Manifest: `data/seed/seed_manifest.yaml`

## Fake data rules

- All customers, loans, transactions, and documents are **fake seeded demo data**
- Never use real PAN, mobile, Aadhaar, or customer PII
- Use masked/fake patterns only (e.g. `XXXXX1234A` for PAN, `98XXXX3210` for mobile)
- `password` column in `users` sheet is plaintext **demo seed input** (`Demo@123` default)
- Seed scripts (T-015/T-016) hash passwords via T-007 `hash_password` — **never store `password_hash` in Excel**
- `risk_segment_label` on customers is internal-only; must not appear in customer UI

## Stable ID strategy

| Entity | Pattern | Example |
|--------|---------|---------|
| User | `USR-ROLE-NNN` | `USR-CUST-001`, `USR-AGENT-001`, `USR-ADMIN-001` |
| Customer | `CUST-NNN` | `CUST-001` |
| Loan | `LN-YYYY-NNNN` | `LN-2026-0001` |
| Application | `APP-YYYY-NNNN` | `APP-2026-0001` |
| KYC | `KYC-YYYY-NNNN` | `KYC-2026-0001` |
| Transaction | `TXN-YYYY-NNNN` | `TXN-2026-0001` |
| Schedule | `SCH-YYYY-NNNN` | `SCH-2026-0001` |
| Ticket | `TKT-YYYY-NNNN` | `TKT-2026-0001` |
| Service Request | `SR-YYYY-NNNN` | `SR-2026-0001` |
| Refund | `REF-YYYY-NNNN` | `REF-2026-0001` |
| Fraud | `FRD-YYYY-NNNN` | `FRD-2026-0001` |
| Offer | `OFFER-YYYY-NNNN` | `OFFER-2026-0001` |
| Bureau log | `BRL-YYYY-NNNN` | `BRL-2026-0001` |
| RM mapping | `RM-YYYY-NNNN` | `RM-2026-0001` |
| Policy doc | `POL-DOMAIN-NNN` | `POL-KYC-001` |
| Audit | `AUD-YYYY-NNNN` | `AUD-2026-0001` |
| Eval case | `EVAL-INTENT-NNN` | `EVAL-FRAUD-001` |

## Demo personas (T-016 alignment)

| Customer ID | Name | Email | Scenario |
|-------------|------|-------|----------|
| CUST-001 | Ramesh Kumar | ramesh.demo@samadhan.ai | Loan pending due to KYC |
| CUST-002 | Priya Sharma | priya.demo@samadhan.ai | Loan rejected |
| CUST-003 | Arjun Mehta | arjun.demo@samadhan.ai | Duplicate EMI debit |
| CUST-004 | Sneha Verma | sneha.demo@samadhan.ai | Closed loan, NOC pending |
| CUST-005 | Imran Khan | imran.demo@samadhan.ai | CIBIL still showing active |
| CUST-006 | Kavita Rao | kavita.demo@samadhan.ai | Fraud/SMS alert |
| CUST-007 | Mohit Jain | mohit.demo@samadhan.ai | Eligible top-up offer |
| CUST-008 | Neha Singh | neha.demo@samadhan.ai | Not eligible for top-up |
| CUST-009 | Farhan Ali | farhan.demo@samadhan.ai | RM callback |
| CUST-010 | Anita Das | anita.demo@samadhan.ai | Loan statement request |

Support agent: `agent.demo@samadhan.ai` → `USR-AGENT-001`  
Admin: `admin.demo@samadhan.ai` → `USR-ADMIN-001`

## Workbook sheets (19 tabs)

| Sheet | MongoDB collection | Stable ID | Seed phase |
|-------|-------------------|-----------|------------|
| users | users | user_id | initial (T-016) |
| customers | customers | customer_id | initial (T-016) |
| loan_applications | loan_applications | application_id | lending (T-017) |
| loans | loans | loan_id | lending (T-017) |
| kyc_documents | kyc_documents | kyc_id | lending (T-017) |
| repayment_schedule | repayment_schedule | schedule_id | lending (T-017) |
| payment_transactions | payment_transactions | transaction_id | lending (T-017) |
| refund_requests | refund_requests | refund_request_id | ticketing (T-021+) |
| service_requests | service_requests | service_request_id | ticketing (T-023+) |
| bureau_reporting_logs | bureau_reporting_logs | bureau_log_id | bureau (T-018) |
| rm_mapping | rm_mapping | rm_mapping_id | bureau (T-018) |
| fraud_cases | fraud_cases | fraud_case_id | bureau (T-018) |
| offers | offers | offer_id | bureau (T-018) |
| tickets | tickets | ticket_id | ticketing (T-021+) |
| messages | messages | message_id | ticketing (T-022+) |
| audit_logs | audit_logs | audit_id | runtime (T-024+) |
| knowledge_documents | knowledge_documents | document_id | policies (T-019) |
| evaluation_cases | evaluation_cases | eval_case_id | evaluations (T-020) |
| usage_counters | usage_counters | counter_id | runtime |

**DATA_MODEL.md aliases:** `knowledge_documents` tab was `policy_documents`; `evaluation_cases` was `golden_eval_cases`.

## Relationships

```text
users.customer_id ──► customers.customer_id
customers ──► loan_applications, loans, kyc_documents, offers, rm_mapping
loan_applications ──► loans, kyc_documents
loans ──► repayment_schedule, payment_transactions, bureau_reporting_logs
tickets ──► messages, refund_requests, service_requests, fraud_cases, audit_logs
users ──► tickets.user_id, messages.sender_id, knowledge_documents.uploaded_by
evaluation_cases.customer_id ──► customers
```

## JSON columns

These Excel columns must contain valid JSON strings when populated (T-014 validates parse):

- `offers.tenure_options` — JSON array
- `messages.message_metadata` — JSON object
- `audit_logs.tool_input_masked`, `tool_output_summary`, `retrieved_policy_ids`, `raw_internal_trace`
- `evaluation_cases.expected_tools`, `expected_response_contains` — JSON arrays

## T-014 validation (implemented)

```bash
uv run python scripts/seed_demo_data.py --mode validate-only
```

Exit codes: `0` = passed, `1` = failed.

Validation stages:

1. Workbook file exists
2. All 19 required sheet tabs present
3. Each sheet header row contains required columns (from `template_spec.py`)
4. When data rows exist (row 2+):
   - Stable ID and required columns non-empty
   - No duplicate stable IDs per sheet
   - Enum values match `allowed_enums` where defined
   - JSON columns parse successfully
   - `users` with `role=customer` must have `customer_id`

Password values are never printed in error output. T-016 adds cross-sheet `customer_id` FK checks and `folder_path` directory validation. T-017 adds lending-sheet `foreign_keys` validation when lending rows exist. T-018 adds bureau/offers-sheet `foreign_keys` validation when bureau rows exist (ticket FK skipped until tickets sheet has data). T-019 adds policy `uploaded_by` FK validation and `storage_path` file checks for `knowledge_documents`. T-020 adds evaluation `customer_id` FK validation for `evaluation_cases`.

## T-020 golden evaluation seed (implemented)

Canonical golden cases: `app/seed/demo_evaluations.py` (aligned with DEMO_GUIDE, AGENT_WORKFLOW, and EVALUATION_AND_LLMOPS).

| Metric | Value |
|--------|-------|
| Active cases | 25 |
| Intent groups | 13 (minimum coverage per EVALUATION_AND_LLMOPS) |
| Stable ID pattern | `EVAL-{INTENT}-NNN` (e.g. `EVAL-EMI-001`, `EVAL-FRAUD-001`) |

Structured fields per case: `expected_intent`, `expected_risk_level`, `expected_priority`, `expected_ticket_class`, `expected_tools`, `expected_guardrail`, `expected_escalation`, `expected_service_request_type`, `expected_response_contains`, `forbidden_response_contains`, `expected_source_domain`, `active`.

Persona anchors: CUST-001 loan/KYC, CUST-002 rejection, CUST-003 EMI/refund, CUST-004 NOC, CUST-005 bureau, CUST-006 fraud, CUST-007/008 top-up, CUST-009 RM, CUST-010 statement/policy/unknown.

Evaluation runner (T-075+) consumes these rows; no runner logic in T-020.

Expected counts after reset (in addition to prior phases): `evaluation_cases` 25. Validate-only total data rows: **152**.

## T-019 policy metadata seed (implemented)

Canonical policy metadata rows: `app/seed/demo_policies.py`. Demo-safe Markdown placeholders live under `data/seed/policies/`.

| document_id | domain | source file |
|-------------|--------|-------------|
| POL-LOAN-STATUS-001 | loan_status | loan_application_status_policy.md |
| POL-REJECTION-001 | rejection | rejection_reason_policy.md |
| POL-KYC-001 | kyc | kyc_document_policy.md |
| POL-EMI-001 | emi | emi_payment_dispute_sop.md |
| POL-REFUND-001 | refund | refund_reversal_policy.md |
| POL-NOC-001 | noc | noc_and_loan_statement_sop.md |
| POL-BUREAU-001 | bureau | bureau_reporting_policy.md |
| POL-FRAUD-001 | fraud | fraud_security_sop.md |
| POL-TOPUP-001 | topup | topup_offer_policy.md |
| POL-RM-001 | rm | rm_callback_sop.md |
| POL-SAFETY-001 | safety | customer_response_safety_policy.md |

Initial metadata status: `approval_status=approved`, `indexed_status=not_indexed`, `chunk_count=0`, `uploaded_by=USR-ADMIN-001`. Indexing is deferred to T-043+.

Expected counts after reset (in addition to prior phases): `knowledge_documents` 11. Validate-only total data rows: **127**.

## T-018 bureau/offers seed (implemented)

Canonical bureau/offers rows: `app/seed/demo_bureau_offers.py` (aligned with MOCK_TOOLS_SPEC and DEMO_GUIDE personas CUST-005–009).

| Sheet | Rows | Scenario highlights |
|-------|------|----------------------|
| bureau_reporting_logs | 2 | Imran closed loan with CIBIL lag (`LN-2026-0005`) |
| offers | 2 | Mohit eligible ₹50k top-up; Neha ineligible with customer-safe reason |
| rm_mapping | 1 | Farhan assigned RM Amit Verma with callback available |
| fraud_cases | 1 | Kavita mock fraud case linked to `TXN-2026-0006` |

MOCK_TOOLS anchor IDs: `BRL-2026-0002`, `FRD-2026-0006`, `OFFER-2026-0001`, `RM-2026-0001`, `LN-2026-0005`.

Reserved placeholder: `fraud_cases.ticket_id=TKT-2026-0006` until T-021 seeds matching ticket rows. Fraud freeze fields use `MOCK-FREEZE-*` references only (mock simulation, not real freeze).

Expected counts after reset (in addition to T-016/T-017): `bureau_reporting_logs` 2, `offers` 2, `rm_mapping` 1, `fraud_cases` 1. Validate-only total data rows: **116**.

## T-017 lending seed (implemented)

Canonical lending rows: `app/seed/demo_lending.py` (aligned with MOCK_TOOLS_SPEC anchor IDs).

| Sheet | Rows (approx) | Scenario highlights |
|-------|---------------|----------------------|
| loan_applications | 10 | Ramesh pending KYC; Priya rejected with customer-safe reason |
| loans | 8 | Arjun active; Sneha closed NOC pending; Imran closed bureau pending_update |
| kyc_documents | 10 | Ramesh bank statement reupload_required |
| payment_transactions | 29 | Arjun duplicate EMI; Kavita fraud_alert; Anita 12+ EMI debits |
| repayment_schedule | 29 | Anita 12+ rows for statement; Arjun paid April EMI |

MOCK_TOOLS anchor IDs: `APP-2026-0001`, `APP-2026-0002`, `LN-2026-0003`, `LN-2026-0004`, `LN-2026-0005`.

Expected counts after reset (in addition to T-016): `loan_applications` 10, `loans` 8, `kyc_documents` 10, `payment_transactions` 29, `repayment_schedule` 29.

## T-016 demo users and customers (implemented)

The workbook includes **10 customer profiles** and **12 users** (10 customers + support agent + admin). Customer folder stubs live under `data/seed/customers/CUST-00N_Name/`.

After MongoDB is running and `.env` is configured:

```bash
uv run python scripts/seed_demo_data.py --mode validate-only
uv run python scripts/seed_demo_data.py --mode reset --env local
```

Expected counts after reset: `customers` inserted=10, `users` inserted=12. Passwords are bcrypt-hashed in MongoDB at load time. Login works when `MONGODB_URI` and `MONGODB_DB_NAME` are set (`MongoUserRepository`).

## T-015 reset and upsert (implemented)

Requires MongoDB configured via `.env` (`MONGODB_URI`, `MONGODB_DB_NAME`). Start local Mongo with Docker Compose before running.

```bash
uv run python scripts/seed_demo_data.py --mode reset --env local
uv run python scripts/seed_demo_data.py --mode upsert --env local
```

| Mode | Behavior |
|------|----------|
| `reset` | Validate workbook → clear 19 demo collections → reload rows from workbook |
| `upsert` | Validate workbook → upsert by stable ID (no delete) |

- Reset on non-`local` env requires `--force`
- Headers-only workbook succeeds with zero inserts (demo rows arrive in T-016+)
- Passwords are hashed at load time; plaintext passwords are never logged
- Per-collection `deleted` / `inserted` / `updated` counts are printed on stdout

## Out of scope for T-017+

- Bureau/offers/RM/fraud (T-018), policies (T-019), eval cases (T-020)
- Policy file content under `data/seed/policies/` (future tasks)
