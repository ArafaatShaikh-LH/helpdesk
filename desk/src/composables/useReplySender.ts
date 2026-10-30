import { createResource } from "frappe-ui";
import { computed, ref, watch, type Ref } from "vue";

type Mailbox = { email_account: string; email_id: string };
type SenderPolicy = {
  ticket: string;
  enabled: boolean;
  sender: Mailbox | null;
  available_senders: Mailbox[];
};

export function useReplySender(
  ticketId: () => string | number,
  accounts: Ref<Mailbox[]>,
  legacySender: Ref<string>
) {
  const fromEmail = ref("");
  const ready = ref(false);
  const receivingMailboxMode = ref(false);
  const receivingEmail = ref("");
  const receivingAccount = ref<Mailbox | null>(null);
  const availableSenders = ref<Mailbox[]>([]);
  const error = ref("");
  let generation = 0;
  const request = createResource({ url: "run_doc_method" });
  const options = computed(() => {
    const eligible = receivingMailboxMode.value
      ? availableSenders.value
      : accounts.value;
    const incoming = receivingAccount.value;
    return incoming &&
      !eligible.some((a) => a.email_account === incoming.email_account)
      ? [...eligible, incoming]
      : eligible;
  });
  const selected = computed(() =>
    options.value.find((account) => account.email_id === fromEmail.value)
  );

  function reconcile() {
    if (!ready.value) return;
    if (receivingMailboxMode.value && receivingEmail.value) {
      fromEmail.value = receivingEmail.value;
    } else if (!selected.value) {
      fromEmail.value = receivingMailboxMode.value
        ? ""
        : accounts.value[0]?.email_id ?? "";
    }
  }

  async function reload() {
    const current = ++generation;
    const ticket = String(ticketId());
    ready.value = false;
    fromEmail.value = "";
    receivingEmail.value = "";
    receivingAccount.value = null;
    availableSenders.value = [];
    error.value = "";
    try {
      const response = await request.submit({
        dt: "HD Ticket",
        dn: ticket,
        method: "get_reply_sender",
      });
      if (current !== generation) return;
      const policy: SenderPolicy = response?.message ?? response;
      if (
        String(policy?.ticket) !== ticket ||
        typeof policy.enabled !== "boolean" ||
        (policy.enabled &&
          !policy.sender &&
          !Array.isArray(policy.available_senders))
      ) {
        throw new Error("Invalid sender policy");
      }
      receivingMailboxMode.value = policy.enabled;
      receivingAccount.value = policy.enabled ? policy.sender : null;
      availableSenders.value = policy.enabled ? policy.available_senders ?? [] : [];
      receivingEmail.value = receivingAccount.value?.email_id ?? "";
      fromEmail.value = policy.enabled
        ? receivingEmail.value
        : legacySender.value;
      ready.value = true;
      reconcile();
    } catch {
      if (current === generation) {
        error.value =
          "Unable to determine the sending mailbox. Retry before sending.";
      }
    }
  }

  watch(accounts, reconcile);
  watch(fromEmail, (value) => {
    if (ready.value && !receivingMailboxMode.value) legacySender.value = value;
  });
  watch(ticketId, reload, { immediate: true });

  return {
    fromEmail,
    selected,
    options,
    ready,
    receivingMailboxMode,
    receivingEmail,
    error,
    reload,
  };
}
