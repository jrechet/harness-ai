import type { NewTicket, Status, Ticket } from "@deskly/shared";

type Fetch = typeof fetch;

export class ApiError extends Error {
  status: number;
  constructor(status: number, code: string) {
    super(code);
    this.status = status;
  }
}

async function call<T>(fetchImpl: Fetch, url: string, init?: RequestInit): Promise<T> {
  const response = await fetchImpl(url, { ...init, headers: { "content-type": "application/json" } });
  const body = (await response.json()) as { code?: string };
  if (!response.ok) throw new ApiError(response.status, body.code ?? "unknown");
  return body as T;
}

export function createApiClient(baseUrl: string, fetchImpl: Fetch = fetch) {
  return {
    list: () => call<Ticket[]>(fetchImpl, `${baseUrl}/tickets`),
    create: (ticket: NewTicket) => call<Ticket>(fetchImpl, `${baseUrl}/tickets`, { method: "POST", body: JSON.stringify(ticket) }),
    changeStatus: (id: string, status: Status) =>
      call<Ticket>(fetchImpl, `${baseUrl}/tickets/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  };
}
