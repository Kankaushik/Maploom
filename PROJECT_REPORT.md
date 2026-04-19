# MapLoom Flask — Project Report

**Date:** March 31, 2026  
**Type:** Full-Stack Web Application  
**Entry Point:** `app.py` (Flask package under `maploom_flask/`)

---

## 1. Project Overview

**MapLoom** is a web-based interactive map management portal. It allows administrators to create, edit, and version-control geographic maps (GeoJSON + custom image overlays), while regular users can view maps and submit location-tagged feedback. The application is branded as *"Where Maps Become Living Threads of Information."*

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | Flask 3.0.3 |
| ORM | SQLAlchemy 2.0.32 |
| Database | SQLite (default) / configurable via `DATABASE_URL` env var |
| Authentication | Flask `session` (server-side cookie) |
| Password Hashing | `passlib` — PBKDF2-SHA256 |
| HTML Sanitization | `bleach` 6.1.0 |
| CORS | `flask-cors` 4.0.1 |
| Data Validation | `pydantic` 2.8.2 |
| Environment Config | `python-dotenv` |
| Frontend Mapping | Leaflet.js 1.9.4 + Leaflet-Geoman 2.18.3 |
| Frontend Styling | Tailwind CSS (CDN), Bootstrap Icons |

---

## 3. Project Structure

```
maploom_flask/
├── __init__.py          # Empty package initializer
├── app.py               # Flask app factory + all routes
├── auth.py              # Session auth helpers + admin_required decorator
├── db.py                # SQLAlchemy engine, session factory, Base
├── models.py            # ORM models: User, Map, MapVersion, Feedback
├── sanitizer.py         # bleach-based HTML sanitizer
├── requirements.txt     # Python dependencies
└── static/
    ├── index.html       # Login page
    ├── admin.html       # Admin map editor UI
    └── user.html        # User map viewer UI
```

---

## 4. Database Models

### `User`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `username` | String(50) | Unique, not null |
| `password_hash` | String(255) | PBKDF2-SHA256 hashed |
| `role` | String(20) | `"admin"` or `"user"` |

**Methods:** `User.make(username, password, role)` — factory; `user.verify(password)` — boolean check.

### `Map`
| Column | Type | Notes |
|---|---|---|
| `name` | String(100) PK | Map identifier |
| `geojson` | Text | Serialized GeoJSON string |
| `areaData` | Text | Serialized area metadata JSON |
| `imgSrc` | Text | Base image source URL/data |
| `imgW`, `imgH` | Integer | Image dimensions |

**Relationship:** one-to-many with `MapVersion` (cascade delete).

### `MapVersion`
Snapshot table — auto-created before any overwrite of a `Map`.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `mapName` | String(100) FK → `maps.name` | Cascade delete |
| `geojson`, `areaData`, `imgSrc`, `imgW`, `imgH` | Same as Map | Snapshot copy |
| `savedAt` | DateTime | `datetime.utcnow` default |

### `Feedback`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `mapName` | String(100) | Optional, no FK constraint |
| `note` | Text | Sanitized HTML |
| `geojson` | Text | Optional GeoJSON annotation |
| `created` | DateTime | `datetime.utcnow` default |

---

## 5. API Endpoints

### Authentication
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/login` | Public | Accepts `{username, password}` JSON; sets session; returns `{success, role}` |

### Maps
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/maps/list` | Public | Returns list of all map names |
| GET | `/api/maps/<name>` | Public | Returns map GeoJSON, areaData, and image metadata |
| POST | `/api/maps/save` | Admin | Create or update a map; auto-snapshots current version before overwrite |
| DELETE | `/api/maps/<name>` | Admin | Deletes a map (cascade-deletes versions) |

### Versioning
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/maps/<name>/versions` | Admin | Lists all saved versions with timestamps |
| POST | `/api/maps/<name>/rollback` | Admin | Restores a snapshot by `{id}`; snapshots current state first |

### Feedback
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/feedback` | Public | Submit feedback with optional mapName and GeoJSON annotation; note is HTML-sanitized |
| GET | `/api/feedback/list` | Admin | List all feedback, optionally filtered by `?map=<name>` |
| DELETE | `/api/feedback/<id>` | Admin | Delete a feedback entry |

### Static / Frontend
| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves `index.html` (login page) |
| GET | `/static/*` | Serves static assets |

---

## 6. Authentication & Authorization

- **Mechanism:** Flask server-side sessions (cookie-based). The session key is loaded from the `FLASK_SECRET` environment variable (defaults to `"change-me-please"` — must be changed in production).
- **Roles:** Two roles — `admin` and `user`. Role is stored in the session on login.
- **`@admin_required` decorator:** Checks `session["role"] == "admin"`, returns HTTP 403 otherwise. Applied to all write/delete/version endpoints.
- **Password security:** PBKDF2-SHA256 via `passlib` — no plain-text storage.

---

## 7. Database Initialization

On startup, `bootstrap()` runs automatically:
1. Creates all tables via `Base.metadata.create_all()`.
2. Seeds three default users if `admin` does not yet exist:
   - `admin / admin123` (role: admin)
   - `user1 / user123` (role: user)
   - `user2 / user234` (role: user)

---

## 8. Frontend Pages

### `index.html` — Login Page
- Tailwind CSS + Bootstrap Icons styling.
- Username/password form with password visibility toggle.
- POSTs to `/api/login`; redirects to `admin.html` or `user.html` based on returned role.
- Background world-map SVG overlay with branding.

### `admin.html` — Admin Map Editor
- Full-screen Leaflet map with Leaflet-Geoman drawing tools.
- Top toolbar for map CRUD, version history, and publishing.
- Allows loading, editing, saving, and rolling back maps.

### `user.html` — User Map Viewer
- Read-only Leaflet map viewer.
- Allows browsing maps and submitting feedback with GeoJSON annotations.

---

## 9. Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///maps.db` | SQLAlchemy connection string |
| `FLASK_SECRET` | `"change-me-please"` | Flask session signing key |

Loaded via `.env` file using `python-dotenv`.

---

## 10. Security Notes

| # | Issue | Severity | Detail |
|---|---|---|---|
| 1 | Weak default secret key | **High** | `FLASK_SECRET` defaults to `"change-me-please"`. Must be overridden via `.env` in all deployments. |
| 2 | Hardcoded seed credentials | **Medium** | Default `admin/admin123` credentials are seeded at startup. Change immediately after first run. |
| 3 | CORS wildcard on API | **Low** | `r"/api/*"` open to all origins (`"*"`). Scope to known frontend domain in production. |
| 4 | No rate limiting on `/api/login` | **Medium** | Brute force attacks are not throttled. Add `flask-limiter` for production. |
| 5 | `mapName` in Feedback has no FK | **Info** | References map names without a database foreign key — orphan feedback possible after map deletion. |
| 6 | HTML sanitization applied | **Good** | Feedback notes are sanitized via `bleach` before storage, preventing stored XSS. |
| 7 | Password hashing applied | **Good** | PBKDF2-SHA256 used — no plain-text passwords stored. |

---

## 11. Key Design Patterns

- **Package layout:** The app lives in a Python package (`maploom_flask/`) with a `create_app()` factory function in `app.py`, suitable for WSGI deployment (Gunicorn, uWSGI).
- **Version snapshotting:** Every `save_map` and `rollback` operation automatically creates a `MapVersion` snapshot of the current state before any overwrite — providing a full audit trail.
- **Session-per-request:** Uses a `with Session(engine) as db:` context manager per request — clean, no session leaks.
- **Static SPA hosting:** Flask serves all three HTML pages directly from the `/static` folder, keeping the frontend and backend in a single deployable unit.

---

## 12. Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
FLASK_SECRET=your-strong-secret-key
DATABASE_URL=sqlite:///maps.db   # or a PostgreSQL URL

# Run development server
python -m flask --app maploom_flask.app run --port 3000

# Or directly
python maploom_flask/app.py
```

---

*Report generated from source code analysis of the `maploom_flask` workspace.*
