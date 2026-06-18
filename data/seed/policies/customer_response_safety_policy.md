# Customer Response Safety Policy (Demo)

> Mock demo policy for Samadhan. Not a real compliance policy.

## Purpose

Ensure AI and agent responses remain safe for customers.

## Key points

- Mask PAN, mobile, Aadhaar-like numbers, loan account numbers, and transaction references in UI and logs.
- Never expose internal risk scores, model probabilities, underwriting thresholds, or raw tool payloads.
- Do not share internal fraud investigation playbooks or security rule details with customers.
- Use customer-safe summaries backed by approved policy and tool outputs only.
- Escalate when a response would require disclosing forbidden internal information.
