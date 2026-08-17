# AI-Powered IT Helpdesk & Intelligent Ticket Resolution System

## 1. Overview

A full-stack IT helpdesk web application where employees raise IT support
tickets and L1 support agents triage, troubleshoot, resolve, or escalate
them — with an AI layer that assists agents by classifying tickets,
diagnosing likely causes, suggesting troubleshooting steps, and
recommending whether/where to escalate.

Built with Django + Django REST Framework, Bootstrap 5, and the OpenAI
API, structured so the AI layer is fully swappable and the app degrades
gracefully (no crashes, no fake data) whenever AI isn't configured or
unavailable.

## 2. Problem Statement

L1 support queues are full of repetitive, low-complexity tickets (WiFi,
DNS, printers, password resets) that eat up agent time before any
troubleshooting even starts. This system gives agents an instant
first-pass diagnosis and a consistent escalation policy, while giving
employees a simple, transparent way to track their tickets.

## 3. Features

- Employee ticket creation, tracking, and commenting
- L1 agent dashboard: assigned tickets, queue stats, charts by
  category/status/priority
- Admin dashboard + full Django Admin for user/agent/category/KB
  management
- Ticket comments (threaded, chronological)
- Ticket history / audit log (every important event is timestamped)
- Knowledge base with search
- Lightweight "similar tickets" search (text-similarity based, ready to
  be swapped for embeddings/vector search later)
- REST API for all core operations

## 4. AI Features

All AI logic lives in the `ai_engine/` package, called via `tickets/services.py`.

| Feature | Module | What it does |
|---|---|---|
| Ticket classification | `ai_engine/classifier.py` | Category, priority, issue type |
| Diagnosis | `ai_engine/diagnosis.py` | Problem summary, possible causes, troubleshooting steps, recommended resolution |
| Ticket summarization | `ai_engine/summarizer.py` | Summarizes ticket + comment thread for an agent |
| AI Support Assistant | `ai_engine/assistant.py` | Free-form Q&A page for agents (e.g. "How do I troubleshoot DNS on Windows?") |
| Escalation recommendation | `ai_engine/escalation.py` | Whether L1 can handle it, and which team to escalate to |

**AI safety:** the AI never claims to execute commands. It only
produces recommendations, explicitly flags destructive/risky steps as
needing human/admin confirmation, and every AI output notes it should
be verified by a human. If `OPENAI_API_KEY` is missing or the API call
fails for any reason (timeout, rate limit, invalid key, network error,
malformed response), the app shows a clear message and the rest of the
application keeps working normally — nothing fakes AI output.

## 5. User Roles

- **Employee** — create/view own tickets, comment, view AI analysis and resolution
- **L1 Support Agent** — view/manage all tickets, run AI analysis, assign, update status, resolve, escalate, use the AI Support Assistant
- **Admin** — everything above, plus Django Admin access to manage users, categories, and knowledge-base articles

## 6. Technology Stack

- **Backend:** Python 3, Django, Django REST Framework
- **Database:** SQLite by default (MySQL-ready via environment variables)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **AI:** OpenAI API (`openai` SDK), isolated in `ai_engine/`
- **Other:** python-dotenv for environment/secrets management

## 7. Architecture

```
Browser (Bootstrap 5 + Chart.js)
        │
        ▼
Django views (tickets/views.py)  ──────►  REST API (tickets/api_views.py)
        │                                          │
        ▼                                          ▼
tickets/services.py  (permissions, similarity search, AI orchestration)
        │
        ▼
ai_engine/  (classifier, diagnosis, summarizer, assistant, escalation)
        │
        ▼
OpenAI API  (key read from environment via .env, never hardcoded)
```

The AI layer never touches Django models directly — `services.py` is the
only bridge, which keeps `ai_engine/` provider-agnostic and testable in
isolation (see `tickets/tests.py::AIFailureHandlingTests`).

## 8. Database Overview

- `Profile` — extends Django's `User` with a `role` (Employee / L1 Agent / Admin)
- `Ticket` — the core ticket record, including all AI-generated fields
- `TicketComment` — threaded comments on a ticket
- `TicketHistory` — append-only audit log per ticket
- `KnowledgeBaseArticle` — searchable KB content
- `Category` — optional category management (Django Admin)

## 9. Installation

See **Section 12 (Running the Project on Windows / VS Code)** below for
the full step-by-step guide. Short version:

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then edit .env
python manage.py migrate
python manage.py load_demo_data
python manage.py runserver
```

## 10. Environment Variables

Copy `.env.example` to `.env` and fill in your own values. **Never commit `.env`.**

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | No (AI disabled without it) | Your OpenAI API key |
| `SECRET_KEY` | Recommended | Django secret key |
| `DEBUG` | No | `True` for local dev |
| `ALLOWED_HOSTS` | No | Comma-separated hosts |
| `AI_MODEL` | No | Defaults to `gpt-4o-mini` |
| `DB_ENGINE` | No | `sqlite` (default) or `mysql` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Only if `DB_ENGINE=mysql` | MySQL connection details |

## 11. Running the Project

```bash
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

## 12. Running on Windows / VS Code (step-by-step)

### Step 1 — Extract the project
Download `AI-Helpdesk.zip` and extract it anywhere, e.g. `C:\Projects\AI-Helpdesk`.

### Step 2 — Open in VS Code
Open the extracted `AI-Helpdesk` folder in VS Code (`File → Open Folder...`).

### Step 3 — Open a terminal
`Terminal → New Terminal` (make sure it's a Command Prompt or PowerShell terminal).

### Step 4 — Create a virtual environment
```bash
python -m venv venv
```

### Step 5 — Activate it
```bash
venv\Scripts\activate
```
Your terminal prompt should now start with `(venv)`.

### Step 6 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 7 — Create your `.env` file
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` in VS Code and add your own OpenAI key on this line:
```
OPENAI_API_KEY=MY_API_KEY
```
Replace `MY_API_KEY` with your actual key. **The app works fine without a key too** — it will just show "AI service is not configured" instead of AI results.

### Step 8 — Run migrations
```bash
python manage.py migrate
```

### Step 9 — Load demo data
```bash
python manage.py load_demo_data
```
This creates demo accounts, sample knowledge-base articles, and 12 sample tickets.

### Step 10 — (Optional) Create your own superuser
```bash
python manage.py createsuperuser
```

### Step 11 — Start the server
```bash
python manage.py runserver
```

### Step 12 — Open it in your browser
- App: <http://127.0.0.1:8000/>
- Django Admin: <http://127.0.0.1:8000/admin/>

### Step 13 — Try it out
1. Log in as `employee` / `employee12345`
2. Create a new ticket
3. Open the ticket to view its details
4. Log out, log back in as `agent` / `agent12345`
5. Open the same ticket and click **Analyze with AI** (requires an API key)
6. Review the AI diagnosis, troubleshooting steps, and escalation recommendation
7. Assign the ticket, add a comment, change its status
8. Resolve or escalate the ticket
9. Visit **AI Assistant** in the nav bar and ask a general troubleshooting question
10. Log in as `admin` / `admin12345` and open the Django Admin to manage users/categories/KB articles

## 13. Demo Credentials

**Development only — do not use these in production.**

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin12345` |
| L1 Agent | `agent` (also `agent2`) | `agent12345` |
| Employee | `employee` (also `employee2`) | `employee12345` |

## 14. API Endpoints

All endpoints require authentication (Django session auth) and enforce
the same role-based access rules as the web UI.

```
GET/POST   /api/tickets/
GET/PUT/PATCH/DELETE  /api/tickets/<id>/
GET/POST   /api/tickets/<id>/comments/
POST       /api/tickets/<id>/analyze/
GET        /api/tickets/<id>/summary/
POST       /api/tickets/<id>/escalate/
POST       /api/ai/assistant/
GET        /api/knowledge-base/
```


## 15. Future Improvements

- Replace difflib-based similar-ticket search with embeddings/vector search
- Add email notifications on ticket status changes
- Add SLA timers and breach alerts
- Add file attachments on tickets
- Add a dedicated React/Vue frontend consuming the REST API
- Add role-based ticket routing rules driven by AI category output

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Install Python from python.org and check "Add Python to PATH" during install, then restart the terminal. |
| `'pip' is not recognized` | Use `python -m pip install -r requirements.txt` instead. |
| `Django not installed` / `ModuleNotFoundError` | Make sure the venv is activated (`venv\Scripts\activate`) then re-run `pip install -r requirements.txt`. |
| `Port already in use` | Run `python manage.py runserver 8080` and open `http://127.0.0.1:8080/` instead. |
| Migration error | Delete `db.sqlite3` and any files in `tickets/migrations/` except `__init__.py`, then run `python manage.py makemigrations tickets` and `python manage.py migrate` again. |
| `TemplateDoesNotExist` | Confirm you're running `manage.py` from the project root (the folder containing `manage.py`), not from inside `tickets/`. |
| `NoReverseMatch` | Usually means a URL name changed — make sure you're on an unmodified copy of `tickets/urls.py`/`api_urls.py`, or check your edits for typos in `{% url %}` tags. |
| `CSRF error` on form submit | Make sure cookies are enabled and you're accessing the site via `127.0.0.1` (not a different host/port than what's in `ALLOWED_HOSTS`). |
| "AI service rejected the configured API key" | Double-check `OPENAI_API_KEY` in `.env` — no quotes, no extra spaces, and the key is active on your OpenAI account. |
| "AI service is not configured" | You haven't set `OPENAI_API_KEY` in `.env` yet — the rest of the app still works without it. |
| "Could not reach the AI service" | Check your internet connection; the OpenAI API requires outbound HTTPS access. |

---

**Security note:** the OpenAI API key is only ever read from the
environment (`os.getenv("OPENAI_API_KEY")` via `.env`). It is never
hardcoded, logged, stored in the database, or exposed via any API
response. `.env` is excluded from Git via `.gitignore` — only
`.env.example` (with empty values) is committed.
