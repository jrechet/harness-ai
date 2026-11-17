# Incident of 18 March 2024 — 4,312 confirmation e-mails in eleven minutes

## What happened
The backfill of the history of the old spreadsheet was started in production on a Monday at 10:05. The script read the file and saved each enrollment with `Enrollment.objects.create(...)`. On each save, the `post_save` signal of `Enrollment` sent the "Enrollment confirmed" e-mail. 4,312 e-mails left in eleven minutes, most of them to people enrolled in sessions that had ended since 2021.

## Consequences
- The SMTP provider suspended the account at 10:16 for an abnormal complaint rate. Suspension lifted after 36 hours.
- During those 36 hours, 214 real enrollments received no confirmation. The training department called each person back.
- About forty people phoned or showed up for a session that had taken place two years earlier.

## Cause
Sending was wired to `post_save`. A signal fires on every save, wherever it comes from: a view, the admin, a script, a data load. Nobody thought of the e-mail while writing the script, and nothing in the script showed it.

## Fixes
- The signal is removed. Sending is an explicit call in `enrollments/services.py`, after the commit (`transaction.on_commit`). The messages live in `enrollments/notifications.py`.
- Outside production, `EMAIL_BACKEND` is the console (`cursus/settings.py`).
- Decision: **a bulk job never sends one e-mail per row.** An import, a management command, an admin action save without notifying. If the people must be notified, the training department decides so and sends itself, in one go.

## What remains open
- Nothing prevents wiring a send back onto a signal or into `save()`: review is the only control.
- `services.enroll()` always sends its confirmation. The next bulk job will have to be able to enroll without sending. The backfill itself was replayed with the console backend.
