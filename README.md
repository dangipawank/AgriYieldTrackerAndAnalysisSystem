# AgriData Analysis (AgriYieldTrackerAndAnalysisSystem) 🚜🌾

This README is a complete handover guide for:

- Your project partner (even with zero prior context)
- Project presentation + demonstration
- Tomorrow's viva preparation

---

## 1) One-Minute Project Summary

AgriData Analysis is a Flask + PostgreSQL web system for managing and analyzing crop yield data by crop, district, municipality, season, and year.

It provides:

- Role-based login (Admin, Officer, Farmer)
- Master data management (crop, crop type, season)
- Yield entry/edit/delete with ownership checks
- Dashboard KPIs
- Full report filtering + CSV/Excel export
- Analysis charts and aggregate summaries

---

## 2) Tech Stack Used (Actual Project)

- Backend: Python, Flask
- Database: PostgreSQL
- Query/DB layer: SQLAlchemy Core
- Security: bcrypt, session auth, CSRF protection
- Frontend: HTML, CSS, Vanilla JavaScript
- Excel export: openpyxl
- Testing: pytest

---

## 3) Roles and Access

- Admin:
  - Manage users
  - Manage crops, crop types, seasons
  - View dashboard/report/analysis
- Officer:
  - View dashboard/report/analysis
- Farmer:
  - Add/edit/delete own yield records
  - View dashboard and full report (own data restrictions apply in routes)

Default seeded accounts (from `init_db.py`):

- admin / admin123
- officer / officer123
- farmer / farmer123

---

## 4) High-Level Module Map

- `app.py`
  - Flask app factory, blueprint registration, CSRF hook, error handlers
- `auth_routes.py`
  - Login/logout routes
- `routes.py`
  - Dashboard, yield CRUD, master CRUD, user CRUD, full report + export
- `analysis_routes.py`
  - Analysis page + JSON endpoints for charts/summary
- `models.py`
  - SQLAlchemy Core table definitions and engine
- `services/auth_service.py`
  - Password hashing/verification, user lookup
- `services/yield_service.py`
  - KPI and analysis query logic
- `services/audit_service.py`
  - Audit logging helper
- `utils/security.py`
  - CSRF utilities, login_required, role_required
- `init_db.py`
  - Schema init + default seed data
- `templates/`
  - UI pages
- `static/style.css`
  - Shared styling
- `tests/`
  - Unit/workflow tests

---

## 5) Database Design (Quick Understanding)

Core entities:

- Master tables: country, province, district, municipalitytype, municipality
- Domain masters: crop_type_master, crop_master, season_master
- Transactions: yielddata
- Auth: users
- Reporting view: vw_yield_full_report

Relationship idea:

- One crop type -> many crops
- One crop -> many yield records
- One district -> many municipalities
- One season -> many yield records
- One user (farmer) -> many created yield records

---

## 6) Complete Setup and Run Guide (Windows)

### Step A: Prerequisites

Install:

- Python 3.11+
- PostgreSQL
- Git

Create database in PostgreSQL (example):

- DB name: `agridb`
- Username/password should match connection string or env var

Default connection in code:

- `postgresql+psycopg2://postgres:root@localhost/agridb`

If yours is different, set env var `DATABASE_URL`.

### Step B: Clone and install

```bash
git clone <your-repo-url>
cd AgriYieldTrackerAndAnalysisSystem
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step C: Initialize DB schema and seed users

```bash
python init_db.py
```

### Step D: Run app

```bash
python app.py
```

Open:

- http://127.0.0.1:5000

### Step E: Run tests

```bash
pytest -q
```

---

## 7) If App Fails to Start (Fast Troubleshooting)

1. Verify PostgreSQL is running.
2. Verify DB exists (`agridb`).
3. Verify credentials in `DATABASE_URL`.
4. Confirm packages installed in active venv.
5. Check terminal traceback (most useful clue).
6. Port conflict fix (PowerShell):

```powershell
$conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
  $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $pids) { Stop-Process -Id $procId -Force }
}
```

7. Retry:

```bash
python app.py
```

---

## 8) Functional Walkthrough (for Partner Learning)

### A. Login

- Go to `/login`
- Login as admin first

### B. Admin flow

1. Manage crop types
2. Manage crops
3. Manage seasons
4. Manage users

### C. Farmer flow

1. Login as farmer
2. Add yield record
3. Edit same record
4. Delete record (optional)

### D. Report flow

1. Open full report
2. Apply filters: year/crop/district/season
3. Export CSV
4. Export Excel

### E. Analysis flow (Officer/Admin)

1. Open analysis page
2. Select crop for trend chart
3. Select district for comparison
4. Explain KPI cards and summary table

---

## 9) 5–7 Minute Presentation Flow (Ready Script)

Use this timing:

- 0:00–0:30 Opening + Introduction
- 0:30–1:00 Problem statement
- 1:00–1:40 Objectives + requirement analysis
- 1:40–2:30 Diagrams (Use case, ER, DFD)
- 2:30–4:30 Live demo (login -> add yield -> report -> analysis)
- 4:30–5:30 Tools, conclusion, future scope
- 5:30–6:00 Buffer for transitions

One-line narration template:

- "This system digitalizes crop yield recording and provides role-based analytics for better agricultural decisions."

---

## 10) Demo Checklist (Before Entering Viva Room)

- [ ] PostgreSQL running
- [ ] App starts without error
- [ ] Can login with admin
- [ ] Can open dashboard
- [ ] Can open add yield form
- [ ] Can open full report and export CSV
- [ ] Can open analysis page and see charts
- [ ] Internet not required for UI/CDN (already removed)

---

## 11) Viva Preparation (High-Probability Q&A)

### Q1. Why this project?

To solve manual, scattered agricultural yield records and support data-driven decision making.

### Q2. Why Flask?

Lightweight, easy to structure with blueprints, suitable for academic CRUD + analytics systems.

### Q3. Why PostgreSQL?

Reliable relational DB with strong query support for filtering, joins, and aggregation.

### Q4. Why role-based access?

Different stakeholders have different responsibilities and data privileges.

### Q5. Why bcrypt?

Plain-text password storage is unsafe; bcrypt provides secure hashing and verification.

### Q6. How CSRF is handled?

Token generated in session and validated on non-safe HTTP methods.

### Q7. How is dashboard KPI calculated?

Through SQL aggregate queries (`SUM`, `AVG`, `COUNT`) in service layer.

### Q8. Why service layer?

Keeps route handlers cleaner and centralizes query/business logic.

### Q9. How is data integrity maintained?

FK relations, validation checks, and controlled CRUD paths.

### Q10. One project limitation?

No advanced forecasting model yet; current analytics are descriptive.

### Q11. Future enhancement?

Add prediction/ML, GIS mapping, printable advanced reports, and API integration.

### Q12. How did you test?

`pytest` with analysis and workflow tests.

---

## 12) Feature-to-File Reference (Quick Viva Support)

- Authentication: `auth_routes.py`, `services/auth_service.py`, `utils/security.py`
- Dashboard + main operations: `routes.py`
- Analysis APIs and page: `analysis_routes.py`, `templates/analysis.html`, `services/yield_service.py`
- DB schema/tables: `models.py`
- DB init/seed: `init_db.py`
- Full report export: `routes.py` (`/yield/full_report/export/<format>`)

---

## 13) What to Show in Printed Report

Include detailed explanation of:

- Introduction and background
- Problem statement and objectives
- Requirement analysis (functional + non-functional)
- Use case diagram
- ER diagram
- DFD (context and level 1)
- Tools and technologies
- Implementation details (module-wise)
- Testing and results
- Conclusion and future enhancements

---

## 14) Common Mistakes to Avoid in Viva

- Don't say "we used AI only"; explain architecture and your logic.
- Don't skip security explanation (bcrypt + CSRF + roles).
- Don't jump to code before problem statement.
- Don't demo random pages; follow a clean flow.
- Don't ignore failure handling questions.
- Don't claim ML if not implemented.

---

## 15) Quick Commands Reference

Install deps:

```bash
pip install -r requirements.txt
```

Initialize DB:

```bash
python init_db.py
```

Run app:

```bash
python app.py
```

Run tests:

```bash
pytest -q
```

---

## 16) Final Handover Notes for Partner

If you have only 1 hour to prepare:

1. Read sections 1, 3, 4, 8, 11 of this README.
2. Run project once and perform demo checklist.
3. Memorize 12 viva Q&A in section 11.
4. Practice 5-minute flow in section 9.

If you have 15 more minutes:

- Read `routes.py` route names and know which role can access what.

---

## 17) Project Status

- Core modules implemented
- Tests passing (`pytest -q`)
- Ready for presentation/demo/viva with this guide

---
