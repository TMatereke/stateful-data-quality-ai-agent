# Demo Walkthrough — Stateful Data-Quality AI Agent



## Objective



Demonstrate how a Python AI agent identifies a data-quality issue, requests human approval, applies an authorized correction, records the outcome, and verifies the result.



**Demo scenario:** Globex has revenue of -62,000. A reviewer approves replacing it with 62,000.



**Expected outcome:** Revenue becomes 62,000, the approval is consumed, and post-remediation verification returns PASS.



## 1. Prepare an isolated demo environment



Use a fresh clone, not your development folder containing your personal conversation history or local data.



```powershell

git clone https://github.com/TMatereke/stateful-data-quality-ai-agent.git C:\ai-agent-demo

cd C:\ai-agent-demo



python -m venv .venv

.\.venv\Scripts\Activate.ps1



python -m pip install -r requirements.txt

```



Initialize synthetic demo files. Run these commands only in this fresh clone:



```powershell

Copy-Item .\day01\customers.example.csv .\day01\customers.csv

Copy-Item .\day01\approval_registry.example.csv .\day01\approval_registry.csv

```



Configure credentials in the current PowerShell session:



```powershell

$env:OPENAI_API_KEY = "YOUR_API_KEY"



# Optional: set a model available to your API project.

$env:OPENAI_MODEL = "YOUR_AVAILABLE_MODEL_ID"

```



Replace the placeholders with your own values. Never commit credentials to the repository.



## 2. Establish the test baseline



Run:



```powershell

python .\day01\run_agent_tests.py

```



The expected baseline is 20 tests passed and zero failed. The runner also writes a local JSON test report.



## 3. Identify the data-quality problem



Start the agent:



```powershell

python .\day01\first_llm.py

```



Ask:



> Check the customer data quality. Which records need attention?



The synthetic dataset contains a negative revenue value for Globex. The agent should identify the issue rather than silently changing the record.



## 4. Request human approval



Ask:



> Request human approval to replace Globex's negative revenue with 62000. The reason is that the negative revenue value appears invalid.



The agent should create a pending approval request and return its approval ID. Record that ID for the next step.



Do not run the remediation workflow while the approval remains pending.



## 5. Approve the request



For this prototype, human approval is recorded locally. Exit the agent with `exit`, then run the following command from the repository root, replacing the placeholder with the actual approval ID returned in the previous step:



```powershell

python -c "import sys; sys.path.insert(0, r'.\day01'); import first_llm; print(first_llm.approve_remediation_request('PASTE_APPROVAL_ID', 'DemoReviewer'))"

```



Check that the result reports `APPROVED`. If it reports `REJECTED`, stop and investigate rather than attempting remediation.



This is a demonstration of a locally recorded reviewer decision, not authenticated production-grade identity verification.



## 6. Execute the controlled workflow



Restart the agent:



```powershell

python .\day01\first_llm.py

```



Ask:



> Run the customer data-quality workflow and report the remediation and verification results.



The expected sequence is:



1. The workflow detects Globex's negative revenue.

2. It retrieves the approved replacement.

3. The remediation function validates the approval details.

4. The revenue is changed to 62000.

5. The approval is marked CONSUMED.

6. The workflow checks data quality again and records the outcome.



The expected verification result is PASS, with no remaining issues in this synthetic dataset.



## 7. Inspect the evidence



Exit the agent, then run:



```powershell

Get-Content .\day01\customers.csv



Import-Csv .\day01\approval_registry.csv |

    Format-Table Customer, ReplacementRevenue, ApprovalStatus, ApprovedBy, ConsumedAt



python .\day01\run_agent_tests.py

```



Confirm that Globex's revenue is 62000, the approval status is CONSUMED, and the regression tests pass.



## What this demo demonstrates



* LLM tool calling and business-data retrieval

* Persistent customer memory and conversation continuity

* Explicit approval before remediation

* Validation of approval identity, timestamp, ID, amount, and status

* Single-use approval consumption

* Audit logging and post-change verification

* Automated regression and end-to-end workflow tests



## Prototype limitations



This project uses local CSV files and a locally supplied reviewer identity. The approval process is not backed by authenticated reviewer accounts, transactional storage, or a concurrency-safe approval service. The prototype is intended to demonstrate architecture and learning, not to authorize production financial changes.



For production use, add authenticated reviewer identities, transactional storage, stronger authorization, concurrency protection, monitoring, and appropriate security review.


## Example observed results

The following results were observed using the synthetic demo dataset.

| Measure                       | Result                                |
| ----------------------------- | ------------------------------------- |
| Initial Globex revenue        | -62,000                               |
| Initial data-quality score    | 80/100                                |
| Human approval                | Approved                              |
| Corrected Globex revenue      | 62,000                                |
| Approval lifecycle            | Consumed after successful remediation |
| Post-remediation verification | PASS                                  |
| Remaining data-quality issues | 0                                     |
| Automated regression tests    | 20 passed, 0 failed                   |

The audit trail recorded the approval request, reviewer decision, revenue correction, approval consumption, and remediation verification.

**Safety note:** The reviewer identity in this prototype is supplied locally and is not independently authenticated. The demonstration uses synthetic customer data and does not establish production-grade financial controls.
