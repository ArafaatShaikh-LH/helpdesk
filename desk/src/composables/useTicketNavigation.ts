import { useShortcut } from "@/composables/shortcuts";
import { router } from "@/router";
import { useSessionStorage } from "@vueuse/core";
import { computed, ref } from "vue";

interface TicketListContext {
  tickets: string[];
  view: string;
  total: number;
}

interface TicketListSummary {
  subject: string;
  status: string;
}

const cookies = new URLSearchParams(document.cookie.split("; ").join("&"));
// Keep only IDs, scoped to this agent and tab; never cache ticket content here.
export const ticketListContext = useSessionStorage<TicketListContext>(
  `hd_ticket_navigation:${cookies.get("user_id") || "guest"}`,
  { tickets: [], view: "", total: 0 },
  { flush: "sync" }
);
export const navigatingTicket = ref(false);
// Display data lives only in memory. sessionStorage still contains IDs only.
export const ticketListSummaries = ref<Record<string, TicketListSummary>>({});
export const showTicketListPane = ref(true);

export function rememberTicketList(
  rows: {
    name: string | number;
    subject?: string;
    status?: string;
    rows?: { name: string | number; subject?: string; status?: string }[];
  }[],
  view: string,
  total: number
) {
  const flatRows = rows.flatMap((row) => row.rows || [row]);
  const tickets = flatRows.map((row) => String(row.name));
  ticketListSummaries.value = Object.fromEntries(
    flatRows.map((row) => [
      String(row.name),
      { subject: row.subject || "", status: row.status || "" },
    ])
  );
  ticketListContext.value = {
    tickets: [...new Set(tickets)],
    view: view || "",
    total,
  };
}

export const currentTicketIndex = computed(() => {
  const route = router.currentRoute.value;
  if (route.name !== "TicketAgent") return -1;
  if ((route.query.view || "") !== ticketListContext.value.view) return -1;
  return ticketListContext.value.tickets.indexOf(String(route.params.ticketId));
});

export function getCurrentTicket() {
  return ticketListContext.value.tickets[currentTicketIndex.value] || null;
}

export function getNextTicket() {
  if (currentTicketIndex.value < 0) return null;
  return ticketListContext.value.tickets[currentTicketIndex.value + 1] || null;
}

export function getPreviousTicket() {
  if (currentTicketIndex.value <= 0) return null;
  return ticketListContext.value.tickets[currentTicketIndex.value - 1] || null;
}

export function goToNextTicket() {
  return moveToTicket(getNextTicket());
}

export function goToPreviousTicket() {
  return moveToTicket(getPreviousTicket());
}

function moveToTicket(ticketId: string | null) {
  if (!ticketId || navigatingTicket.value) return null;
  navigateToTicket(ticketId);
  return ticketId;
}

export function navigateToTicket(ticketId: string) {
  const view = router.currentRoute.value.query.view;
  navigatingTicket.value = true;
  return router
    .push({
      name: "TicketAgent",
      params: { ticketId },
      query: view ? { view } : {},
      hash: "",
    })
    .finally(() => {
      navigatingTicket.value = false;
    });
}

export function canNavigateTickets() {
  return (
    !navigatingTicket.value &&
    currentTicketIndex.value >= 0 &&
    ticketListContext.value.tickets.length > 1
  );
}

// Register once on the ticket page; header buttons reuse the same functions.
export function useTicketNavigation() {
  useShortcut(
    { key: ">", shift: true },
    () => canNavigateTickets() && goToNextTicket()
  );
  useShortcut(
    { key: "<", shift: true },
    () => canNavigateTickets() && goToPreviousTicket()
  );
}
