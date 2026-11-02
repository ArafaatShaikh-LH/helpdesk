<template>
  <aside
    v-if="showTicketListPane && currentTicketIndex >= 0"
    class="hidden xl:flex h-full w-72 shrink-0 flex-col border-e border-outline-gray-2 bg-surface-white"
    :aria-label="__('Tickets in the current view')"
  >
    <div class="border-b border-outline-gray-2 px-4 py-3">
      <div class="text-sm font-semibold text-ink-gray-9">
        {{ __("Tickets in this view") }}
      </div>
      <div class="mt-1 text-p-xs text-ink-gray-5">
        {{ ticketListContext.tickets.length }} {{ __("loaded") }}
        <span v-if="ticketListContext.total > ticketListContext.tickets.length">
          / {{ ticketListContext.total }} {{ __("total") }}
        </span>
      </div>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto">
      <button
        v-for="(ticketId, index) in ticketListContext.tickets"
        :key="ticketId"
        ref="ticketButtons"
        type="button"
        class="flex w-full flex-col gap-1 border-b border-outline-gray-1 px-4 py-3 text-start hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ink-gray-9"
        :class="index === currentTicketIndex ? 'bg-surface-gray-2' : ''"
        :aria-current="index === currentTicketIndex ? 'page' : undefined"
        :disabled="navigatingTicket"
        @click="navigateToTicket(ticketId)"
      >
        <span class="truncate text-p-xs text-ink-gray-5">#{{ ticketId }}</span>
        <span
          class="line-clamp-2 w-full text-p-sm text-ink-gray-9"
          :class="index === currentTicketIndex ? 'font-semibold' : ''"
        >
          {{
            ticketListSummaries[ticketId]?.subject ||
            __("Ticket {0}", [ticketId])
          }}
        </span>
        <span
          v-if="ticketListSummaries[ticketId]?.status"
          class="text-p-xs text-ink-gray-6"
        >
          {{ __(ticketListSummaries[ticketId].status) }}
        </span>
      </button>
    </div>
    <div
      v-if="ticketListContext.total > ticketListContext.tickets.length"
      class="border-t border-outline-gray-2 px-4 py-2 text-p-xs text-ink-gray-5"
    >
      {{ __("Return to the list to load more tickets.") }}
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  currentTicketIndex,
  navigateToTicket,
  navigatingTicket,
  showTicketListPane,
  ticketListContext,
  ticketListSummaries,
} from "@/composables/useTicketNavigation";
import { __ } from "@/translation";
import { createResource } from "frappe-ui";
import { nextTick, ref, watch } from "vue";

const ticketButtons = ref<HTMLButtonElement[]>([]);
const summaries = createResource({ url: "frappe.client.get_list" });
let fetchedList = "";

watch(
  () => ticketListContext.value.tickets.join(","),
  async (ids) => {
    if (!ids || fetchedList === ids) return;
    if (
      ticketListContext.value.tickets.every(
        (id) => ticketListSummaries.value[id]?.subject
      )
    )
      return;
    fetchedList = ids;
    try {
      const rows = await summaries.fetch({
        doctype: "HD Ticket",
        fields: ["name", "subject", "status"],
        filters: [["name", "in", ticketListContext.value.tickets]],
        limit_page_length: ticketListContext.value.tickets.length,
      });
      ticketListSummaries.value = {
        ...ticketListSummaries.value,
        ...Object.fromEntries(
          rows.map((row: { name: string; subject: string; status: string }) => [
            row.name,
            { subject: row.subject, status: row.status },
          ])
        ),
      };
    } catch {
      // The ticket IDs remain usable even if summaries cannot be loaded.
    }
  },
  { immediate: true }
);

watch(
  [currentTicketIndex, showTicketListPane],
  async ([index, shown]) => {
    if (index < 0 || !shown) return;
    await nextTick();
    ticketButtons.value[index]?.scrollIntoView({ block: "nearest" });
  },
  { immediate: true }
);
</script>
