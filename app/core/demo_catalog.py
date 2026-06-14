"""Static demo metadata for the public /demo-access page (T-011).

Presentation-only catalog — not user seeding. Accounts are documented here
for recruiters; actual login requires T-016 seed data.
"""

from typing import Literal, TypedDict


class DemoAccount(TypedDict):
    email: str
    role: str
    scenario: str
    category: Literal["customer", "support_agent", "admin"]


class CustomerTestQuestion(TypedDict):
    email: str
    scenario: str
    query: str


class WalkthroughStep(TypedDict):
    title: str
    description: str
    available: bool


class RoleInstruction(TypedDict):
    role: str
    instructions: list[str]


DEFAULT_DEMO_PASSWORD = "Demo@123"

DEMO_PAGE_DISCLAIMER = (
    "This is a mock demo project. All customer data, loan records, transactions, "
    "bureau logs, documents, and actions are fake and seeded for demonstration. "
    "Samadhan does not connect to real banking, lending, payment, KYC, fraud, or bureau systems."
)

DEMO_ACCOUNTS: list[DemoAccount] = [
    {
        "email": "ramesh.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Loan pending due to KYC",
        "category": "customer",
    },
    {
        "email": "priya.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Loan rejected",
        "category": "customer",
    },
    {
        "email": "arjun.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Duplicate EMI debit",
        "category": "customer",
    },
    {
        "email": "sneha.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Closed loan, NOC pending",
        "category": "customer",
    },
    {
        "email": "imran.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "CIBIL still showing active",
        "category": "customer",
    },
    {
        "email": "kavita.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Fraud/SMS alert",
        "category": "customer",
    },
    {
        "email": "mohit.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Eligible top-up offer",
        "category": "customer",
    },
    {
        "email": "neha.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Not eligible for top-up",
        "category": "customer",
    },
    {
        "email": "farhan.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "RM callback",
        "category": "customer",
    },
    {
        "email": "anita.demo@samadhan.ai",
        "role": "Customer",
        "scenario": "Loan statement request",
        "category": "customer",
    },
    {
        "email": "agent.demo@samadhan.ai",
        "role": "Support Agent",
        "scenario": "Review escalated tickets",
        "category": "support_agent",
    },
    {
        "email": "admin.demo@samadhan.ai",
        "role": "Admin",
        "scenario": "Policies, audit logs, evaluations",
        "category": "admin",
    },
]

CUSTOMER_TEST_QUESTIONS: list[CustomerTestQuestion] = [
    {
        "email": "ramesh.demo@samadhan.ai",
        "scenario": "Loan pending due to KYC",
        "query": "Why is my loan still pending?",
    },
    {
        "email": "priya.demo@samadhan.ai",
        "scenario": "Loan rejected",
        "query": "Why was my loan rejected?",
    },
    {
        "email": "arjun.demo@samadhan.ai",
        "scenario": "Duplicate EMI debit",
        "query": "My EMI was deducted twice this month.",
    },
    {
        "email": "sneha.demo@samadhan.ai",
        "scenario": "Closed loan, NOC pending",
        "query": "I closed my loan. Where is my NOC?",
    },
    {
        "email": "imran.demo@samadhan.ai",
        "scenario": "CIBIL still showing active",
        "query": "I paid off my loan two months ago, but it is still showing active on CIBIL.",
    },
    {
        "email": "kavita.demo@samadhan.ai",
        "scenario": "Fraud/SMS alert",
        "query": "I got an SMS for a transaction I did not make. Block my account.",
    },
    {
        "email": "mohit.demo@samadhan.ai",
        "scenario": "Eligible top-up offer",
        "query": "Am I eligible for another loan?",
    },
    {
        "email": "neha.demo@samadhan.ai",
        "scenario": "Not eligible for top-up",
        "query": "Can I get more funds?",
    },
    {
        "email": "farhan.demo@samadhan.ai",
        "scenario": "RM callback",
        "query": "I want to speak to my relationship manager.",
    },
    {
        "email": "anita.demo@samadhan.ai",
        "scenario": "Loan statement request",
        "query": "I need my loan statement for the last financial year for my tax returns.",
    },
]

WALKTHROUGH_STEPS: list[WalkthroughStep] = [
    {
        "title": "Landing Page",
        "description": "Review the product overview, supported scenarios, and architecture highlights.",
        "available": True,
    },
    {
        "title": "Demo Access Page",
        "description": "Pick a scenario-specific demo account and note the shared demo password.",
        "available": True,
    },
    {
        "title": "Customer Login",
        "description": "Sign in with a customer demo account after running seed reset.",
        "available": True,
    },
    {
        "title": "Customer Chat Scenario",
        "description": "Ask a recommended test question and observe intent, tools, and guardrails.",
        "available": False,
    },
    {
        "title": "Ticket Creation",
        "description": "Verify Tier 2, Tier 1 service request, or Human Review ticket routing.",
        "available": False,
    },
    {
        "title": "Support Agent Dashboard",
        "description": "Review escalated Human Review tickets as the support agent.",
        "available": False,
    },
    {
        "title": "Audit Trail",
        "description": "Inspect masked audit logs for intent, tool calls, and guardrail decisions.",
        "available": False,
    },
    {
        "title": "Admin Policy/Evaluation View",
        "description": "Upload policy docs, view evaluations, and review admin audit views.",
        "available": False,
    },
]

ROLE_INSTRUCTIONS: list[RoleInstruction] = [
    {
        "role": "Customer",
        "instructions": [
            "Log in with a scenario-specific customer demo account.",
            "Open customer chat and ask the recommended test question for that persona.",
            "Confirm responses stay customer-safe and use mock data only.",
            "Check that high-risk cases create Human Review tickets instead of auto-closing.",
        ],
    },
    {
        "role": "Support Agent",
        "instructions": [
            "Log in as agent.demo@samadhan.ai.",
            "Open the Human Review queue and review escalated tickets.",
            "Inspect masked tool outputs and audit context before taking action.",
            "Update ticket status using support-agent workflows when available.",
        ],
    },
    {
        "role": "Admin",
        "instructions": [
            "Log in as admin.demo@samadhan.ai.",
            "Review policy upload and re-indexing flows when implemented.",
            "Inspect audit logs with sensitive values masked.",
            "View golden evaluation results and LLMOps dashboards when available.",
        ],
    },
]
