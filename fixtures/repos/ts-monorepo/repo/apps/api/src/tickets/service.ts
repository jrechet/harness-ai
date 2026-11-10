import { canTransition } from "@deskly/shared";
import type { NewTicket, Status, Ticket } from "@deskly/shared";
import type { TicketStore } from "./store.ts";

export class TicketNotFound extends Error {}

export class TransitionRefused extends Error {
  from: Status;
  to: Status;
  constructor(from: Status, to: Status) {
    super(`a ${from} ticket cannot become ${to}`);
    this.from = from;
    this.to = to;
  }
}

export interface Deps {
  store: TicketStore;
  now: () => Date;
  newId: () => string;
}

export function createTicketService({ store, now, newId }: Deps) {
  return {
    list(): Ticket[] {
      return store.list();
    },

    create(input: NewTicket): Ticket {
      const at = now().toISOString();
      const ticket: Ticket = { id: newId(), ...input, status: "open", createdAt: at, updatedAt: at };
      store.save(ticket);
      return ticket;
    },

    changeStatus(id: string, to: Status): Ticket {
      const ticket = store.get(id);
      if (!ticket) throw new TicketNotFound(id);
      if (!canTransition(ticket.status, to)) throw new TransitionRefused(ticket.status, to);
      const updated: Ticket = { ...ticket, status: to, updatedAt: now().toISOString() };
      store.save(updated);
      return updated;
    },
  };
}

export type TicketService = ReturnType<typeof createTicketService>;
