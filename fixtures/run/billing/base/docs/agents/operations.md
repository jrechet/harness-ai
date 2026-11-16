---
point: operations
mode: append
---
- API logs: `make logs SERVICE=<service>`, read-only.
- Deployment history: `make deployments`, read-only.
- Mitigate: `make rollback VERSION=<previous version>`, decided and run by the on-call person.
- Billing data is never corrected by hand in the database: any correction goes through a ticket.
