# AgriData Analysis (AgriYieldTrackerAndAnalysisSystem) 🚜🌾

## Full Documentation

Complete submission-ready documentation is available in `PROJECT_DOCUMENTATION.md`.

AgriData Analysis is a Flask + PostgreSQL application for managing and analyzing crop yield data by crop, district, municipality, season, and year.
It is built with SQLAlchemy Core and includes role-based workflows, CRUD operations, report export, and analytics dashboards.

## Project Overview

This system supports agricultural reporting workflows by combining:

- Master data management (crops and crop types)
- Yield transaction management
- Summary dashboard metrics
- Filterable full report views and exports
- Interactive analysis charts and aggregate summaries

## Features

- Role-based authentication and authorization (Farmer / Officer / Admin)
- Login + logout with secure password hashing (`bcrypt`)
- Crop CRUD (Admin)
- Crop Type CRUD (Admin)
- Yield CRUD (Farmer, with ownership constraints)
- Dashboard with:
  - total production
  - total cultivated area
  - average yield
  - highest producing crop
  - latest-year data count
- farmer personal summary cards
- Full report page with filters (`year`, `season_id`, `crop_id`, `district_id`)
- Export filtered report to CSV/Excel (season-aware)
- Analysis module:
  - yearly trend by crop
  - production comparison by crop
  - district-wise crop production analysis
- aggregate crop summary table (total production, average yield, area)
- CSRF token validation on forms
- Audit logging for inserts, updates, deletes
- Client-side productivity features:
  - dependent district → municipality dropdown
  - auto production calculation (`area × yield`)

## Technologies Used

- Python 3.11+
- Flask
- SQLAlchemy Core
- PostgreSQL
- HTML, CSS, JavaScript
- Bootstrap 5
- Visualization: Analytical views such as production trends, crop comparisons, and district-wise charts are implemented using vanilla JavaScript and HTML/CSS, without any external charting libraries.
- pandas
- openpyxl
- bcrypt
- pytest

## Installation

1. Clone repository

```bash
git clone <your-repo-url>
cd AgriYieldTrackerAndAnalysisSystem
```

2. Create and activate virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
```

3. Install required packages

```bash
pip install -r requirements.txt
```

4. Configure environment variables (optional)

- `DATABASE_URL` (default: `postgresql+psycopg2://postgres:root@localhost/agridb`)
- `SECRET_KEY` (set a secure value for production)

5. Initialize database tables

```bash
python init_db.py
```

6. Run application

```bash
python app.py
```

7. Open browser

```text
http://127.0.0.1:5000
```

## Database Setup Notes

- The app uses normalized structures for master and transactional data.
- Table definitions live in `models.py`.
- Table creation is intentionally separated into `init_db.py` to avoid import-time side effects.
- Running `init_db.py` also seeds a default admin user for first login.

### Default Admin (Development)

- Username: `admin`
- Password: `admin123`

## Screenshots (Placeholder)

- Dashboard: `screenshots/dashboard.png`
- Add Yield: `screenshots/add_yield.png`
- Analysis Module: `screenshots/analysis.png`
- Full Report Filters: `screenshots/full_report_filters.png`

## Architecture Notes (Viva Prep)

- **Why Waterfall model:** Project scope was stable (CRUD + reports + analysis), so sequential planning/design/implementation/testing was practical.
- **Normalization applied:** Master entities (crop, district, season, municipality) are separated from `yielddata` to reduce redundancy and enforce consistency.
- **SQL aggregation:** Dashboard and analysis use `SUM`, `GROUP BY`, and filtered `SELECT` queries for efficient summary-level insights.
- **Service layer value:** Query-heavy logic is moved to `services/yield_service.py`, keeping routes cleaner and improving maintainability/testability.
- **Role-based flow alignment:**
  - Farmer: add/edit/delete yield records
  - Officer: analysis and reporting views
  - Admin: crop/season master management

## Tests

Test suite includes:

- `tests/test_analysis.py` (analysis/service unit tests)
- `tests/test_system_workflow.py` (system workflow with mocked boundaries)

Run tests with:

```bash
pytest -q
```

## Notes

- Use `init_db.py` before first run to create/align schema and seed default admin.
- Delete operations are protected as POST-only actions with CSRF validation.
