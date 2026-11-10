import { isStatus } from "@deskly/shared";
import { createApiClient } from "./api-client.ts";
import { renderTicketList } from "./ticket-list.ts";

const api = createApiClient("/api");
const root = document.querySelector<HTMLElement>("#tickets");

async function refresh(): Promise<void> {
  if (root) root.innerHTML = renderTicketList(await api.list());
}

root?.addEventListener("click", async (event) => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-ticket]");
  const status = button?.dataset.status;
  if (!button?.dataset.ticket || !isStatus(status)) return;
  await api.changeStatus(button.dataset.ticket, status);
  await refresh();
});

void refresh();
