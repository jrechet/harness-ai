# Operations

## Environments
| Name | Bus | Who deploys |
|---|---|---|
| local | in memory, or the broker of `docker-compose.yml` | everyone |
| preproduction | the platform team's cluster, virtual host `comptoir-preprod` | the platform's deployment pipeline |
| production | the platform team's cluster, virtual host `comptoir-prod` | the same, after approval |

Deployment does not live in this repository: the platform team builds the images from `main` and sets `BROKER_URL`.

## The broker
- Dedicated cluster, run by the platform team since March 2025. Before that, it was the hosting provider's shared plan.
- "At least once" delivery: see `docs/adr/0002-at-least-once-delivery.md`.
- The `comptoir_broker` client is built into the base image. Without `BROKER_URL`, a service starts on an in-memory bus.

## Who reads our events
| Event | In this repository | Elsewhere |
|---|---|---|
| `order.created` | `billing`, `notifications` | the accounting export (`comptoir-export`), the data warehouse |
| `invoice.issued` | `notifications` | the accounting export (`comptoir-export`) |

The outside consumers belong to other teams. Their tests do not run here.

## Deployment order
The services are deployed one by one, with no downtime. For a few minutes, a consumer receives events published by the old and by the new version of its provider.

## Replaying events
Only the platform team replays a queue, with its own tools. On 9 January 2026, a replay launched from a workstation, with the production `BROKER_URL` left in a terminal, published three days of `invoice.issued` again under new `id`s: 3,100 invoice emails re-sent to customers. Since then, nobody points a workstation at preproduction or production.
