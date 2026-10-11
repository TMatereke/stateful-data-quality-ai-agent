from openai import OpenAI
import csv
from datetime import datetime
import os
import uuid
import json
import re
from openai import NotFoundError
client = OpenAI()
RUN_ID = str(uuid.uuid4())[:8]
WORKFLOW_NAME = "CustomerDataQuality"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

def get_sales_data():
    return {
        "January": 120000,
        "February": 135000,
        "March": 150000
    }

def calculate_sales_metrics(sales_data):    
    january_sales = sales_data["January"]
    february_sales = sales_data["February"]
    march_sales = sales_data["March"]

    highest_month = max(sales_data, key=sales_data.get)
    total_sales = january_sales + february_sales + march_sales
    percentage_increase = ((march_sales - january_sales) / january_sales) * 100

    return {
        "highest_sales_month": highest_month,
        "highest_sales_value": sales_data[highest_month],
        "total_sales": total_sales,
        "january_to_march_percentage_increase": percentage_increase
    }
def get_customer_data():
    return {
        "Acme": 85000,
        "Globex": 62000,
        "Initech": 91000,
        "Umbrella": 47000
    }
def get_customer_data_from_csv():
    customers = {}

    with open("day01/customers.csv", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                customers[row["Customer"]] = int(row["Revenue"])
            except ValueError:
                customers[row["Customer"]] = None

    return customers

SESSION_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "agent_session.json"
)  
def load_agent_session():
    """Load the OpenAI session from conversation memory."""

    memory = load_conversation_memory()

    return {
        "conversation_id": memory.get("conversation_id"),
        "updated_at": memory.get("session_updated_at"),
    }


def save_agent_session(conversation_id):
    """Save the OpenAI session into conversation memory."""

    memory = load_conversation_memory()

    memory["conversation_id"] = conversation_id
    memory["session_updated_at"] = datetime.now().isoformat()

    save_conversation_memory(memory)

    return {
        "conversation_id": conversation_id,
        "updated_at": memory["session_updated_at"],
    } 
def check_customer_data_quality():
    customers = get_customer_data_from_csv()

    missing_revenue = []
    negative_revenue = []
    duplicate_customers = []

    with open("day01/customers.csv", newline="") as file:
        reader = csv.DictReader(file)
        total_records = 0
        seen_customers = set()

        for row in reader:
            customer = row["Customer"]
            total_records += 1

            if customer in seen_customers:
                duplicate_customers.append(customer)

            seen_customers.add(customer)
        duplicate_record_count = len(duplicate_customers)
        for customer, revenue in customers.items():

            if revenue is None:
                missing_revenue.append(customer)
                continue

            if revenue < 0:
                negative_revenue.append(customer)



    issues = []

    for customer in missing_revenue:
        issues.append({
        "customer": customer,
        "issue": "Missing or invalid revenue",
        "severity": "HIGH",
        "action": "Investigate and correct the revenue value before processing the data."
    })

    for customer in negative_revenue:
        issues.append({
        "customer": customer,
        "issue": "Negative revenue",
        "severity": "HIGH",
        "priority": "Immediate attention",
        "action": "Investigate the negative revenue value and correct it if it is invalid."
    })

    for customer in set(duplicate_customers):
        issues.append({
        "customer": customer,
        "issue": "Duplicate customer",
        "severity": "MEDIUM",
        "priority": "Review",
        "action": "Review the duplicate records and determine which record should be retained."
    })

    severity_weights = {
        "HIGH": 20,
        "MEDIUM": 10
    }

    penalty = 0

    for issue in issues:
        penalty += severity_weights[issue["severity"]]

    quality_score = max(0, 100 - penalty)
    if quality_score >= 90:
        quality_rating = "Excellent"
    elif quality_score >= 75:
            quality_rating = "Good"
    elif quality_score >= 50:
        quality_rating = "Needs Attention"
    else:
        quality_rating = "Poor"

    return {
        "total_records": total_records,
        "unique_customers": len(customers),
        "duplicate_records": duplicate_record_count,
        "issues": issues,
        "quality_score": quality_score,
        "quality_rating": quality_rating,
        "data_quality_status": "PASS" if not issues else "FAIL"
    }
def determine_data_quality_status():
    result = check_customer_data_quality()

    issue_count = len(result["issues"])

    if issue_count > 0:
        return {
            "status": "FAIL",
            "issue_count": issue_count,
            "message": "Data quality issues remain."
        }

    return {
        "status": "PASS",
        "issue_count": 0,
        "message": "No data quality issues found."
    }
def verify_customer_data_quality():
    quality_result = check_customer_data_quality()

    return {
        "verification_status": "PASS" if not quality_result["issues"] else "FAIL",
        "remaining_issues": quality_result["issues"],
        "quality_score": quality_result["quality_score"],
        "quality_rating": quality_result["quality_rating"]
    }
def fix_negative_revenue(
    customer,
    replacement_revenue,
    approved_by=None,
    approved_at=None,
    approval_id=None
):
    customers = get_customer_data_from_csv()

    if customer not in customers:
        log_agent_action(
                action="FIX_NEGATIVE_REVENUE_FAILED",
                customer=customer,
                old_value=None,
                new_value=replacement_revenue,
                approval_status="APPROVED"
                ) 
        
        return {
            "status": "FAILED",
            "message": f"Customer {customer} was not found."
        }

    current_revenue = customers[customer]

    if current_revenue is None:
        log_agent_action(
            action="FIX_NEGATIVE_REVENUE_FAILED",
            customer=customer,
            old_value=current_revenue,
            new_value=replacement_revenue,
            approval_status="APPROVED"
        )     
        return {
            "status": "FAILED",
            "message": f"Customer {customer} has missing or invalid revenue."
        }

    if current_revenue >= 0:
        log_agent_action(
            action="FIX_NEGATIVE_REVENUE_NO_ACTION",
            customer=customer,
            old_value=current_revenue,
            new_value=replacement_revenue
        )
        return {
            "status": "NO_ACTION",
            "message": f"{customer} does not have negative revenue.",
            "current_revenue": current_revenue
        }
    try:
        replacement_revenue = int(replacement_revenue)
    except (ValueError, TypeError):
        return {
            "status": "REJECTED",
            "message": "Replacement revenue must be a valid integer."
        }
    if replacement_revenue < 0:
        log_agent_action(
            action="FIX_NEGATIVE_REVENUE",
            approval_id=approval_id,
            customer=customer,
            old_value=current_revenue,
            new_value=replacement_revenue,
            approval_status="APPROVED",
            approved_by=approved_by,
            approved_at=approved_at
        )
        
        return {
            "status": "FAILED",
            "message": "Replacement revenue must not be negative."
        }

        # SECURITY CHECK: authorization is required before any file write.

    if not isinstance(approval_id, str) or not approval_id.strip():
        return {
            "status": "REJECTED",
            "message": "A valid approval ID is required."
        }

    if not isinstance(approved_by, str) or not approved_by.strip():
        return {
            "status": "REJECTED",
            "message": "An approved reviewer identity is required."
        }

    if not approved_at:
        return {
            "status": "REJECTED",
            "message": "The approval timestamp is required."
        }

    # Retrieve authorization from the approval registry.
    approval = get_approved_replacement(customer)

    if approval.get("status") != "APPROVED":
        return {
            "status": "REJECTED",
            "message": (
                "No valid, currently approved remediation "
                "was found for this customer."
            )
        }

    if approval.get("approval_id") != approval_id.strip():
        return {
            "status": "REJECTED",
            "message": "The approval ID does not match the approved request."
        }

    if approval.get("replacement_revenue") != replacement_revenue:
        return {
            "status": "REJECTED",
            "message": "Replacement revenue does not match the approved amount."
        }

    if approval.get("approved_by") != approved_by.strip():
        return {
            "status": "REJECTED",
            "message": "The approver does not match the approved request."
        }

    if approval.get("approved_at") != approved_at:
        return {
            "status": "REJECTED",
            "message": "The approval timestamp does not match the registry."
        }
    rows = []

    with open("day01/customers.csv", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["Customer"] == customer:
                row["Revenue"] = str(replacement_revenue)

            rows.append(row)

    # Write the updated data only after all rows
    # have successfully been read and prepared.
    with open("day01/customers.csv", "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["RecordID", "Customer", "Revenue"]
        )

        writer.writeheader()
        writer.writerows(rows)
        log_agent_action(
    action="FIX_NEGATIVE_REVENUE",
    approval_id=approval_id,
    customer=customer,
    old_value=current_revenue,
    new_value=replacement_revenue,
    approval_status="APPROVED",
    approved_by=approved_by,
    approved_at=approved_at
)

    return {
        "status": "FIXED",
        "approval_id": approval_id,
        "customer": customer,
        "old_revenue": current_revenue,
        "new_revenue": replacement_revenue
    }
def inspect_duplicate_customer(customer):
    duplicate_records = []

    with open("day01/customers.csv", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["Customer"] == customer:
                duplicate_records.append({
                    "customer": row["Customer"],
                    "revenue": row["Revenue"]
                })

    if len(duplicate_records) <= 1:
        return {
            "status": "NO_DUPLICATE",
            "customer": customer,
            "records": duplicate_records
        }

    return {
        "status": "DUPLICATE_FOUND",
        "customer": customer,
        "record_count": len(duplicate_records),
        "records": duplicate_records
    }
def remove_duplicate_customer(record_id):
    rows = []
    removed = False
    removed_record = None

    with open("day01/customers.csv", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["RecordID"] == str(record_id) and not removed:
                removed = True
                removed_record = row
                continue

            rows.append(row)

    if not removed:
        return {
            "status": "NOT_FOUND",
            "record_id": record_id,
            "message": "The specified record was not found."
        }

    with open("day01/customers.csv", "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["RecordID", "Customer", "Revenue"]
        )

        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "REMOVED",
        "record_id": record_id,
        "customer": removed_record["Customer"],
        "revenue_removed": removed_record["Revenue"]
    }
def get_approved_replacement(customer):
    approval_file = "day01/approval_registry.csv"

    if not os.path.exists(approval_file):
        return {
            "status": "REJECTED",
            "reason": "Approval registry does not exist.",
            "approval_id": None,
            "replacement_revenue": None,
            "approved_by": None,
            "approved_at": None
        }

    matching_rows = []

    with open(approval_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["Customer"] == customer:
                matching_rows.append(row)

    if not matching_rows:
        return {
            "status": "REJECTED",
            "reason": "No approval record found for this customer.",
            "approval_id": None,
            "replacement_revenue": None,
            "approved_by": None,
            "approved_at": None
        }

    # Use the latest approval request for this customer.
    row = matching_rows[-1]

    approval_status = row["ApprovalStatus"]

    if approval_status != "APPROVED":
        return {
            "status": "REJECTED",
            "reason": f"Approval status is {approval_status}.",
            "approval_id": row.get("ApprovalID") or None,
            "replacement_revenue": None,
            "approved_by": row.get("ApprovedBy") or None,
            "approved_at": row.get("ApprovedAt") or None
        }

    try:
        replacement_revenue = int(row["ReplacementRevenue"])
    except (ValueError, TypeError):
        return {
            "status": "REJECTED",
            "reason": "Approved replacement revenue is not a valid integer.",
            "approval_id": row.get("ApprovalID") or None,
            "replacement_revenue": None,
            "approved_by": row.get("ApprovedBy") or None,
            "approved_at": row.get("ApprovedAt") or None
        }

    if replacement_revenue <= 0:
        return {
            "status": "REJECTED",
            "reason": "Approved replacement revenue must be greater than zero.",
            "approval_id": row.get("ApprovalID") or None,
            "replacement_revenue": None,
            "approved_by": row.get("ApprovedBy") or None,
            "approved_at": row.get("ApprovedAt") or None
        }

    return {
        "status": "APPROVED",
        "reason": "Valid approved replacement found.",
        "approval_id": row.get("ApprovalID") or None,
        "replacement_revenue": replacement_revenue,
        "approved_by": row.get("ApprovedBy") or None,
        "approved_at": row.get("ApprovedAt") or None
    }
def request_remediation_approval(
    customer,
    proposed_replacement,
    reason
):
    approval_file = "day01/approval_registry.csv"

    try:
        proposed_replacement = int(proposed_replacement)
    except (ValueError, TypeError):
        return {
            "status": "REJECTED",
            "reason": "Proposed replacement revenue must be a valid integer."
        }

    if proposed_replacement <= 0:
        return {
            "status": "REJECTED",
            "reason": "Proposed replacement revenue must be greater than zero."
        }

    fieldnames = [
        "ApprovalID",
        "Customer",
        "ReplacementRevenue",
        "ApprovalStatus",
        "ApprovedBy",
        "ApprovedAt",
        "ConsumedAt"
    ]

    existing_rows = []

    if os.path.exists(approval_file) and os.path.getsize(approval_file) > 0:

        with open(approval_file, "r", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                
                existing_rows.append({
                    "ApprovalID": row.get("ApprovalID", ""),
                    "Customer": row.get("Customer", ""),
                    "ReplacementRevenue": row.get("ReplacementRevenue", ""),
                    "ApprovalStatus": row.get("ApprovalStatus", ""),
                    "ApprovedBy": row.get("ApprovedBy", ""),
                    "ApprovedAt": row.get("ApprovedAt", ""),
                    "ConsumedAt": row.get("ConsumedAt", "")
                })

    # Do not create a duplicate pending request
    for row in reversed(existing_rows):
        if row["Customer"] == customer:
            if row["ApprovalStatus"] == "PENDING":
                return {
                    "status": "ALREADY_PENDING",
                    "customer": customer,
                    "proposed_replacement": proposed_replacement,
                    "reason": reason
                }

            # Stop here only after checking the latest request.
            break
    approval_id = uuid.uuid4().hex[:8]
    existing_rows.append({
        "ApprovalID": approval_id,
        "Customer": customer,
        "ReplacementRevenue": proposed_replacement,
        "ApprovalStatus": "PENDING",
        "ApprovedBy": "",
        "ApprovedAt": "",
        "ConsumedAt": ""
    })

    with open(approval_file, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(existing_rows)

    log_agent_action(
        action="REQUEST_REMEDIATION_APPROVAL",
        approval_id=approval_id,
        customer=customer,
        old_value=None,
        new_value=proposed_replacement,
        approval_status="PENDING",
        verification_status=None,
        approved_by=None,
        approved_at=None
    )

    return {
        "status": "PENDING_APPROVAL",
        "approval_id": approval_id,
        "customer": customer,
        "proposed_replacement": proposed_replacement,
        "reason": reason
    }
def get_pending_approval_requests():
    approval_file = "day01/approval_registry.csv"

    if not os.path.exists(approval_file):
        return {
            "status": "NO_APPROVAL_FILE",
            "pending_requests": []
        }

    pending_requests = []

    with open(approval_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["ApprovalStatus"] == "PENDING":
                pending_requests.append({
                    "customer": row["Customer"],
                    "proposed_replacement": int(row["ReplacementRevenue"]),
                    "approval_status": row["ApprovalStatus"],
                    "approved_by": row.get("ApprovedBy") or None,
                    "approved_at": row.get("ApprovedAt") or None
                })

    return {
        "status": "OK",
        "pending_count": len(pending_requests),
        "pending_requests": pending_requests
    }
def approve_remediation_request(approval_id, approved_by):
    approval_file = "day01/approval_registry.csv"

    if not approval_id or not approval_id.strip():
        return {
            "status": "REJECTED",
            "reason": "An approval ID is required."
        }

    if not approved_by or not approved_by.strip():
        return {
            "status": "REJECTED",
            "reason": "An approver identity is required."
        }

    if not os.path.exists(approval_file):
        return {
            "status": "REJECTED",
            "reason": "Approval registry does not exist."
        }

    with open(approval_file, "r", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if fieldnames is None:
        return {
            "status": "REJECTED",
            "reason": "Approval registry has no valid header."
        }

    if "ApprovalID" not in fieldnames:
        return {
            "status": "REJECTED",
            "reason": "Approval registry does not contain ApprovalID."
        }

    matching_rows = [
        row for row in rows
        if row.get("ApprovalID") == approval_id
    ]

    if not matching_rows:
        return {
            "status": "REJECTED",
            "approval_id": approval_id,
            "reason": "No approval request found for this ApprovalID."
        }

    row = matching_rows[0]

    if row["ApprovalStatus"] != "PENDING":
        return {
            "status": "REJECTED",
            "approval_id": approval_id,
            "reason": (
                f"Approval request is not pending. "
                f"Current status: {row['ApprovalStatus']}."
            )
        }

    try:
        replacement_revenue = int(row["ReplacementRevenue"])
    except (ValueError, TypeError):
        return {
            "status": "REJECTED",
            "approval_id": approval_id,
            "reason": "The pending replacement revenue is invalid."
        }

    if replacement_revenue <= 0:
        return {
            "status": "REJECTED",
            "approval_id": approval_id,
            "reason": "The replacement revenue must be greater than zero."
        }

    approved_at = datetime.now().isoformat()

    row["ApprovalStatus"] = "APPROVED"
    row["ApprovedBy"] = approved_by.strip()
    row["ApprovedAt"] = approved_at

    with open(approval_file, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(rows)

    log_agent_action(
        action="APPROVE_REMEDIATION_REQUEST",
        approval_id=approval_id,
        customer=row["Customer"],
        old_value=None,
        new_value=replacement_revenue,
        approval_status="APPROVED",
        verification_status=None,
        approved_by=approved_by.strip(),
        approved_at=approved_at
    )

    return {
        "status": "APPROVED",
        "approval_id": approval_id,
        "customer": row["Customer"],
        "replacement_revenue": replacement_revenue,
        "approved_by": approved_by.strip(),
        "approved_at": approved_at
    }
def consume_remediation_approval(approval_id):
    approval_file = "day01/approval_registry.csv"

    if not os.path.exists(approval_file):
        return {
            "status": "REJECTED",
            "reason": "Approval registry does not exist."
        }

    with open(approval_file, "r", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if fieldnames is None:
        return {
            "status": "REJECTED",
            "reason": "Approval registry has no valid header."
        }

    matching_indexes = [
    index
    for index, row in enumerate(rows)
    if (
        row.get("ApprovalID") == approval_id
        and row["ApprovalStatus"] == "APPROVED"
    )
]

    if not matching_indexes:
        return {
            "status": "NOT_CONSUMED",
            "approval_id": approval_id,
            "reason": "No approved remediation was found to consume."
        }

    # Consume the latest approved request only.
    latest_index = matching_indexes[-1]
    row = rows[latest_index]

    consumed_at = datetime.now().isoformat()
    customer = row["Customer"]
    row["ApprovalStatus"] = "CONSUMED"

    if "ConsumedAt" in fieldnames:
        row["ConsumedAt"] = consumed_at

    with open(approval_file, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(rows)

    log_agent_action(
        action="CONSUME_REMEDIATION_APPROVAL",
        approval_id=approval_id,
        customer=row["Customer"],
        old_value=None,
        new_value=row["ReplacementRevenue"],
        approval_status="CONSUMED",
        verification_status=None,
        approved_by=row.get("ApprovedBy"),
        approved_at=row.get("ApprovedAt")
    )

    return {
        "status": "CONSUMED",
        "approval_id": approval_id,
        "customer": row["Customer"],
        "consumed_at": consumed_at,
        "approved_by": row.get("ApprovedBy"),
        "approved_at": row.get("ApprovedAt")
    }

STATE_FILE = "day01/agent_state.json"


def load_agent_state():
    default_state = {
        "version": 1,
        "updated_at": None,
        "last_run": None,
        "run_history": []
    }

    if not os.path.exists(STATE_FILE):
        return default_state

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            return default_state

        # Backward compatibility:
        # migrate the previous single last_run into run_history.
        if "run_history" not in state:
            state["run_history"] = []

            if state.get("last_run") is not None:
                state["run_history"].append(state["last_run"])

        return state

    except (json.JSONDecodeError, OSError):
        return default_state

CONVERSATION_MEMORY_FILE = "day01/conversation_memory.json"

def load_conversation_memory():
    default_memory = {
        "conversation_id": None,
        "session_updated_at": None,
        "version": 2,
        "messages": [],
        "summary": "",
        "memory_context": {
            "active_customer": None,
            "last_topic": None,
            "last_tool": None,
            "last_approval_id": None,
            "last_workflow_status": None,
            "last_business_snapshot": None,
             "customers": {}
        }
    }

    if not os.path.exists(CONVERSATION_MEMORY_FILE):
        return default_memory

    try:
        with open(
            CONVERSATION_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            memory = json.load(file)

        if not isinstance(memory, dict):
            return default_memory

        # Migrate older memory versions.
        current_version = memory.get("version", 1)

        if current_version < 2:
            memory["version"] = 2
            memory.setdefault("messages", [])
            memory.setdefault("summary", "")
            memory.setdefault("conversation_id", None)
            memory.setdefault("session_updated_at", None)

        # -----------------------------------------------------
        # Ensure memory_context exists.
        # -----------------------------------------------------
        memory.setdefault(
            "memory_context",
            {
                "active_customer": None,
                "last_topic": None,
                "last_tool": None,
                "last_approval_id": None,
                "last_workflow_status": None,
                "last_business_snapshot": None,
                "customers": {}
            }
        )

        context = memory["memory_context"]
        context.setdefault("active_customer", None)
        context.setdefault("last_topic", None)
        context.setdefault("last_tool", None)
        context.setdefault("last_approval_id", None)
        context.setdefault("last_workflow_status", None)
        context.setdefault("last_business_snapshot", None)
        context.setdefault("customers", {})

        return memory

    except (json.JSONDecodeError, OSError):
        return default_memory

def update_memory_context(
    user_query=None,
    tool_name=None,
    tool_result=None
):
    memory = load_conversation_memory()

    context = memory["memory_context"]

    # ---------------------------------------------------------
    # 1. Detect the customer from the user's question.
    # ---------------------------------------------------------
    if user_query:
        try:
            customers = get_customer_data_from_csv()
            customer_names = list(customers.keys())

            for customer in sorted(
                customer_names,
                key=len,
                reverse=True
            ):
                pattern = r"\b" + re.escape(customer) + r"\b"

                if re.search(
                    pattern,
                    user_query,
                    re.IGNORECASE
                ):
                    context["active_customer"] = customer
                    break

        except Exception:
            pass

        # -----------------------------------------------------
        # 2. Detect the topic.
        # -----------------------------------------------------
        query = user_query.lower()

        if any(
            word in query
            for word in [
                "current state",
                "status",
                "how is",
                "current revenue"
            ]
        ):
            context["last_topic"] = "customer_state"

        elif any(
            word in query
            for word in [
                "history",
                "what happened",
                "recently",
                "previous"
            ]
        ):
            context["last_topic"] = "customer_history"

        elif any(
            word in query
            for word in [
                "approval",
                "approved",
                "approver",
                "permission"
            ]
        ):
            context["last_topic"] = "approval"

        elif any(
            word in query
            for word in [
                "remediation",
                "corrected",
                "fixed",
                "repair"
            ]
        ):
            context["last_topic"] = "remediation"

        elif any(
            word in query
            for word in [
                "run",
                "workflow",
                "quality check",
                "data quality"
            ]
        ):
            context["last_topic"] = "workflow"

    # ---------------------------------------------------------
    # 3. Record the last tool used.
    # ---------------------------------------------------------
    if tool_name:
        context["last_tool"] = tool_name

    # ---------------------------------------------------------
    # 4. Process tool results.
    # ---------------------------------------------------------
    if isinstance(tool_result, dict):

        customer = tool_result.get("customer")

        approval_id = tool_result.get("approval_id")

        if approval_id:
            context["last_approval_id"] = approval_id

        # -----------------------------------------------------
        # get_customer_state()
        # -----------------------------------------------------
        if (
            tool_name == "get_customer_state"
            and customer
            ):
            latest_approval = tool_result.get(
                "latest_approval"
            )

            latest_remediation = tool_result.get(
                "latest_remediation"
            )

            latest_verification = tool_result.get(
                "latest_verification"
            )

            context["last_business_snapshot"] = {
                "customer": customer,
                "current_revenue": tool_result.get(
                    "current_revenue"
                ),
                "latest_approval": latest_approval,
                "latest_remediation": latest_remediation,
                "latest_verification": latest_verification
            }
            context.setdefault("customers", {})

            context["customers"][customer] = {
                "current_revenue": tool_result.get(
                    "current_revenue"
                ),
                "latest_approval": latest_approval,
                "latest_remediation": latest_remediation,
                "latest_verification": latest_verification,
                "last_updated": datetime.now().isoformat()
            }

            # Approval ID is nested inside latest_approval.
            if (
                isinstance(latest_approval, dict)
                and latest_approval.get("approval_id")
            ):
                context["last_approval_id"] = (
                    latest_approval["approval_id"]
                )

        # -----------------------------------------------------
        # run_quality_workflow()
        # -----------------------------------------------------
        if tool_name == "run_quality_workflow":

            final_status = tool_result.get(
                "final_status"
            )

            if isinstance(final_status, dict):
                context["last_workflow_status"] = (
                    final_status.get("status")
                )

            context["last_business_snapshot"] = {
                "workflow": "CustomerDataQuality",
                "final_status": final_status,
                "verification": tool_result.get(
                    "verification"
                ),
                "remediation_summary": tool_result.get(
                    "remediation_summary"
                )
            }

            # Try to capture the approval ID from the
            # remediation summary.
            remediation_summary = tool_result.get(
                "remediation_summary",
                []
            )

            if remediation_summary:
                for item in reversed(remediation_summary):
                    candidate_id = item.get(
                        "approval_id"
                    )

                    if candidate_id:
                        context["last_approval_id"] = (
                            candidate_id
                        )
                        break

        # -----------------------------------------------------
        # get_customer_history()
        # -----------------------------------------------------
        if (
            tool_name == "get_customer_history"
            and customer
        ):
            events = tool_result.get(
                "events",
                []
            )

            if events:

                # Search newest events first for an
                # approval ID.
                for event in reversed(events):
                    candidate_id = event.get(
                        "approval_id"
                    )

                    if candidate_id:
                        context["last_approval_id"] = (
                            candidate_id
                        )
                        break

        # -----------------------------------------------------
        # get_agent_state()
        # -----------------------------------------------------
        if tool_name == "get_agent_state":

            state = tool_result.get(
                "state"
            )

            if isinstance(state, dict):

                last_run = state.get(
                    "last_run"
                )

                if isinstance(last_run, dict):
                    status = last_run.get(
                        "status"
                    )

                    if status:
                        context["last_workflow_status"] = (
                            status
                        )

    memory["memory_context"] = context

    save_conversation_memory(memory)

    return memory
def get_memory_context():
    memory = load_conversation_memory()

    context = memory.get(
        "memory_context",
        {}
    )

    return {
        "status": "OK",
        "memory_context": {
            "active_customer": context.get("active_customer"),
            "last_topic": context.get("last_topic"),
            "last_tool": context.get("last_tool"),
            "last_approval_id": context.get("last_approval_id"),
            "last_workflow_status": context.get("last_workflow_status"),
            "last_business_snapshot": context.get(
                "last_business_snapshot"
            )
        }
    }
def save_conversation_memory(memory):
    temp_file = CONVERSATION_MEMORY_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            memory,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_file,
        CONVERSATION_MEMORY_FILE
    )


def add_conversation_message(role, content):
    memory = load_conversation_memory()

    memory["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })

    memory["messages"] = memory["messages"][-20:]

    save_conversation_memory(memory)

    update_conversation_summary()

    return memory

def get_conversation_memory(limit=10):
    memory = load_conversation_memory()

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 10

    limit = max(1, min(limit, 20))

    messages = memory["messages"][-limit:]

    return {
        "status": "OK",
        "message_count": len(messages),
        "summary": memory.get("summary", ""),
        "messages": messages
    }



def save_agent_state(state):
    state["updated_at"] = datetime.now().isoformat()

    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            indent=2
        )

    os.replace(temp_file, STATE_FILE)

def update_last_run_state(
    quality_result,
    verification_result,
    final_status,
    remediation_summary
):
    state = load_agent_state()

    new_run = {
        "run_id": RUN_ID,
        "workflow": WORKFLOW_NAME,
        "completed_at": datetime.now().isoformat(),
        "status": final_status["status"],
        "quality_score": quality_result["quality_score"],
        "quality_rating": quality_result["quality_rating"],
        "issue_count": len(quality_result["issues"]),
        "issues": quality_result["issues"],
        "verification": verification_result,
        "remediation_summary": remediation_summary
    }

    history = state.get("run_history", [])

    history.append(new_run)

    # Keep only the latest 5 runs
    state["run_history"] = history[-5:]

    # Keep last_run for backwards compatibility
    state["last_run"] = new_run

    save_agent_state(state)

    return state
def get_agent_state():
    state = load_agent_state()

    return {
        "status": "OK",
        "state": state
    }
def get_run_history(limit=5):
    state = load_agent_state()

    history = state.get("run_history", [])

    if not history:
        return {
            "status": "OK",
            "run_count": 0,
            "runs": []
        }

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 5

    limit = max(1, min(limit, 10))

    selected_runs = history[-limit:]

    return {
        "status": "OK",
        "run_count": len(selected_runs),
        "runs": selected_runs
    }
def get_customer_history(customer, limit=10):
    audit_file = "day01/agent_audit.csv"

    if not os.path.exists(audit_file):
        return {
            "status": "NO_AUDIT_FILE",
            "customer": customer,
            "event_count": 0,
            "events": []
        }

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 10

    limit = max(1, min(limit, 50))

    events = []

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get("Customer") == customer:
                events.append({
                    "run_id": row.get("RunID"),
                    "timestamp": row.get("Timestamp"),
                    "action": row.get("Action"),
                    "approval_id": row.get("ApprovalID") or None,
                    "old_value": row.get("OldValue") or None,
                    "new_value": row.get("NewValue") or None,
                    "approval_status": row.get("ApprovalStatus") or None,
                    "verification_status": row.get("VerificationStatus") or None,
                    "approved_by": row.get("ApprovedBy") or None,
                    "approved_at": row.get("ApprovedAt") or None
                })

    events = events[-limit:]

    return {
        "status": "OK",
        "customer": customer,
        "event_count": len(events),
        "events": events
    }
def get_customer_state(customer):
    customers = get_customer_data_from_csv()

    if customer not in customers:
        return {
            "status": "NOT_FOUND",
            "customer": customer
        }

    current_revenue = customers[customer]

    approval_file = "day01/approval_registry.csv"

    latest_approval = None

    if os.path.exists(approval_file):
        with open(approval_file, "r", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row.get("Customer") == customer:
                    latest_approval = {
                        "approval_id": row.get("ApprovalID") or None,
                        "replacement_revenue": row.get("ReplacementRevenue") or None,
                        "status": row.get("ApprovalStatus") or None,
                        "approved_by": row.get("ApprovedBy") or None,
                        "approved_at": row.get("ApprovedAt") or None,
                        "consumed_at": row.get("ConsumedAt") or None
                    }

    latest_remediation = None
    latest_verification = None

    audit_file = "day01/agent_audit.csv"

    if os.path.exists(audit_file):
        with open(audit_file, "r", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row.get("Customer") != customer:
                    continue

                if row.get("Action") == "FIX_NEGATIVE_REVENUE":
                    latest_remediation = {
                        "approval_id": row.get("ApprovalID") or None,
                        "old_value": row.get("OldValue") or None,
                        "new_value": row.get("NewValue") or None,
                        "status": row.get("VerificationStatus") or "FIXED",
                        "approved_by": row.get("ApprovedBy") or None,
                        "approved_at": row.get("ApprovedAt") or None,
                        "timestamp": row.get("Timestamp")
                    }

                elif row.get("Action") == "VERIFY_REMEDIATION":
                    latest_verification = {
                        "approval_id": row.get("ApprovalID") or None,
                        "status": row.get("VerificationStatus") or None,
                        "timestamp": row.get("Timestamp")
                    }

    return {
        "status": "OK",
        "customer": customer,
        "current_revenue": current_revenue,
        "latest_approval": latest_approval,
        "latest_remediation": latest_remediation,
        "latest_verification": latest_verification
    }
def run_quality_workflow():
    quality_result = check_customer_data_quality()

    remediation_summary = []

    for issue in quality_result["issues"]:

        approval = get_approved_replacement(
            issue["customer"]
        )

        approved_value = approval["replacement_revenue"]

        remediation_result = None
        consumption_result = None

        # Execute a repair only when:
        # 1. The issue is negative revenue
        # 2. An approved replacement exists
        if (
            issue["issue"] == "Negative revenue"
            and approval["status"] == "APPROVED"
        ):

            remediation_result = fix_negative_revenue(
                issue["customer"],
                approved_value,
                approved_by=approval["approved_by"],
                approved_at=approval["approved_at"],
                approval_id=approval["approval_id"]
            )

            # Consume the exact approval only after
            # the remediation was successfully performed.
            if remediation_result.get("status") == "FIXED":

                consumption_result = (
                    consume_remediation_approval(
                        approval["approval_id"]
                    )
                )

        remediation_summary.append({
            "approval_id": approval["approval_id"],
            "customer": issue["customer"],
            "issue": issue["issue"],
            "severity": issue["severity"],
            "priority": issue["priority"],
            "recommended_action": issue["action"],
            "approval_required": True,
            "approval_status": approval["status"],
            "approval_reason": approval["reason"],
            "approved_replacement": approved_value,
            "approved_by": approval["approved_by"],
            "approved_at": approval["approved_at"],
            "remediation_result": remediation_result,
            "consumption_result": consumption_result
        })

    # ---------------------------------------------------------
    # Re-check the data after any approved remediation.
    # ---------------------------------------------------------
    verification_result = verify_customer_data_quality()

    for item in remediation_summary:

        if (
            item["remediation_result"] is not None
            and item["remediation_result"].get("status") == "FIXED"
        ):

            log_agent_action(
                action="VERIFY_REMEDIATION",
                approval_id=item["approval_id"],
                customer=item["customer"],
                old_value=item["remediation_result"]["old_revenue"],
                new_value=item["remediation_result"]["new_revenue"],
                approval_status="APPROVED",
                verification_status=(
                    verification_result["verification_status"]
                ),
                approved_by=item["approved_by"],
                approved_at=item["approved_at"]
            )

            update_audit_verification(
                RUN_ID,
                "FIX_NEGATIVE_REVENUE",
                verification_result["verification_status"]
            )

    # ---------------------------------------------------------
    # Determine final workflow status.
    # ---------------------------------------------------------
    final_status = determine_data_quality_status()

    log_agent_action(
        action="WORKFLOW_COMPLETED",
        customer="ALL",
        old_value=None,
        new_value=None,
        approval_status=None,
        verification_status=final_status["status"]
    )

    # ---------------------------------------------------------
    # Persist workflow/run history.
    # ---------------------------------------------------------
    update_last_run_state(
        quality_result=quality_result,
        verification_result=verification_result,
        final_status=final_status,
        remediation_summary=remediation_summary
    )

    # ---------------------------------------------------------
    # Persist customer-specific durable memory.
    # ---------------------------------------------------------
    memory = load_conversation_memory()

    context = memory["memory_context"]

    context.setdefault("customers", {})

    for item in remediation_summary:

        customer_name = item.get("customer")

        if not customer_name:
            continue

        customer_memory = context["customers"].setdefault(
            customer_name,
            {}
        )

        customer_memory["last_approval_id"] = (
            item.get("approval_id")
        )

        customer_memory["last_approval_status"] = (
            item.get("approval_status")
        )

        customer_memory["approved_by"] = (
            item.get("approved_by")
        )

        customer_memory["approved_at"] = (
            item.get("approved_at")
        )

        customer_memory["approved_replacement"] = (
            item.get("approved_replacement")
        )

        customer_memory["last_remediation"] = (
            item.get("remediation_result")
        )

        customer_memory["last_consumption"] = (
            item.get("consumption_result")
        )

        customer_memory["last_verification"] = {
            "status": verification_result[
                "verification_status"
            ],
            "remaining_issues": verification_result[
                "remaining_issues"
            ],
            "timestamp": datetime.now().isoformat()
        }

        # Update current revenue when remediation succeeded.
        remediation = item.get("remediation_result")

        if (
            isinstance(remediation, dict)
            and remediation.get("status") == "FIXED"
        ):
            customer_memory["current_revenue"] = (
                remediation.get("new_revenue")
            )

        customer_memory["last_updated"] = (
            datetime.now().isoformat()
        )

    memory["memory_context"] = context

    save_conversation_memory(memory)

    return {
        "quality_check": quality_result,
        "verification": verification_result,
        "final_status": final_status,
        "remediation_summary": remediation_summary
    }
def get_customer_memory(customer):
    memory = load_conversation_memory()

    customers = (
        memory
        .get("memory_context", {})
        .get("customers", {})
    )

    customer_memory = customers.get(customer)

    if customer_memory is None:
        return {
            "status": "NOT_FOUND",
            "customer": customer,
            "message": (
                f"No durable memory found for customer {customer}."
            )
        }

    return {
        "status": "OK",
        "customer": customer,
        "memory": customer_memory
    }
        
def find_relevant_memory(user_query):
    memory = load_conversation_memory()

    context = memory.get(
        "memory_context",
        {}
    )

    customers = context.get(
        "customers",
        {}
    )

    if not customers:
        return {
            "status": "NOT_FOUND",
            "reason": "No customer memory is available.",
            "customer": None,
            "memory": None
        }

    query = user_query.strip()

    if not query:
        return {
            "status": "NOT_FOUND",
            "reason": "No user query was provided.",
            "customer": None,
            "memory": None
        }

    # ---------------------------------------------------------
    # 1. Look for an explicitly named customer.
    # ---------------------------------------------------------
    for customer in sorted(
        customers.keys(),
        key=len,
        reverse=True
    ):
        pattern = r"\b" + re.escape(customer) + r"\b"

        if re.search(
            pattern,
            query,
            re.IGNORECASE
        ):
            return {
                "status": "OK",
                "match_type": "EXPLICIT_CUSTOMER",
                "customer": customer,
                "memory": customers[customer]
            }

    # ---------------------------------------------------------
    # 2. Fall back to the active customer.
    # ---------------------------------------------------------
        ambiguous_patterns = [
        r"\bother customer\b",
        r"\banother customer\b",
        r"\bother one\b",
        r"\banother one\b",
    ]

    if any(
        re.search(pattern, query, re.IGNORECASE)
        for pattern in ambiguous_patterns
    ):
        candidates = [
            customer
            for customer in customers.keys()
            if customer != context.get("active_customer")
        ]

        return {
            "status": "AMBIGUOUS",
            "match_type": "AMBIGUOUS_REFERENCE",
            "customer": None,
            "candidates": candidates,
            "reason": (
                "The user referred to another customer, "
                "but did not identify which customer."
            ),
            "memory": None
        }
    active_customer = context.get(
        "active_customer"
    )

    if (
        active_customer
        and active_customer in customers
    ):
        return {
            "status": "OK",
            "match_type": "ACTIVE_CUSTOMER",
            "customer": active_customer,
            "memory": customers[active_customer]
        }

    # ---------------------------------------------------------
    # 3. Search recent conversation messages.
    # ---------------------------------------------------------
    messages = memory.get(
        "messages",
        []
    )

    for message in reversed(messages[-10:]):

        content = message.get(
            "content",
            ""
        )

        for customer in sorted(
            customers.keys(),
            key=len,
            reverse=True
        ):
            pattern = r"\b" + re.escape(customer) + r"\b"

            if re.search(
                pattern,
                content,
                re.IGNORECASE
            ):
                return {
                    "status": "OK",
                    "match_type": "RECENT_CONVERSATION",
                    "customer": customer,
                    "memory": customers[customer]
                }

    return {
        "status": "NOT_FOUND",
        "reason": (
            "No relevant customer could be identified "
            "from persistent memory."
        ),
        "customer": None,
        "memory": None
    }

def log_agent_action(
    action,
    customer,
    old_value=None,
    new_value=None,
    approval_status=None,
    verification_status=None,
    approved_by=None,
    approved_at=None,
    approval_id=None
):
    audit_file = "day01/agent_audit.csv"

    expected_header = [
        "RunID",
        "Workflow",
        "Timestamp",
        "Action",
        "ApprovalID",
        "Customer",
        "OldValue",
        "NewValue",
        "ApprovalStatus",
        "VerificationStatus",
        "ApprovedBy",
        "ApprovedAt"
    ]

    file_exists = os.path.exists(audit_file)
    file_is_empty = (
        not file_exists
        or os.path.getsize(audit_file) == 0
    )

    # Create a new audit file if needed
    if file_is_empty:
        with open(audit_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(expected_header)

    else:
        # Read and migrate the existing audit file
        with open(audit_file, "r", newline="") as file:
            reader = csv.DictReader(file)
            existing_header = reader.fieldnames or []
            rows = list(reader)

        if existing_header != expected_header:
            for row in rows:
                row.setdefault("ApprovalID", "")
                row.setdefault("ApprovedBy", "")
                row.setdefault("ApprovedAt", "")

            with open(audit_file, "w", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=expected_header
                )
                writer.writeheader()
                writer.writerows(rows)

    # Write the new audit record
    with open(audit_file, "a", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            RUN_ID,
            WORKFLOW_NAME,
            datetime.now().isoformat(),
            action,
            approval_id,
            customer,
            old_value,
            new_value,
            approval_status,
            verification_status,
            approved_by,
            approved_at
        ])
def update_audit_verification(run_id, action, verification_status):
    audit_file = "day01/agent_audit.csv"
    rows = []
    updated = False

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames

        for row in reader:
            if (
                row["RunID"] == run_id
                and row["Action"] == action
                and not updated
            ):
                row["VerificationStatus"] = verification_status
                updated = True

            rows.append(row)

    if not updated:
        return {
            "status": "NOT_FOUND",
            "run_id": run_id,
            "action": action
        }

    with open(audit_file, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "UPDATED",
        "run_id": run_id,
        "action": action,
        "verification_status": verification_status
    }        
def get_audit_summary():
    audit_file = "day01/agent_audit.csv"
    unique_run_ids = set()
    total_records = 0
    action_counts = {}

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            total_records += 1
            if row["RunID"]:
                unique_run_ids.add(row["RunID"])

            action = row["Action"]
            action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_audit_records": total_records,
        "unique_agent_runs": len(unique_run_ids),
        "action_counts": action_counts
    }

def get_audit_run(run_id):
    audit_file = "day01/agent_audit.csv"
    records = []

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["RunID"] == run_id:
                records.append(row)

    if not records:
        return {
            "status": "RUN_NOT_FOUND",
            "run_id": run_id
        }

    return {
        "status": "RUN_FOUND",
        "run_id": run_id,
        "record_count": len(records),
        "records": records
    }
def get_latest_audit_run():
    audit_file = "day01/agent_audit.csv"

    runs = {}

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            run_id = row["RunID"]

            if not run_id:
                continue

            timestamp = datetime.fromisoformat(row["Timestamp"])

            if run_id not in runs:
                runs[run_id] = {
                    "latest_timestamp": timestamp,
                    "records": []
                }

            runs[run_id]["records"].append(row)

            if timestamp > runs[run_id]["latest_timestamp"]:
                runs[run_id]["latest_timestamp"] = timestamp

    if not runs:
        return {
            "status": "NO_RUNS_FOUND"
        }

    latest_run_id = max(
        runs,
        key=lambda run_id: runs[run_id]["latest_timestamp"]
    )

    latest_records = runs[latest_run_id]["records"]

    latest_records.sort(
        key=lambda row: datetime.fromisoformat(row["Timestamp"])
    )

    return {
        "status": "RUN_FOUND",
        "run_id": latest_run_id,
        "record_count": len(latest_records),
        "records": latest_records
    }    
def get_latest_remediation():
    latest_run = get_latest_audit_run()

    if latest_run.get("status") == "NO_RUNS_FOUND":
        return {
            "status": "NO_REMEDIATION_FOUND",
            "reason": "No agent runs were found."
        }

    remediation_records = []

    for row in latest_run["records"]:
        if (
            row["Action"] == "FIX_NEGATIVE_REVENUE"
            and row["VerificationStatus"] == "PASS"
        ):
            remediation_records.append(row)

    if not remediation_records:
        return {
            "status": "NO_REMEDIATION_FOUND",
            "run_id": latest_run["run_id"],
            "reason": "No successful remediation was recorded in the latest run."
        }

    remediation_records.sort(
        key=lambda row: datetime.fromisoformat(row["Timestamp"]),
        reverse=True
    )

    row = remediation_records[0]

    return {
        "status": "REMEDIATION_FOUND",
        "run_id": row["RunID"],
        "workflow": row["Workflow"],
        "timestamp": row["Timestamp"],
        "action": row["Action"],
        "customer": row["Customer"],
        "old_value": row["OldValue"],
        "new_value": row["NewValue"],
        "approval_status": row["ApprovalStatus"],
        "approved_by": row.get("ApprovedBy") or None,
        "approved_at": row.get("ApprovedAt") or None,
        "verification_status": row["VerificationStatus"]
    }
def get_run_summary(run_id):
    audit_file = "day01/agent_audit.csv"

    records = []

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["RunID"] == run_id:
                records.append(row)

    if not records:
        return {
            "status": "RUN_NOT_FOUND",
            "run_id": run_id
        }

    issues_detected = 0
    issues_remediated = 0
    failed_actions = 0
    verification_status = None
    run_status = None

    for row in records:
        action = row["Action"]

        if action == "FIX_NEGATIVE_REVENUE":
            issues_detected += 1

            if row["VerificationStatus"] == "PASS":
                issues_remediated += 1

        elif action == "FIX_NEGATIVE_REVENUE_FAILED":
            issues_detected += 1
            failed_actions += 1

        elif action == "VERIFY_REMEDIATION":
            verification_status = row["VerificationStatus"]

        elif action == "WORKFLOW_COMPLETED":
            run_status = row["VerificationStatus"]
            if verification_status is None:
               verification_status = row["VerificationStatus"]

    return {
        "status": "RUN_FOUND",
        "run_id": run_id,
        "workflow": records[0]["Workflow"],
        "issues_detected": issues_detected,
        "issues_remediated": issues_remediated,
        "failed_actions": failed_actions,
        "verification_status": verification_status,
        "run_status": run_status
    }           
def get_latest_run_summary():
    latest_run = get_latest_audit_run()

    if latest_run.get("status") == "NO_RUNS_FOUND":
        return {
            "status": "NO_RUNS_FOUND"
        }

    return get_run_summary(latest_run["run_id"])

def get_latest_operations_report():
    summary = get_latest_run_summary()

    if summary.get("status") == "NO_RUNS_FOUND":
        return {
            "status": "NO_RUNS_FOUND"
        }

    verification_status = summary["verification_status"]

    if verification_status is None:
        verification_status = "NOT_RECORDED"

    if summary["run_status"] == "PASS" and summary["failed_actions"] == 0:
        alert_status = "OK"
        attention_required = False
        alert_reason = (
            "Latest workflow completed successfully with no failed actions."
        )
    else:
        alert_status = "ATTENTION_REQUIRED"
        attention_required = True
        alert_reason = (
            f"Latest workflow requires attention: "
            f"{summary['failed_actions']} failed action(s), "
            f"verification status {verification_status}, "
            f"run status {summary['run_status']}."
        )

    return {
        "status": "OK",
        "run_id": summary["run_id"],
        "workflow": summary["workflow"],
        "issues_detected": summary["issues_detected"],
        "issues_remediated": summary["issues_remediated"],
        "failed_actions": summary["failed_actions"],
        "verification_status": verification_status,
        "run_status": summary["run_status"],
        "alert_status": alert_status,
        "attention_required": attention_required,
        "alert_reason": alert_reason
    }
def get_agent_alert_status():
    summary = get_latest_run_summary()

    if summary.get("status") == "NO_RUNS_FOUND":
        return {
            "status": "NO_RUNS_FOUND"
        }

    if summary["run_status"] == "PASS" and summary["failed_actions"] == 0:
        return {
            "status": "OK",
            "run_id": summary["run_id"],
            "message": "Latest data quality workflow completed successfully with no failed actions."
        }

    return {
        "status": "ATTENTION_REQUIRED",
        "run_id": summary["run_id"],
        "message": "The latest data quality workflow requires attention.",
        "failed_actions": summary["failed_actions"],
        "verification_status": summary["verification_status"],
        "run_status": summary["run_status"]
    }
def get_recent_run_history(limit=5):
    audit_file = "day01/agent_audit.csv"

    runs = {}

    with open(audit_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            run_id = row["RunID"]

            if not run_id:
                continue

            timestamp = datetime.fromisoformat(row["Timestamp"])

            if run_id not in runs:
                runs[run_id] = {
                    "latest_timestamp": timestamp,
                    "records": []
                }

            runs[run_id]["records"].append(row)

            if timestamp > runs[run_id]["latest_timestamp"]:
                runs[run_id]["latest_timestamp"] = timestamp

    sorted_runs = sorted(
        runs.items(),
        key=lambda item: item[1]["latest_timestamp"],
        reverse=True
    )

    history = []

    for run_id, run_data in sorted_runs[:limit]:
        records = run_data["records"]

        issues_detected = 0
        issues_remediated = 0
        failed_actions = 0
        verification_status = None
        run_status = None

        for row in records:
            action = row["Action"]

            if action == "FIX_NEGATIVE_REVENUE":
                issues_detected += 1

                if row["VerificationStatus"] == "PASS":
                    issues_remediated += 1

            elif action == "FIX_NEGATIVE_REVENUE_FAILED":
                issues_detected += 1
                failed_actions += 1

            elif action == "VERIFY_REMEDIATION":
                verification_status = row["VerificationStatus"]

            elif action == "WORKFLOW_COMPLETED":
                run_status = row["VerificationStatus"]

                if verification_status is None:
                    verification_status = run_status

        history.append({
            "run_id": run_id,
            "workflow": records[0]["Workflow"],
            "timestamp": run_data["latest_timestamp"].isoformat(),
            "issues_detected": issues_detected,
            "issues_remediated": issues_remediated,
            "failed_actions": failed_actions,
            "verification_status": verification_status,
            "run_status": run_status
        })

    return {
        "status": "OK",
        "run_count": len(history),
        "runs": history
    }
def get_run_health_metrics(limit=5):
    history = get_recent_run_history(limit)

    if history.get("status") != "OK":
        return {
            "status": history.get("status", "UNKNOWN")
        }

    runs = history["runs"]
    total_runs = len(runs)

    passed_runs = sum(
        1 for run in runs
        if run["run_status"] == "PASS"
    )

    failed_runs = sum(
        1 for run in runs
        if run["run_status"] == "FAIL"
    )

    pass_rate = (
        round((passed_runs / total_runs) * 100, 2)
        if total_runs > 0
        else 0
    )

    return {
        "status": "OK",
        "runs_analyzed": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "pass_rate_percent": pass_rate
    }
def get_run_health_status(limit=5, minimum_pass_rate=80):
    metrics = get_run_health_metrics(limit)

    if metrics.get("status") != "OK":
        return {
            "status": metrics.get("status", "UNKNOWN")
        }

    if metrics["pass_rate_percent"] >= minimum_pass_rate:
        health_status = "HEALTHY"
    else:
        health_status = "ATTENTION_REQUIRED"

    return {
        "status": "OK",
        "runs_analyzed": metrics["runs_analyzed"],
        "passed_runs": metrics["passed_runs"],
        "failed_runs": metrics["failed_runs"],
        "pass_rate_percent": metrics["pass_rate_percent"],
        "minimum_pass_rate_percent": minimum_pass_rate,
        "health_status": health_status
    }
def get_agent_monitoring_report():
    operations = get_latest_operations_report()
    health = get_run_health_status()

    if (
        operations.get("status") != "OK"
        or health.get("status") != "OK"
    ):
        return {
            "status": "MONITORING_DATA_UNAVAILABLE"
        }

    return {
        "status": "OK",

        "latest_run": {
            "run_id": operations["run_id"],
            "workflow": operations["workflow"],
            "issues_detected": operations["issues_detected"],
            "issues_remediated": operations["issues_remediated"],
            "failed_actions": operations["failed_actions"],
            "verification_status": operations["verification_status"],
            "run_status": operations["run_status"],
            "alert_status": operations["alert_status"],
            "attention_required": operations["attention_required"],
            "alert_reason": operations["alert_reason"]
        },

        "historical_health": {
            "runs_analyzed": health["runs_analyzed"],
            "passed_runs": health["passed_runs"],
            "failed_runs": health["failed_runs"],
            "pass_rate_percent": health["pass_rate_percent"],
            "minimum_pass_rate_percent": health["minimum_pass_rate_percent"],
            "health_status": health["health_status"]
        }
    }
def get_agent_health():
    health = get_agent_monitoring_report()
    remediation = get_latest_remediation()

    if health.get("status") != "OK":
        return {
            "status": "UNAVAILABLE"
        }

    latest = health["latest_run"]
    historical = health["historical_health"]

    return {
        "status": "OK",

        "latest_run_id": latest["run_id"],
        "latest_run_status": latest["run_status"],
        "latest_alert_status": latest["alert_status"],
        "attention_required": latest["attention_required"],

        "historical_health_status": historical["health_status"],
        "historical_pass_rate_percent": historical["pass_rate_percent"],
        "runs_analyzed": historical["runs_analyzed"],

        "latest_remediation": remediation
    }
def get_overall_agent_status():
    health = get_agent_health()

    if health.get("status") != "OK":
        return {
            "status": "UNAVAILABLE"
        }

    return {
        "status": "OK",
        "overall_status": (
            "HEALTHY"
            if (
                health["latest_run_status"] == "PASS"
                and health["latest_alert_status"] == "OK"
                and health["historical_health_status"] == "HEALTHY"
            )
            else "ATTENTION_REQUIRED"
        ),

        "latest_run_id": health["latest_run_id"],
        "latest_run_status": health["latest_run_status"],
        "latest_alert_status": health["latest_alert_status"],
        "attention_required": health["attention_required"],

        "historical_health_status": health["historical_health_status"],
        "historical_pass_rate_percent": health["historical_pass_rate_percent"],
        "runs_analyzed": health["runs_analyzed"],

        "latest_remediation": health["latest_remediation"]
    }
def update_conversation_summary():
    memory = load_conversation_memory()

    messages = memory.get("messages", [])

    if not messages:
        memory["summary"] = ""
        save_conversation_memory(memory)
        return memory

    recent_messages = messages[-10:]

    summary_parts = []

    for message in recent_messages:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            summary_parts.append(f"User: {content}")
        elif role == "assistant":
            summary_parts.append(f"Assistant: {content}")

    memory["summary"] = "\n".join(summary_parts)

    save_conversation_memory(memory)

    return memory
tools = [
    {
        "type": "function",
        "name": "get_sales_data",
        "description": "Get monthly sales data for January, February and March.",
    },
    {
    "type": "function",
    "name": "calculate_sales_metrics",
    "description": "Calculate total sales, highest sales month, highest sales value, and the percentage increase from January to March.",
    "parameters": {
        "type": "object",
        "properties": {
            "sales_data": {
                "type": "object",
                "description": "Monthly sales data with month names as keys and sales amounts as values."
            }
        },
        "required": ["sales_data"],
        "additionalProperties": False
    }
},
    {
    "type": "function",
    "name": "get_customer_data",
    "description": "Get revenue data for our customers."
},
 {
    "type": "function",
    "name": "check_customer_data_quality",
    "description": "Check customer data for missing revenue values and return a data quality status."
},
 {
    "type": "function",
    "name": "verify_customer_data_quality",
    "description": "MANDATORY verification step. After checking customer data quality, call this tool to independently re-check the data and confirm whether the identified issues still exist. Do not provide the final answer until this tool has been called"
},
 {
    "type": "function",
    "name": "fix_negative_revenue",
    "description": "Correct a customer's negative revenue using a validated replacement value. Never invent a replacement value.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "The customer whose negative revenue should be corrected."
            },
            "replacement_revenue": {
                "type": "integer",
                "description": "The validated replacement revenue value."
            }
        },
        "required": ["customer", "replacement_revenue"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "inspect_duplicate_customer",
    "description": "Inspect all records for a customer suspected of having duplicates. Do not modify or delete any data.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "The customer whose duplicate records should be inspected."
            }
        },
        "required": ["customer"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "remove_duplicate_customer",
    "description": "Remove one specific duplicate customer record identified by the exact customer name and exact revenue value. Only use this tool when the exact record has been explicitly approved for removal.",
"parameters": {
    "type": "object",
    "properties": {
        "record_id": {
            "type": "integer",
            "description": "Remove one specific record using its exact RecordID. Only use this tool when that RecordID has been explicitly approved for removal."
        }
    },
    "required": ["record_id"],
    "additionalProperties": False
}
},
 {
    "type": "function",
    "name": "determine_data_quality_status",
    "description": "Determine the data quality status using deterministic Python rules. Returns PASS when no issues exist and FAIL when one or more issues exist."
},
 {
    "type": "function",
    "name": "run_quality_workflow",
    "description": (
        "Run the customer data quality workflow in a controlled sequence. "
        "Approved remediation values are read from the authoritative approval registry."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "request_remediation_approval",
    "description": (
        "Create a pending remediation approval request. "
        "The tool never grants approval or performs remediation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "Customer requiring remediation approval."
            },
            "proposed_replacement": {
                "type": "integer",
                "description": "Proposed positive replacement revenue."
            },
            "reason": {
                "type": "string",
                "description": "Reason the remediation is being proposed."
            }
        },
        "required": [
            "customer",
            "proposed_replacement",
            "reason"
        ],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_audit_summary",
    "description": "Read the agent audit log and return the total number of audit records and counts by action.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},

 {
    "type": "function",
    "name": "get_run_summary",
    "description": "Return a concise business summary of a specific agent run, including issues detected, issues remediated, failed actions, verification status, and overall run status.",
    "parameters": {
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": "The exact Run ID to summarize."
            }
        },
        "required": ["run_id"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_latest_run_summary",
    "description": "Return a concise business summary of the most recent agent run.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_agent_alert_status",
    "description": "Determine whether the latest customer data quality workflow is OK or requires attention.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_latest_audit_run",
    "description": "Read the audit log and return all audit records belonging to the most recent agent run.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_latest_operations_report",
    "description": "Return one coherent operational snapshot for the latest CustomerDataQuality workflow run, including issues, remediation, verification, run status, and alert status.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_recent_run_history",
    "description": "Return the most recent customer data quality workflow runs, including issues, remediation, failures, verification, and overall status.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of recent runs to return.",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_run_health_metrics",
    "description": "Calculate deterministic health metrics for the most recent customer data quality workflow runs.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent runs to analyze.",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_agent_monitoring_report",
    "description": "Return a combined monitoring report containing the latest workflow status and recent historical health metrics.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_run_health_status",
    "description": "Determine the health status of recent customer data quality workflow runs using a configurable pass-rate threshold.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent runs to analyze.",
                "minimum": 1,
                "maximum": 20
            },
            "minimum_pass_rate": {
                "type": "number",
                "description": "Minimum required pass rate percentage for a HEALTHY status.",
                "minimum": 0,
                "maximum": 100
            }
        },
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_overall_agent_status",
    "description": "Return the deterministic overall health status of the data-quality agent using the latest run and recent historical health.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
{
    "type": "function",
    "name": "get_agent_health",
    "description": "Return a concise health status for the data-quality agent, including the latest run status, alert status, attention requirement, historical health, and pass rate.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_audit_run",
    "description": "Read the audit log and return all audit records for a specific Run ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": "The exact Run ID to retrieve."
            }
        },
        "required": ["run_id"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "fix_negative_revenue",
    "description": "Directly change a customer's negative revenue.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string"
            },
            "new_revenue": {
                "type": "number"
            }
        },
        "required": ["customer", "new_revenue"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_latest_remediation",
    "description": "Return the most recent successful remediation recorded in the latest agent run, including the customer, old and new values, approval details, and verification status.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_pending_approval_requests",
    "description": (
        "Return all pending remediation approval requests. "
        "This tool is read-only and cannot approve requests or perform remediation."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_agent_state",
    "description": (
        "Return the agent's persistent state from the previous "
        "completed workflow run. This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_run_history",
    "description": (
        "Return recent completed agent workflow runs from persistent state. "
        "This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent runs to return. Maximum 10."
            }
        },
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_customer_history",
    "description": (
        "Return recent historical audit events for a specific customer. "
        "This tool is read-only and includes approvals, remediation, "
        "verification, and workflow events."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "Customer name to retrieve history for."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of events to return."
            }
        },
        "required": ["customer"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_customer_state",
    "description": (
        "Return the current business state of a customer, including "
        "current revenue, latest approval, latest remediation, and "
        "latest verification. This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "Customer name."
            }
        },
        "required": ["customer"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_conversation_memory",
    "description": (
        "Return recent conversation messages stored in persistent memory. "
        "This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent messages to return."
            }
        },
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_memory_context",
    "description": (
        "Return the agent's compact persistent memory context, "
        "including the active customer, last topic, last tool, "
        "last approval ID, workflow status, and latest business snapshot. "
        "This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "get_customer_memory",
    "description": (
        "Return the persistent business memory stored for a specific "
        "customer, including the latest approval, remediation, "
        "consumption, verification, and current revenue. "
        "This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer": {
                "type": "string",
                "description": "Customer name."
            }
        },
        "required": ["customer"],
        "additionalProperties": False
    }
},
 {
    "type": "function",
    "name": "find_relevant_memory",
    "description": (
        "Find the most relevant customer memory for a user's question. "
        "It uses explicit customer names, the active customer, and recent "
        "conversation context. This tool is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "user_query": {
                "type": "string",
                "description": (
                    "The user's question or follow-up requiring "
                    "relevant customer memory."
                )
            }
        },
        "required": ["user_query"],
        "additionalProperties": False
    }
},
]

tool_functions = {
    "get_sales_data": get_sales_data,
    "calculate_sales_metrics": calculate_sales_metrics,
    "get_customer_data": get_customer_data_from_csv,
    "check_customer_data_quality": check_customer_data_quality,
    "verify_customer_data_quality": verify_customer_data_quality,
    "fix_negative_revenue": fix_negative_revenue,
    "inspect_duplicate_customer": inspect_duplicate_customer,
    "remove_duplicate_customer": remove_duplicate_customer,
    "determine_data_quality_status": determine_data_quality_status,
    "run_quality_workflow": run_quality_workflow,
    "request_remediation_approval": request_remediation_approval,
    "get_pending_approval_requests": get_pending_approval_requests,
    "get_audit_summary": get_audit_summary,
    "get_latest_audit_run": get_latest_audit_run,
    "get_audit_run": get_audit_run,
    "get_latest_remediation": get_latest_remediation,
    "get_run_summary": get_run_summary,
    "get_latest_run_summary": get_latest_run_summary,
    "get_agent_alert_status": get_agent_alert_status,
    "get_recent_run_history": get_recent_run_history,
    "get_run_health_metrics": get_run_health_metrics,
    "get_run_health_status": get_run_health_status,
    "get_agent_monitoring_report": get_agent_monitoring_report,
    "get_agent_health": get_agent_health,
    "get_overall_agent_status": get_overall_agent_status,
    "get_latest_operations_report": get_latest_operations_report,
    "get_agent_state": get_agent_state,
    "get_conversation_memory": get_conversation_memory,
    "get_customer_memory": get_customer_memory,
    "get_run_history": get_run_history,
    "get_customer_history": get_customer_history,
    "get_customer_state": get_customer_state,
    "get_memory_context": get_memory_context,
    "find_relevant_memory": find_relevant_memory,
    "update_audit_verification": update_audit_verification
    
}
# 2. Execute tools requested by the AI
def execute_tool(tool_call):

    APPROVAL_REQUEST_TOOLS = {
        "request_remediation_approval",
    }

    READ_ONLY_TOOLS = {
        "get_sales_data",
        "calculate_sales_metrics",
        "get_customer_data",
        "check_customer_data_quality",
        "verify_customer_data_quality",
        "inspect_duplicate_customer",
        "determine_data_quality_status",
        "get_audit_summary",
        "get_latest_audit_run",
        "get_audit_run",
        "get_latest_remediation",
        "get_pending_approval_requests",
        "get_run_summary",
        "get_latest_run_summary",
        "get_agent_alert_status",
        "get_latest_operations_report",
        "get_recent_run_history",
        "get_run_health_metrics",
        "get_run_health_status",
        "get_agent_monitoring_report",
        "get_agent_health",
        "get_overall_agent_status",
        "get_agent_state",
        "get_conversation_memory",
        "get_customer_memory",
        "get_run_history",
        "get_customer_history",
        "get_customer_state",
        "get_memory_context",
        "find_relevant_memory",
    }

    WRITE_TOOLS = {
        "fix_negative_revenue",
        "remove_duplicate_customer",
        "update_audit_verification",
        "run_quality_workflow",
    }

    ALLOWED_TOOLS = (
        READ_ONLY_TOOLS
        | WRITE_TOOLS
        | APPROVAL_REQUEST_TOOLS
    )

    tool_name = tool_call.name

    # Guardrail 1: tool must be explicitly allowed
    if tool_name not in ALLOWED_TOOLS:

        result = {
            "status": "TOOL_BLOCKED",
            "tool": tool_name,
            "message": f"Tool execution blocked: {tool_name}",
        }

        print("AI requested:", tool_name)
        print("Tool blocked:", result)

        return result

    # Guardrail 2: low-level write tools cannot be called directly
    if (
        tool_name in WRITE_TOOLS
        and tool_name != "run_quality_workflow"
    ):

        result = {
            "status": "WRITE_TOOL_BLOCKED",
            "tool": tool_name,
            "message": (
                f"Direct write tool execution blocked: {tool_name}. "
                "Use run_quality_workflow for controlled data changes."
            ),
        }

        print("AI requested:", tool_name)
        print("Write tool blocked:", result)

        return result

    # Only after all guardrails pass do we execute the tool
    tool_function = tool_functions[tool_name]

    arguments = (
        json.loads(tool_call.arguments)
        if tool_call.arguments
        else {}
    )

    result = tool_function(**arguments)

    MEMORY_READ_TOOLS = {
        "get_memory_context",
        "get_conversation_memory",
        "get_agent_state",
        "get_customer_memory",
        "find_relevant_memory",
    }

    # Memory lookup tools are read-only and must not change
    # the durable memory context.
    if tool_name not in MEMORY_READ_TOOLS:

        update_memory_context(
            tool_name=tool_name,
            tool_result=result
        )

    print("AI requested:", tool_name)
    print("Tool returned:", result)

    return result


# 3. Interactive multi-turn agent loop


if __name__ == "__main__":

    # 1. Load the conversation ID from conversation_memory.json
    session_state = load_agent_session()
    conversation_id = session_state.get("conversation_id")

    if conversation_id:
        print("Resuming saved conversation.")

    else:
        # Create a persistent OpenAI Conversation
        conversation = client.conversations.create()
        conversation_id = conversation.id

        # Save its ID immediately so it survives a restart
        save_agent_session(conversation_id)

        print("Created a new persistent conversation.")

    instructions = """
    You are a stateful data-quality business agent.

    ROUTING RULES

    1. Use tools before answering business-data questions.

    2. For current customer state, use get_customer_state.

    3. For customer history, use get_customer_history.

    4. For workflow history, use get_run_history.

    5. For previous agent state, use get_agent_state.

    6. When the user asks what is remembered about a named customer,
       use find_relevant_memory first.

    7. For indirect customer references, use find_relevant_memory first.

    8. Do not call get_conversation_memory merely to identify a customer.

    9. If find_relevant_memory returns AMBIGUOUS, do not guess.
       Ask the user which customer they mean.

    10. If the user supplies a customer name after a clarification,
        treat it as the intended customer and retrieve relevant data.

    11. Use get_customer_memory when durable customer memory is needed.

    12. Use get_conversation_memory when the user asks about
        the conversation itself.

    13. Do not call extra tools when an existing result is sufficient.

    14. Never claim a data change succeeded without tool evidence.
    """

    # 2. Continue accepting user messages until they exit
    while True:

        user_query = input("User: ").strip()

        if not user_query:
            print("No question provided.")
            continue

        if user_query.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        
        if user_query.lower() == "/help":

            print("\nAvailable commands:")
            print("  /help   - Show this command guide")
            print("  /status - Display session and memory status")
            print("  /new    - Start a new conversation")
            print("  exit    - Exit the agent")

            print("\nExamples:")
            print("  What do you remember about Globex?")
            print("  Was that remediation successful?")
            print("  What is the current state of Acme?")

            continue
        
        if user_query.lower() == "/new":

            conversation = client.conversations.create()
            conversation_id = conversation.id

            save_agent_session(conversation_id)

            print("Started a new conversation.")
            print("Customer memory and audit history are preserved.")

            continue
        
        if user_query.lower() == "/status":

            memory = load_conversation_memory()
            context = memory.get("memory_context", {})
            customers = context.get("customers", {})

            print("\nAgent status:")
            print(f"Conversation ID: {conversation_id}")
            print(
                "Active customer: "
                f"{context.get('active_customer') or 'None'}"
            )
            print(
                "Last topic: "
                f"{context.get('last_topic') or 'None'}"
            )
            print(
                "Customers in durable memory: "
                f"{', '.join(customers.keys()) or 'None'}"
            )
            print(
                "Stored customer count: "
                f"{len(customers)}"
            )

            continue

        add_conversation_message(
            role="user",
            content=user_query
        )

        update_memory_context(
            user_query=user_query
        )

        # 3. Submit the user's message to the saved conversation
        try:
            response = client.responses.create(
                model=MODEL,
                conversation=conversation_id,
                instructions=instructions,
                input=user_query,
                tools=tools,
            )

        except NotFoundError:
            print(
                "Saved conversation unavailable. "
                "Starting a new conversation."
            )

            conversation = client.conversations.create()
            conversation_id = conversation.id

            save_agent_session(conversation_id)

            # Retry the user's message once, using the new conversation.
            response = client.responses.create(
                model=MODEL,
                conversation=conversation_id,
                instructions=instructions,
                input=user_query,
                tools=tools,
            )

        # 4. Keep processing tool calls until the answer is ready
        while True:

            tool_outputs = []

            for item in response.output:

                if item.type == "function_call":

                    result = execute_tool(item)

                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": str(result),
                        }
                    )

            # No tool calls means the model has finished this turn
            if not tool_outputs:

                print("\nAI final answer:")
                print(response.output_text)

                add_conversation_message(
                    role="assistant",
                    content=response.output_text
                )

                # Persist the session ID and update timestamp
                save_agent_session(conversation_id)

                break

            # 5. Submit tool results to the same conversation
            response = client.responses.create(
                model=MODEL,
                conversation=conversation_id,
                instructions=instructions,
                input=tool_outputs,
                tools=tools,
            )