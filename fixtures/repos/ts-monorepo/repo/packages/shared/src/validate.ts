import { PRIORITIES } from "./ticket.ts";
import type { Priority } from "./ticket.ts";

export interface NewTicket {
  title: string;
  requester: string;
  priority: Priority;
}

export type Result<T> = { ok: true; value: T } | { ok: false; errors: string[] };

const MAX_TITLE = 120;

// parseNewTicket is the one validation of a ticket creation: the API applies it
// to the request body, the web form applies it before sending.
export function parseNewTicket(input: unknown): Result<NewTicket> {
  const errors: string[] = [];
  const body = (typeof input === "object" && input !== null ? input : {}) as Record<string, unknown>;
  const title = typeof body.title === "string" ? body.title.trim() : "";
  const requester = typeof body.requester === "string" ? body.requester.trim() : "";
  const priority = body.priority ?? "normal";
  if (title === "") errors.push("title is required");
  if (title.length > MAX_TITLE) errors.push(`title is longer than ${MAX_TITLE} characters`);
  if (!/^[^@\s]+@[^@\s]+$/.test(requester)) errors.push("requester must be an email address");
  if (!(PRIORITIES as readonly unknown[]).includes(priority)) errors.push("priority is unknown");
  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, value: { title, requester, priority: priority as Priority } };
}
