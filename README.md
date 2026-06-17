# Qualihome: Client Pre-Qualification System

> A web-based management and tracking system for a local real estate firm, using the Similarity-Augmented C5.0 Algorithm to pre-qualify clients based on structured data inputs.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

---

## Overview

Qualihome serves as a centralized hub for managing client pre-qualification data for a real estate firm. The system uses the Similarity-Augmented C5.0 Algorithm to evaluate and classify client eligibility, while maintaining secure role-based access for administrators, agents, and clients to ensure accurate tracking, status updates, and reporting.

---

## Key Features

- **Similarity-Augmented C5.0 Classification** — Machine learning engine that pre-qualifies clients based on structured data inputs and similarity scoring.
- **Role-Based Access Control** — Secure authentication distinguishing between admin, agent, and client user levels to protect sensitive data.
- **Client Portal** — Specialized interface for clients to track their pre-qualification status.
- **Agent Portal** — Dedicated interface for agents to manage client records and tasks.
- **Administrative Dashboard** — Monitors system performance, user activity, and report generation.
- **Geographic Data Standardization** — Uses PSGC (Philippine Standard Geographic Code) integration for standardized location data.

---

## Technical Implementation

| Layer | Technology |
|---|---|
| Backend | Python (Flask) |
| ML Engine | Similarity-Augmented C5.0 Algorithm (`c50_engine.py`) |
| Database | MySQL |
| Frontend | HTML5, CSS3, JavaScript |
| Geographic Data | PSGC (`psgc.py`) |

### Architecture

- `app/auth/` — User login, registration, and session management.
- `app/client/` — Client-side operations, pre-qualification tracking, and status updates.
- `app/main/` — Core application routes and utility scripts including geographic data processing.
- `app/ml/` — Machine learning integration including the C5.0 classification engine.
- `app/static/css/` — Separate dashboard stylesheets for admin, agent, and client views.
- `app/static/img/` — Visual assets including award badges and icons.

---

## Project Structure

```
/
├── app/
│   ├── auth/              # Authentication routes and forms
│   ├── client/            # Client management routes and forms
│   ├── main/              # Core routes, utilities, and psgc.py
│   ├── ml/                # C5.0 ML engine and classification logic
│   └── static/
│       ├── css/           # Admin, agent, and client dashboard styles
│       └── img/           # Icons, badges, and visual assets
└── app/config.py          # Environment and database configuration
```

---

## How to Get Started

1. **Dependencies** — Set up a Python environment and install required packages via `pip install -r requirements.txt`.
2. **Configuration** — Update `app/config.py` with your local database credentials and environment variables.
3. **Database Initialization** — Initialize the database schema to support authentication, client data, and ML logging modules.
4. **Run** — Start the Flask development server by executing the application entry point.

---

## Credits

Developed by **Juan Carlos Garcia** as a commissioned system for a local real estate firm.
