<script setup lang="ts">
import LayoutHeader from "@/components/LayoutHeader.vue";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import { computed, ref, watch } from "vue";

const auth = useAuthStore();
const url = computed(() => auth.managerOverviewUrl);
const loading = ref(true);
watch(url, () => { loading.value = true; });
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col bg-surface-white">
    <LayoutHeader>
      <template #left-header>
        <h1 class="text-lg-medium text-ink-gray-9">{{ __("Manager Overview") }}</h1>
      </template>
      <template #right-header>
        <a v-if="url" :href="url" target="_blank" rel="noopener noreferrer"
          class="rounded px-3 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2">
          {{ __("Open in Insights") }}
        </a>
      </template>
    </LayoutHeader>
    <template v-if="url">
      <p v-if="loading" role="status" class="p-3 text-sm text-ink-gray-6">
        {{ __("Loading manager dashboard…") }}
      </p>
      <iframe :src="url" :title="__('Manager Overview dashboard')"
        class="min-h-0 w-full flex-1 border-0" referrerpolicy="same-origin"
        @load="loading = false" />
    </template>
    <div v-else class="p-6 text-p-base text-ink-gray-7" role="status">
      {{ __("This dashboard is not configured or has not been shared with you. Ask your administrator for access.") }}
    </div>
  </section>
</template>
