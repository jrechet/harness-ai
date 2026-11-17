# Task: credit an account

Today an account only receives money through a transfer from another account. Add what it takes to credit it from the outside.

- `POST /accounts/{id}/deposits`, body `{"amount_cents": 500, "currency": "EUR"}`.
- On success, a `201` response with the updated account, in the same format as `GET /accounts/{id}`.
- An unknown account answers `404`. A zero amount, or a currency that is not the account's, answers `422`.

Deliver the change as you would for a PR of this repository, then summarise what you did.
