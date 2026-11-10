import type { Ticket } from "@deskly/shared";

// In-memory store. The production adapter lives in another repository
// (deskly-infra) and implements the same three methods.
export class TicketStore {
  #tickets = new Map<string, Ticket>();

  list(): Ticket[] {
    return [...this.#tickets.values()].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }

  get(id: string): Ticket | undefined {
    return this.#tickets.get(id);
  }

  save(ticket: Ticket): void {
    this.#tickets.set(ticket.id, ticket);
  }
}
