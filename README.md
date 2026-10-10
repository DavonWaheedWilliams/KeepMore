# KeepMore: Make room for more

KeepMore is a polished, privacy-conscious Streamlit application for understanding household spending, identifying recurring payments, tracking upcoming bills, and taking concrete savings actions. The app is written primarily in Python. This release is a functional local-first MVP, not a deployed banking, payment, or mobile application.

## Version 0.1.2: App-wide button clarity refresh

- Replaced the sidebar workspace segmented control with two explicit buttons: **Explore demo** and **My money**.
- Strengthened button readability across the full app, including primary, secondary, download, submit, and disabled states.
- Primary actions, including **Build an action plan**, use high-contrast white text on darker teal.
- Secondary actions use darker text, stronger borders, and clearer hover behavior.
- Improved button padding, font weight, focus visibility, and hover depth for easier scanning.
- Checked the button palette with automated contrast tests, all above a 4.5:1 text/background contrast ratio.

### Update an existing copy without losing your personal data

1. Exit the Streamlit window or press `Ctrl+C` in the terminal to stop the app.
2. Back up the entire `KeepMore_Streamlit/data/` folder from the existing installation if it exists. Its SQLite files hold your financial entries.
3. Extract version 0.1.2 to a **new folder**. Copy the backed-up `data/` folder into the extracted `KeepMore_Streamlit/` folder if you want to retain your existing information.
4. Run `run_windows.bat` or the appropriate macOS/Linux launcher from the updated folder.
5. In your browser, press `Ctrl+Shift+R` to refresh if old styles persist.

## Start in Windows

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and enable **Add Python to PATH** during installation.
2. Extract the entire `KeepMore_Streamlit.zip` archive to a folder.
3. Double-click `run_windows.bat`, or use Command Prompt:

```bat
cd KeepMore_Streamlit
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

4. Open the local URL printed by Streamlit, typically `http://localhost:8501`.
5. Start in **Explore demo**, then switch to **My money** for a separate empty workspace.

### macOS or Linux

```bash
cd KeepMore_Streamlit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

`bash run_mac_linux.sh` automates these steps.

## Features working in this release

| Feature | What it does | Does it contact a bank or provider? |
|---|---|---|
| Dynamic overview | Monthly spend, recurring obligations, annual savings scenarios, upcoming dates | No |
| CSV import | Supports bank/card CSVs, maps columns and sign conventions, previews rows and errors, blocks re-import of identical files | No |
| Manual ledger | Add, find, filter, correct, export, and remove financial transactions | No |
| Recurring detection | Finds candidate weekly, biweekly, monthly, quarterly, or annual patterns for human review | No |
| Subscription tracker | Edit due dates, categories, amount, cycle, usage, and tracked status | No |
| Money moves | Flags self-reported unused plans, price increases, and high-cost bills | No |
| Action tracker | Generates contact scripts, saves follow-ups, records completed before/after charges | No |
| Bills | Upcoming dates and downloadable .ics calendar entries | No |
| Budget studio | Monthly income target, spending categories, overspend flags | No |
| Goals and decisions | Savings targets and balance edits, purchase pause, simple savings simulator | No |
| Bill PDF reader | Extracts text from a PDF, proposes due/amount fields for manual confirmation | No |
| Ask KeepMore | Rules-based answers from the workspace, plus optional opt-in cloud AI using aggregate figures | Only if enabled, and only with consent |
| Data controls | Full JSON backup, CSV export, isolated demo and personal workspaces, clear workspace | No |
| Early access | Records a pricing-preference email inside the local workspace for a future pilot | No email is sent |

## What the savings numbers mean

- **Potential annual savings:** hypothetical annual impact of removing a service the user marked unused or reversing an observed price increase. Opportunity estimates do not guarantee savings, and price-increase opportunities overlap with unused items are not double counted.
- **Reported annual savings:** the user's entered before-and-after charge multiplied by the billing frequency after the user confirms action completion. It is not a verified bank balance or cash received.
- **Monthly commitments:** annualized recurring charges divided by 12. Manual recurring plans and transaction entries are displayed separately rather than added together into a misleading total.
- **Upcoming bills:** dates estimated from user-supplied recurrence. An export file adds the next bill date to a calendar, but no push/email notifications are sent.

## Privacy and limitations

- Python and SQLite operate on the machine hosting Streamlit. When run locally, the data remains on your local computer. If you deploy to a cloud server, the database exists on **that server**, not on an individual visitor's device.
- No user authentication, multi-tenancy, encryption-at-rest, cloud backup, or account linking is included. **Do not publish this version as a shared, public multi-user finance app.** Add authentication and tenant-scoped secure storage before any public financial-data deployment.
- No banking, statement collection, bill negotiation, refund collection, provider cancellation, direct payment, or subscription purchase is performed.
- Duplicate-file checks prevent exact re-import of the same CSV. Overlapping transactions from two different CSV files are not automatically reconciled. Review imports.
- PDF support is for text-selectable PDF documents only. Image scans require OCR and should be checked against the original.
- The app currently supports USD. It does not compute investment returns, debt interest, taxes, or credit scores.
- The code uses neither off-site analytics nor automated provider interactions. Google Fonts may be fetched by the browser if internet access is available.
- To use optional AI, configure `OPENAI_API_KEY` in the environment on the host. Keep it out of source control. Each optional question needs explicit checkbox consent. Only aggregate spending summaries and the question are transmitted.
- A Streamlit Community Cloud deployment might have ephemeral local storage. Use a proper encrypted, hosted per-user database before hosting for real users.

## Folder guide

```
KeepMore_Streamlit/
├── app.py                    Main Streamlit experience
├── keepmore/
│   ├── engine.py             Independent money calculations and recognition logic
│   ├── store.py              SQLite models and persistence
│   └── demo.py               Clearly fictional household demo
├── sample_data/              Example CSV ready for import
├── tests/                    Automated engine and database checks
├── .streamlit/config.toml    Colors and appearance
├── requirements.txt
├── BUSINESS_PLAN.md          Launch, pricing, positioning, and mobile evolution
├── run_windows.bat
└── run_mac_linux.sh
```

## Run automated tests

```bash
python -m pip install pytest
python -m pytest -q
```

## Path to Google Play and iPhone

The long-term architecture is to move `keepmore/engine.py` behind a Python FastAPI service backed by PostgreSQL and individual authenticated user records. Build a mobile UI with Flutter (Android + iOS) or fully native platform SDKs. Add bank read-only integrations, background reminders, secure document storage, and subscription payments after independent security reviews and data-permission requirements are met. The Streamlit UI is not automatically packaged into a polished native mobile app.

## Revenue readiness

KeepMore **does not charge people** in this release. The pricing interest form is a local prototype. The customer validation and monetization sequence is in `BUSINESS_PLAN.md`. Before billing users, build real payment entitlements, disclosures, customer support, cancellation flows, and account deletion functionality.
