<template>
  <div>
    <input
      ref="input"
      type="file"
      multiple
      class="hidden"
      :disabled="uploading"
      @change="onFilesSelected"
    />
    <slot
      :openFileSelector="openFileSelector"
      :uploading="uploading"
      :progress="progress"
    />
  </div>
</template>

<script setup lang="ts">
import { useFileUpload, type UploadedFile } from "frappe-ui";
import { onBeforeUnmount, ref } from "vue";

const props = defineProps<{
  doctype?: string;
  docname?: string;
  folder?: string;
}>();
const emit = defineEmits<{
  success: [file: UploadedFile];
  failure: [error: unknown];
}>();
const input = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const { upload, progress } = useFileUpload();
let disposed = false;
let controller: AbortController | null = null;

function openFileSelector() {
  if (!uploading.value) input.value?.click();
}

async function onFilesSelected(event: Event) {
  if (uploading.value || disposed) return;
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  target.value = "";
  if (!files.length) return;

  uploading.value = true;
  try {
    for (const file of files) {
      if (disposed) break;
      controller = new AbortController();
      try {
        const uploaded = await upload(file, {
          private: true,
          doctype: props.doctype,
          docname: props.docname,
          folder: props.folder,
          signal: controller.signal,
        });
        if (!disposed) emit("success", uploaded);
      } catch (error) {
        if (!disposed) emit("failure", error);
      } finally {
        controller = null;
      }
    }
  } finally {
    uploading.value = false;
  }
}

onBeforeUnmount(() => {
  disposed = true;
  controller?.abort();
});
</script>
