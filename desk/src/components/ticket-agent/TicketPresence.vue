<template>
  <div
    v-if="status !== 'ready' || viewers.length"
    role="status"
    aria-live="polite"
    class="flex max-w-64 items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-7"
    :title="label"
  >
    <LucideUsers v-if="status === 'ready'" class="size-4 shrink-0" />
    <LucideRefreshCw v-else class="size-4 shrink-0" />
    <span class="truncate">{{ label }}</span>
  </div>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useUserStore } from "@/stores/user";
import { __ } from "@/translation";
const props = defineProps<{ viewers: string[]; status: string }>();
const { getUser } = useUserStore();
const label = computed(() => {
  if (props.status === "unavailable") return __("Viewer status unavailable");
  if (props.status !== "ready") return __("Checking who is viewing…");
  const names = props.viewers.map(id => getUser(id)?.full_name || id);
  return names.length === 1
    ? __("{0} is also viewing", [names[0]])
    : __("{0} are also viewing", [names.join(", ")]);
});
</script>
