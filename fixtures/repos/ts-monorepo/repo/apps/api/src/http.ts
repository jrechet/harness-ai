import type { IncomingMessage, ServerResponse } from "node:http";
import { isStatus, parseNewTicket } from "@deskly/shared";
import { TicketNotFound, TransitionRefused } from "./tickets/service.ts";
import type { TicketService } from "./tickets/service.ts";

async function readJson(req: IncomingMessage): Promise<unknown> {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  try {
    return raw === "" ? {} : JSON.parse(raw);
  } catch {
    return undefined;
  }
}

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

// createApp maps HTTP onto the ticket service. Rules stay in the service and in
// @deskly/shared; this file only translates.
export function createApp(tickets: TicketService) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const url = new URL(req.url ?? "/", "http://localhost");
    const ticketId = /^\/tickets\/([^/]+)$/.exec(url.pathname)?.[1];
    try {
      if (req.method === "GET" && url.pathname === "/tickets") {
        return send(res, 200, tickets.list());
      }
      if (req.method === "POST" && url.pathname === "/tickets") {
        const parsed = parseNewTicket(await readJson(req));
        if (!parsed.ok) return send(res, 422, { code: "invalid_ticket", errors: parsed.errors });
        return send(res, 201, tickets.create(parsed.value));
      }
      if (req.method === "PATCH" && ticketId) {
        const body = (await readJson(req)) as { status?: unknown } | undefined;
        if (!isStatus(body?.status)) return send(res, 422, { code: "unknown_status" });
        return send(res, 200, tickets.changeStatus(ticketId, body.status));
      }
      return send(res, 404, { code: "not_found" });
    } catch (error) {
      if (error instanceof TicketNotFound) return send(res, 404, { code: "ticket_not_found" });
      if (error instanceof TransitionRefused) {
        return send(res, 409, { code: "transition_refused", from: error.from, to: error.to });
      }
      return send(res, 500, { code: "internal" });
    }
  };
}
