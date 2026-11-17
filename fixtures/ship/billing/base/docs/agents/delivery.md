---
point: delivery
mode: append
---
- Deliver: `make deliver VERSION=<version>` from the head of `main`, run by the person on call.
- Roll back: `make rollback VERSION=<previous version>`. A migration already played is not undone this way: it has its `.down.sql`, played by hand by the database owner.
- Approval: the product owner gives their go-ahead in the delivery channel before any delivery.
- No delivery on Friday after 3 pm.
