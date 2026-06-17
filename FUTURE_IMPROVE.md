# FUTURE_IMPROVE.md

Potential improvements found while analyzing the codebase (2026-06-17). Grouped by priority. Each item: **what**, **where**, **why**.

---

## 🔴 Security / correctness (do first)

### 1. Hardcoded default password for new members
**Where:** `manage_chorale/views.py` → `MemberPopupView.post` — `password="defaultpassword123"`.
**Why:** Every member added by an admin/secretary gets the **same known password**. Anyone aware of it can log in as any newly-added member. Replace with: create the user with an unusable password (`set_unusable_password()`), then send an OTP-verified set-password / invite link (reuse the existing `send_link_to_user` / password-reset flow). Also makes the account's email actually owned by the member.

### 2. `MemberPopupView.post` has no response on invalid form
**Where:** `manage_chorale/views.py` → `MemberPopupView.post`.
**Why:** When `form.is_valid()` is `False`, the method falls through and returns `None` → Django raises `ValueError: ... didn't return an HttpResponse`. The invalid-form branch must re-render the template with the bound form (like the other create views).

### 3. Enable RLS on Supabase + audit the anon key
**Where:** Supabase project (infra, not repo).
**Why:** Django connects as the `postgres` role (has `BYPASSRLS`), so enabling RLS won't break the app — it's pure hardening against any anon/`authenticated` key or the PostgREST API surface. Enable RLS on every `public` table (`ENABLE`, not `FORCE`); default-deny is fine if nothing uses the anon key. Confirm no frontend/mobile client uses the anon key before relying on deny-by-default.

### 4. Verify auth endpoints are rate-limited
**Where:** `manage_users/views.py` (login, register, OTP verify, password reset).
**Why:** `RateLimitedMixin` is applied across `manage_chorale` but auth endpoints are the highest-value brute-force / enumeration targets. Confirm login, OTP submit, and reset-request have per-IP limits; add them if missing.

### 5. Broad `except Exception` swallows errors in chorale creation
**Where:** `manage_chorale/views.py` → `CreateChoraleView.done`.
**Why:** A bare `except Exception` catches everything and shows a generic message, hiding real failures (and there's no DB transaction wrapping the multi-row create). Wrap the `Chorale` + `Membership` creation in `transaction.atomic()` and let unexpected errors surface to logging/monitoring instead of being silently swallowed.

---

## 🟠 Code hygiene

### 6. Remove `print()` debug statements
**Where:** `views.py` (`print(data)` — logs member PII; `print(f"Erreur ...")`), `notifications/consumers.py` (`[WS] connect/disconnect`), `manage_users/tasks.py` (`print("Email sent ...")`).
**Why:** `print` leaks data to stdout, isn't level-filtered, and clutters prod logs. Replace with the `logging` module at appropriate levels.

### 7. Drop the `fake_data.json` dashboard fallback
**Where:** `views.py` → `load_recent_activities` + `DashboardView` (`recent_activities = recent_events if recent_events else load_recent_activities()`).
**Why:** A brand-new chorale with no activity shows **fabricated** recent events, which is misleading in production. Show an empty state instead.

### 8. Remove legacy / stray test & report files
**Where:** `manage_chorale/tests.py` (3-line stub) and `landing/tests.py` next to the real `tests/` packages; `test_channel.py` at repo root; committed `test_reports/test_report_*.html`.
**Why:** `pytest.ini` matches `tests.py` too, so stubs get collected; stray files confuse the test layout. Delete or fold into the proper package; add `test_reports/` to `.gitignore`.

### 9. Retire the legacy `CustomUser` role constants
**Where:** `manage_users/models.py` (`ROLE_*`, `CHORALE_ROLE_*` aliases).
**Why:** They exist only "the time of the refactor." Now that `Membership` is the source of truth, grep for remaining usages and remove the aliases to prevent anyone reading role state off the user again.

### 10. Clean up the WebSocket echo leftover
**Where:** `notifications/consumers.py` → `receive`.
**Why:** The consumer still echoes any received message — a tunnel test. Remove or guard it so the production WS endpoint doesn't reflect arbitrary client input.

---

## 🟡 Features / completeness

### 11. `MeetingReport` and `Commission` have models but no UI
**Where:** `manage_chorale/models.py`.
**Why:** Both are defined (and `MeetingReport` is referenced in docs as "PV de réunion") but have no forms, views, URLs, or templates. Either build the CRUD (likely secretary-scoped) or remove the dead models until needed.

### 12. Dashboard deltas are hardcoded to 0
**Where:** `views.py` → `DashboardView` (`increase_members = increase_balance = increase_sanctions = 0`, with a TODO).
**Why:** The "+X since last period" indicators always show 0. Implement periodic snapshots (e.g. a Celery beat task writing monthly aggregates) to compute real deltas.

### 13. Location parsing in chorale creation is fragile
**Where:** `views.py` → `CreateChoraleView.done` (splits `location` on `,`, defaults country to `'France'`).
**Why:** The default `'France'` contradicts the XAF/Central-Africa domain, and naive comma-splitting mismangles many inputs. Add dedicated `city`/`country` fields to the wizard form.

### 14. `notify_chorale` pushes one member's notification id to the whole group
**Where:** `notifications/services.py` → `notify_chorale` (sends `_serialize(notifs[0])` to the chorale group).
**Why:** Every connected member receives the same payload carrying the *first* member's notification id; per-user read state / dedup by id can get confused. Consider pushing a content-only announcement (no per-row id) to the group, and let each client reconcile via the REST `list` endpoint.

### 15. International phone validator vs `max_length=15`
**Where:** `manage_users/models.py` → `Profile._contact` (`max_length=15`, validator allows spaces).
**Why:** `+237 77 123 45 67` with spaces exceeds 15 chars and fails to save. Either normalize (strip spaces before save) or widen the field.

---

## 🟢 Ops / CI (from the deployment debugging session)

### 16. SSH forced-command / shell hook on the VPS auto-runs `deploy.sh`
**Where:** VPS — check `~/.ssh/authorized_keys` for a `command="..."` prefix, `sshd_config` `ForceCommand`, and shell rc files (`~/.bashrc`, `~/.profile`, `/etc/profile.d/`).
**Why:** A connection-time hook ran `deploy.sh` on *every* ssh/scp (even `mkdir`), with no `TAG`, causing the recurring `TAG non defini` exit 1 and the phantom double-deploy. Remove the hook so only the workflow's deploy step invokes the script.

### 17. Reconcile the deployed `deploy.sh` with the repo version
**Where:** `deployment/deploy.sh` vs whatever is on the VPS.
**Why:** Logs showed an older emoji/relative-`cd` script running while the repo had the `TAG`-guarded, `-f compose.prod.yml` version. The scp step overwrites the VPS copy each run, so make sure the repo version is canonical and delete any hand-edited copy on the box.

### 18. Narrow the deploy triggers
**Where:** `.github/workflows/deploy.yml` (`on.push.branches` + `tags`).
**Why:** Pushing a commit on `main` together with a `v*.*.*` tag fires two workflow runs → two deploys. The new `concurrency` block now queues them safely; if tag-based releases aren't used, drop the tag trigger entirely to avoid the redundant run.

### 19. Per-`$TAG` rollback marker
**Where:** `deployment/deploy.sh` (`.deploy_previous_image`).
**Why:** Shared mutable file on the VPS. Safe now that deploys are serialized, but storing it per-tag (`.deploy_previous_image.$TAG`) removes the last bit of shared-state risk.

---

## 🔵 Nice-to-have

- **Currency i18n:** "XAF" is hardcoded into many user-facing strings (services, views). Centralize formatting / make it configurable per chorale.
- **`gunicorn` vs ASGI:** `gunicorn` is in `requirements.txt` but the app is ASGI (Channels). Confirm prod serves via daphne/uvicorn workers, and drop `gunicorn` if unused.
- **Test coverage gaps:** add tests for `MemberPopupView` (especially the invalid-form path and member-creation flow), the notifications service/consumer, and `SanctionService.lift`.
- **`SECRET_KEY` duplication:** `prod.py` re-declares `SECRET_KEY = config('SECRET_KEY')` already set in `base.py` — harmless but redundant.
</content>
