
# AgriYieldTrackerAndAnalysisSystem 🚜🌾

![GitHub repo size](https://img.shields.io/github/repo-size/<your-username>/AgriYieldTrackerAndAnalysisSystem)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Flask](https://img.shields.io/badge/flask-2.3-green)
![PostgreSQL](https://img.shields.io/badge/postgresql-15-blue)

A **Flask & PostgreSQL-based system** to track crop yields across districts, municipalities, seasons, and years in Nepal.  
This system allows agricultural officers and data analysts to **add, edit, filter, and report crop yield data** efficiently.

---

## Features ✅

- Add, edit, and delete **crop yield records**
- Filter yields by **year, crop, district, and season**
- Manage **master data** for crops and crop types
- Auto-calculate **production** based on area harvested × yield per hectare
- Form validation for numeric fields and unique crop names
- Dependent dropdowns (District → Municipality) for user-friendly data entry
- Simple, clean dashboard to view all records

---

## Tech Stack 🛠️

- **Backend:** Python, Flask, SQLAlchemy  
- **Database:** PostgreSQL  
- **Frontend:** HTML, CSS, JavaScript (jQuery)  
- **Version Control:** Git & GitHub  

---

## Screenshots 📸

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Add Yield Form
![Add Yield](screenshots/add_yield.png)

### Edit Crop Form
![Edit Crop](screenshots/edit_crop.png)

> Replace these placeholder images with your actual screenshots inside a `/screenshots` folder.

---

## Installation 💻

1. **Clone the repository:**

```bash
git clone https://github.com/<your-username>/AgriYieldTrackerAndAnalysisSystem.git
cd AgriYieldTrackerAndAnalysisSystem
````

2. **Create a virtual environment:**

```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure PostgreSQL:**

* Update `config.py` or your database connection string with your credentials
* Ensure database and tables exist

5. **Run the Flask app:**

```bash
python run.py
```

6. **Open in browser:**

```
http://127.0.0.1:5000
```

---

## Folder Structure 📂

```
AgriYieldTrackerAndAnalysisSystem/
│
├── app/                  # Flask app: routes, models, templates
├── templates/            # HTML templates
├── static/               # CSS, JS, images
├── screenshots/          # Example screenshots
├── migrations/           # DB migrations (if using Flask-Migrate)
├── requirements.txt      # Python dependencies
├── config.py             # DB and app configuration
├── run.py                # Start Flask server
└── README.md             # This file
```

---

## Usage Example ⚡

### Filter Yields

* Go to **Dashboard → Filter**
* Select **Year**, **Crop**, **District**, **Season**
* Click **Apply** to see filtered results

### Add a New Crop

1. Navigate to **Master Data → Crops → Add Crop**
2. Enter **Crop Name** and select **Crop Type**
3. Click **Add Crop**

### Edit Crop/Yield

* Use **Edit** buttons on the list pages
* Update fields, save changes

---

## Contributing 🤝

1. Fork the repository
2. Create a branch: `git checkout -b feature-name`
3. Make your changes
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature-name`
6. Open a Pull Request

---

## License 📄

This project is **MIT licensed**. See the LICENSE file for details.

---
