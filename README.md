# ma_chorale

Django web application for managing church choral groups — member management, event scheduling, financial tracking, and activity logging.

---

## Features

- **Chorale management** — Create and configure chorales (name, type, location, logo, slogan)
- **Member management** — Invite members, assign roles (secretary, treasurer, censor), track absences and sanctions
- **Events calendar** — Schedule practices, meetings, and concerts with a monthly grid view
- **Financial tracking** — Contribution types, per-member payment tracking, cash flow entries
- **Meeting reports** — Attach reports to meetings
- **Commissions** — Manage internal working groups
- **Activity log** — Audit trail of all significant actions via `Event.log()`
- **Demo mode** — Isolated per-visitor demo session at `/demo/` with seed data, auto-cleaned after 2h

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 (ASGI via Channels) |
| Database | PostgreSQL |
| Cache / Broker | Redis (`django-redis`, Celery) |
| Task queue | Celery 5.6 |
| Email | SMTP (dev) / SendGrid (prod) |
| Static files | WhiteNoise with compression |
| Auth | Custom OTP email verification |
| Rate limiting | `django-ratelimit` |
| Containerization | Docker (multi-stage, non-root) |

---

## Project Structure

```
ma_chorale/
├── landing/            # Public pages (home, demo)
├── manage_users/       # Auth: register, OTP verify, login, password reset
├── manage_chorale/     # Core domain: chorale, members, events, contributions
├── notifications/      # Django Channels WebSocket consumers (minimal)
├── ma_chorale/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── prod.py
│   │   └── test.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── templates/
    ├── auth/
    ├── base/
    ├── components/
    ├── emails/
    ├── landing/
    └── pages/
```

### URL Structure

| Prefix | App |
|---|---|
| `/` | `landing` |
| `/u/` | `manage_users` (register, login, verify, reset) |
| `/a/<slug>/` | `manage_chorale` (dashboard, members, events, contributions) |
| `/demo/` | Demo session |

---

## Role System

**`CustomUser.role`** — Platform-level role:
- `member` — default
- `super_admin_chorale` — creator/admin of a chorale

**`Membership.role`** — Organizational role within a chorale:
- `member`, `secretary`, `treasurer`, `censor`, `admin`

All views under `/a/<slug>/` are gated by `ChoraleRequireMixin` (`manage_chorale/mixins.py`), which resolves the chorale from the URL slug and enforces membership/admin access.

---

## Key Models

| Model | Description |
|---|---|
| `Chorale` | Central entity — name, slug, admin, members (M2M via `Membership`) |
| `Membership` | Through model — links user to chorale with a role |
| `Contribution` | Contribution type (catalogue), e.g. "Monthly fee 2026" |
| `MemberContribution` | Payment record: which member paid which contribution |
| `CashFlow` | Income/expense entries for the chorale treasury |
| `ChoraleEvent` | Calendar event (practice, meeting, concert) |
| `Absence` | Member absence record for an event |
| `Sanction` | Disciplinary record |
| `Commission` | Internal working group |
| `MeetingReport` | Report attached to a meeting |
| `Event` | Audit log — use `Event.log(chorale, user, type, description)` |
| `CustomUser` | Extends `AbstractUser` — lowercase username/email, OTP verification |
| `OtpCode` | 5-digit OTP, 10-minute expiry |

---

## Setup

### Prerequisites

- Python 3.14+
- PostgreSQL
- Redis

### Local Development

```bash
# Clone and enter
git clone <repo>
cd ma_chorale

# Create virtualenv and install dependencies
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: DATABASE_URL, SECRET_KEY, REDIS_URL, EMAIL_*, SENDGRID_API_KEY

# Run migrations
python manage.py migrate --settings=ma_chorale.settings.dev

# (Optional) Load fake data
python manage.py loaddata fake_data.json --settings=ma_chorale.settings.dev

# Start dev server
python manage.py runserver --settings=ma_chorale.settings.dev
```

### Celery Worker (requires Redis)

```bash
celery -A ma_chorale worker -l info
```

### Static Files

```bash
python manage.py collectstatic --settings=ma_chorale.settings.dev
```

---

## Docker

```bash
docker build -t ma_chorale .
docker run -p 8000:8000 --env-file .env ma_chorale
```

Multi-stage build: `python:3.14-slim` builder → minimal runtime image. Runs as non-root user (`appuser`, UID 1000). Entrypoint at `entrypoint.sh`.

---

## Testing

```bash
# All tests
pytest

# Single file
pytest manage_chorale/tests/test_chorale_views.py

# Single test
pytest manage_chorale/tests/test_chorale_views.py::test_create_chorale_view_get_step1

# Rebuild test DB
pytest --no-reuse-db
```

Tests use `pytest-django` with `model-bakery` for fixtures. Settings: `ma_chorale.settings.test` (locmem email, `CELERY_TASK_ALWAYS_EAGER=True`).

Test files:
- `manage_chorale/tests/test_chorale_views.py`
- `manage_chorale/tests/test_chorale_forms.py`
- `manage_chorale/tests/test_treasurer_views.py`
- `manage_chorale/tests/test_censor_views.py`
- `manage_users/tests/test_views.py`
- `manage_users/tests/test_forms.py`

---

## Migrations

```bash
python manage.py makemigrations --settings=ma_chorale.settings.dev
python manage.py migrate --settings=ma_chorale.settings.dev
```

---

## Internationalization

Messages compiled with:
```bash
python manage.py compilemessages --settings=ma_chorale.settings.dev
```

Locale files in `locale/`.

---

## Service Layer

- `manage_chorale/services.py` — `get_dashboard_stats(chorale_id)` cached in Redis (60s TTL)
- `manage_chorale/contrats.py` — Abstract base classes for contribution domain (`IContribution`, `IMembreContribution`)
- `manage_chorale/manager.py` — Custom `EventManager` for the audit `Event` model

---

## Chorale Creation Wizard

`CreateChoraleView` uses `django-formtools` `SessionWizardView` (two steps: `create` → `conf`). On completion, the user's role is promoted to `super_admin_chorale`.

---

## License

Private — all rights reserved.