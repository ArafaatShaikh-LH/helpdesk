<template>
  <Dialog
    :open="true"
    :title="__('Forward email')"
    size="2xl"
    @update:open="close"
  >
    <template #default>
      <div class="flex flex-col gap-4">
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              "Forward this email to new recipients. Their replies join this ticket. Everyone with access to the ticket can see the conversation. The original customer is not copied automatically."
            )
          }}
        </p>
        <div v-if="source.loading" role="status">
          {{ __("Loading selected email…") }}
        </div>
        <div v-if="loadError" role="alert" class="text-p-sm text-ink-red-4">
          {{ loadError }}
          <Button :label="__('Retry')" @click="loadSource" />
        </div>
        <template v-if="source.data">
          <FormControl
            v-model="fromEmail"
            type="select"
            :label="__('From')"
            :options="mailboxOptions"
            :disabled="!ready || !!receivingEmail || sending.loading"
          />
          <div v-if="senderError" role="alert" class="text-p-sm text-ink-red-4">
            {{ __(senderError) }}
            <Button :label="__('Retry')" @click="reloadSender" />
          </div>
          <p
            v-else-if="ready && !options.length"
            role="alert"
            class="text-p-sm text-ink-red-4"
          >
            {{
              __(
                "No outgoing business mailboxes are available. Contact your administrator."
              )
            }}
          </p>
          <FormControl
            v-model="to"
            :label="__('To (required)')"
            :disabled="sending.loading"
            :placeholder="__('Enter email addresses separated by commas')"
          />
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl
              v-model="cc"
              :label="__('Cc')"
              :disabled="sending.loading"
            />
            <FormControl
              v-model="bcc"
              :label="__('Bcc')"
              :disabled="sending.loading"
            />
          </div>
          <FormControl
            :model-value="source.data.subject"
            :label="__('Subject')"
            disabled
          />
          <FormControl
            v-model="note"
            type="textarea"
            :label="__('Add a message (optional)')"
            :disabled="sending.loading"
            :maxlength="50000"
            :rows="4"
          />
          <fieldset
            v-if="source.data.attachments.length"
            :disabled="sending.loading"
            class="flex flex-col gap-2"
          >
            <legend class="mb-2 text-p-sm font-medium">
              {{ __("Attachments from this email") }}
            </legend>
            <label
              v-for="file in source.data.attachments"
              :key="file.name"
              class="flex items-center gap-2 text-p-sm"
            >
              <input v-model="attachments" type="checkbox" :value="file.name" />
              {{ file.file_name }}
            </label>
          </fieldset>
          <p v-else class="text-p-sm text-ink-gray-5">
            {{ __("This email has no attachments.") }}
          </p>
          <details class="rounded border border-outline-gray-2 p-3 text-p-sm">
            <summary class="cursor-pointer">
              {{ __("Selected email preview") }}
            </summary>
            <div
              class="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words"
            >
              {{ source.data.preview_text }}
            </div>
          </details>
        </template>
        <p v-if="sendError" role="alert" class="text-p-sm text-ink-red-4">
          {{ sendError }}
        </p>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button
          :label="__('Cancel')"
          :disabled="sending.loading"
          @click="close(false)"
        />
        <Button
          :label="__('Send forward')"
          variant="solid"
          :loading="sending.loading"
          :disabled="!canSend"
          @click="send"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { useReplySender } from "@/composables/useReplySender";
import { getUserEmailInfo } from "@/composables/useUserEmailInfo";
import { __ } from "@/translation";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

const props = defineProps<{ ticketId: string; communication: string }>();
const emit = defineEmits<{ close: []; sent: [] }>();
const to = ref("");
const cc = ref("");
const bcc = ref("");
const note = ref("");
const attachments = ref<string[]>([]);
const loadError = ref("");
const sendError = ref("");
const requestId = crypto.randomUUID();
const user = getUserEmailInfo();
const accounts = computed(() => user.data?.outgoing_emails ?? []);
// This dialog owns its draft. No normal-reply localStorage or recipients are reused.
const legacySender = ref("");
const {
  fromEmail,
  selected,
  options,
  ready,
  receivingEmail,
  error: senderError,
  reload: reloadSender,
} = useReplySender(() => props.ticketId, accounts, legacySender);
const mailboxOptions = computed(() => [
  { label: __("Choose a mailbox"), value: "" },
  ...options.value
    .filter((a) => a.email_account !== "No Reply")
    .map((a) => ({
      label: `${a.email_account} <${a.email_id}>`,
      value: a.email_id,
    })),
]);
const source = createResource({
  url: "run_doc_method",
  transform: (response: any) => response?.message ?? response,
});
const sending = createResource({ url: "run_doc_method" });
const canSend = computed(
  () =>
    !!source.data &&
    !source.loading &&
    !sending.loading &&
    ready.value &&
    !!selected.value &&
    selected.value.email_account !== "No Reply" &&
    !!to.value.trim()
);

function close(open: boolean) {
  if (!open && !sending.loading) emit("close");
}

async function loadSource() {
  loadError.value = "";
  try {
    const response = await source.submit({
      dt: "HD Ticket",
      dn: props.ticketId,
      method: "get_forward_email",
      args: { communication: props.communication },
    });
    const data = response?.message ?? response;
    if (
      data?.communication !== props.communication ||
      !Array.isArray(data.attachments)
    ) {
      throw new Error(__("Unable to load the selected email."));
    }
    source.setData(data);
    attachments.value = data.attachments.map(
      (file: { name: string }) => file.name
    );
  } catch (error) {
    source.setData(null);
    loadError.value = message(error);
  }
}

async function send() {
  if (!canSend.value) return;
  sendError.value = "";
  try {
    await sending.submit({
      dt: "HD Ticket",
      dn: props.ticketId,
      method: "forward_email",
      args: {
        communication: props.communication,
        source_modified: source.data.source_modified,
        request_id: requestId,
        to: to.value,
        cc: cc.value,
        bcc: bcc.value,
        note: note.value,
        from_email: selected.value,
        attachments: attachments.value,
      },
    });
    toast.success(__("Forward queued for sending."));
    emit("sent");
    emit("close");
  } catch (error) {
    sendError.value = message(error);
  }
}

function message(error: unknown) {
  return (
    (error as { messages?: string[]; message?: string })?.messages?.join(" ") ||
    (error as Error)?.message ||
    __("Unable to forward this email. Please try again.")
  );
}
onMounted(loadSource);
</script>
