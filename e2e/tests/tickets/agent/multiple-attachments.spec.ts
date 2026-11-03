import { expect, test, uid, usePersona } from "../../../helpers/fixtures";
import { composer, openTicket } from "../../../helpers/ticket";

usePersona("agent");

for (const mode of ["Reply", "Comment"]) {
  test(`${mode} accepts several private attachments in one selection`, async ({
    page,
    api,
    ticket,
  }) => {
    const suffix = uid();
    const files = ["one", "two", "three"].map((name) => ({
      name: `${mode}-${name}-${suffix}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from(`TEST ONLY ${mode} ${name} ${suffix}`),
    }));
    await openTicket(page, ticket.name);
    await page.getByRole("button", { name: mode, exact: true }).click();
    await composer(page).fill("TEST ONLY: multi-file attachment draft");
    const input = page.locator('input[type="file"][multiple]');
    await expect(input).toHaveCount(1);
    await input.setInputFiles(files);
    for (const file of files) {
      await expect(page.getByText(file.name, { exact: true })).toBeVisible();
    }
    await expect(input).toBeEnabled();
    const uploaded = await api.list("File", {
      fields: [
        "file_name",
        "is_private",
        "attached_to_doctype",
        "attached_to_name",
      ],
      filters: { file_name: ["in", files.map((file) => file.name)] },
    });
    expect(uploaded).toHaveLength(3);
    for (const file of uploaded) {
      expect(file.is_private).toBe(1);
      expect(file.attached_to_doctype).toBe("HD Ticket");
      expect(String(file.attached_to_name)).toBe(String(ticket.name));
    }
    // Leave the draft unsent; this check sends no email and posts no comment.
  });
}
