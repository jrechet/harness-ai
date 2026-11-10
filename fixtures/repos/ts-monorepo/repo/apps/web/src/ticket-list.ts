import { nextStatuses } from "@deskly/shared";
import type { Ticket } from "@deskly/shared";
import { statusLabel } from "./status-label.ts";

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => ESCAPES[char] ?? char);
}

function renderActions(ticket: Ticket): string {
  return nextStatuses(ticket.status)
    .map((next) => `<button data-ticket="${escapeHtml(ticket.id)}" data-status="${next}">${escapeHtml(statusLabel(next))}</button>`)
    .join("");
}

// renderTicketList returns markup: every value that came from a user goes
// through escapeHtml.
export function renderTicketList(tickets: readonly Ticket[]): string {
  if (tickets.length === 0) return '<p class="empty">Aucun ticket.</p>';
  const rows = tickets
    .map(
      (ticket) =>
        `<li class="ticket ticket--${ticket.priority}">` +
        `<strong>${escapeHtml(ticket.title)}</strong> ` +
        `<span class="requester">${escapeHtml(ticket.requester)}</span> ` +
        `<span class="status">${escapeHtml(statusLabel(ticket.status))}</span> ` +
        renderActions(ticket) +
        `</li>`,
    )
    .join("");
  return `<ul class="tickets">${rows}</ul>`;
}
