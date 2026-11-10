import type { Status } from "@deskly/shared";

// Typed on Status since June 2026: a status added to @deskly/shared without a
// label here is now a compile error instead of "undefined" on screen.
const LABELS: Record<Status, string> = {
  open: "Ouvert",
  in_progress: "En cours",
  waiting: "En attente du client",
  resolved: "Résolu",
  closed: "Fermé",
};

export function statusLabel(status: Status): string {
  return LABELS[status];
}
