<template>
  <div
    class="flex items-center gap-1"
    role="group"
    :aria-label="__('Ticket navigation')"
  >
    <Tooltip :text="previousHint">
      <Button
        :label="__('Previous')"
        :disabled="!previousTicket || navigatingTicket"
        @click="goToPreviousTicket()"
      >
        <template #prefix><LucideChevronLeft class="size-4" /></template>
      </Button>
    </Tooltip>
    <span
      v-if="currentTicketIndex >= 0"
      class="hidden lg:inline whitespace-nowrap px-1 text-p-xs text-ink-gray-5"
      :title="__('Position in the loaded ticket list')"
    >
      {{ currentTicketIndex + 1 }} / {{ ticketListContext.tickets.length }}
    </span>
    <Tooltip :text="nextHint">
      <Button
        :label="__('Next')"
        :disabled="!nextTicket || navigatingTicket"
        @click="goToNextTicket()"
      >
        <template #suffix><LucideChevronRight class="size-4" /></template>
      </Button>
    </Tooltip>
  </div>
</template>

<script setup lang="ts">
import {
  currentTicketIndex,
  getNextTicket,
  getPreviousTicket,
  goToNextTicket,
  goToPreviousTicket,
  navigatingTicket,
  ticketListContext,
} from "@/composables/useTicketNavigation";
import { __ } from "@/translation";
import { Button, Tooltip } from "frappe-ui";
import { computed } from "vue";
import LucideChevronLeft from "~icons/lucide/chevron-left";
import LucideChevronRight from "~icons/lucide/chevron-right";

const previousTicket = computed(getPreviousTicket);
const nextTicket = computed(getNextTicket);
const openListHint = () =>
  __("Open a ticket from the ticket list to use Previous and Next.");
const previousHint = computed(() => {
  if (currentTicketIndex.value < 0) return openListHint();
  return previousTicket.value
    ? __("Previous ticket in this list (Shift + <)")
    : __("First ticket in this list");
});
const nextHint = computed(() => {
  if (currentTicketIndex.value < 0) return openListHint();
  if (nextTicket.value) return __("Next ticket in this list (Shift + >)");
  return ticketListContext.value.total > ticketListContext.value.tickets.length
    ? __("End of loaded tickets. Return to the list and load more to continue.")
    : __("Last ticket in this list");
});
</script>
