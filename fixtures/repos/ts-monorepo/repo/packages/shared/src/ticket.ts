// The ticket model shared by the API and the web app. A status or a transition
// is declared here once; neither app keeps its own list.

export const STATUSES = ["open", "in_progress", "waiting", "resolved", "closed"] as const;
export type Status = (typeof STATUSES)[number];

export const PRIORITIES = ["low", "normal", "high"] as const;
export type Priority = (typeof PRIORITIES)[number];

export interface Ticket {
  id: string;
  title: string;
  requester: string;
  status: Status;
  priority: Priority;
  createdAt: string;
  updatedAt: string;
}

const TRANSITIONS: Record<Status, readonly Status[]> = {
  open: ["in_progress", "closed"],
  in_progress: ["waiting", "resolved"],
  waiting: ["in_progress", "closed"],
  resolved: ["closed", "in_progress"],
  closed: [],
};

export function isStatus(value: unknown): value is Status {
  return typeof value === "string" && (STATUSES as readonly string[]).includes(value);
}

export function nextStatuses(from: Status): readonly Status[] {
  return TRANSITIONS[from];
}

export function canTransition(from: Status, to: Status): boolean {
  return TRANSITIONS[from].includes(to);
}
