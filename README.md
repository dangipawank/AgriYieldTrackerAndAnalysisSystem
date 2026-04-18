# Agri-Yield Tracker & Analysis System

A Flask-based web application for agricultural yield tracking, analysis, reporting, and role-based management.

## Features
- Role-based authentication (`Admin`, `Officer`, `Farmer`)
- Yield data CRUD with ownership controls
- Master data management (crops, crop types, seasons)
- Analytics dashboard with live chart data
- Full yield reporting with CSV/Excel export
- CSRF protection and audit logging

## Tech Stack
- Python, Flask
- SQLAlchemy
- PostgreSQL (`psycopg2`)
- Tailwind CSS + Jinja templates
- Pytest

## Project Structure
- `app.py` - Flask app factory/bootstrap
- `routes.py` - Main application routes
- `auth_routes.py` - Authentication routes
- `analysis_routes.py` - Analysis endpoints/pages
- `services/` - Business logic and auth/yield/audit services
- `templates/` - Jinja HTML templates
- `static/` - CSS assets
- `tests/` - Test suite

## Setup
1. Create virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate virtual environment:
   - Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure database env (optional):
   - `DATABASE_URL`
   - `SECRET_KEY`
5. Initialize database:
   ```bash
   python init_db.py
   ```
6. Run app:
   ```bash
   python app.py
   ```
7. Open:
   - `http://127.0.0.1:5000/login`

## Default Accounts (after `init_db.py`)
- `admin / admin123`
- `officer / officer123`
- `farmer / farmer123`

## Tests
```bash
python -m pytest -q
```

## Notes
- This repository is prepared for GitHub push with a single root documentation file (`README.md`).
- Local environment/log/cache artifacts are excluded via `.gitignore`.
