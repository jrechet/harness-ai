# ADR 0001 — Business logic lives in the services

Date: 2023-11-20. Status: accepted.

## Context
A Django application offers four places to put a rule: the view, the form, the model (`save()`, signals), the template. Without a decision, all four end up carrying a piece of it.

## Decision
- A business rule (seats, waiting list, cancellation) is written once, in the `services.py` of its application.
- A view reads the request, calls a service, picks the response. An admin action does the same.
- A model describes data and its table constraints. No rule in `save()`.
- A template displays what the view gives it.

## Verification
None. It is a review convention. No incident is due to it so far.
