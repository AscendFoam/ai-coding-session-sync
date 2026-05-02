import { test, expect } from "@playwright/test";

test.describe("AISS desktop workbench command interactions", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "AISS Desktop Workbench" })).toBeVisible();
    await expect(page.locator("#activityLog")).toBeVisible();
    await waitForWorkbenchReady(page);
  });

  test("Ctrl/Cmd+K toggles command palette", async ({ page }, testInfo) => {
    const modifier = testInfo.project.name.includes("webkit") ? "Meta" : "Control";

    await expect(page.getByRole("dialog", { name: "Command palette" })).toBeHidden();
    await page.keyboard.press(`${modifier}+K`);
    await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
    await page.keyboard.press(`${modifier}+K`);
    await expect(page.getByRole("dialog", { name: "Command palette" })).toBeHidden();
  });

  test("Arrow navigation wraps within the current command group", async ({ page }, testInfo) => {
    const modifier = testInfo.project.name.includes("webkit") ? "Meta" : "Control";

    await page.keyboard.press(`${modifier}+K`);
    await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();

    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "open_palette");
    await page.keyboard.press("ArrowUp");
    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "clear_filters");
    await page.keyboard.press("ArrowDown");
    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "open_palette");
  });

  test("PageUp and PageDown jump between command groups", async ({ page }, testInfo) => {
    const modifier = testInfo.project.name.includes("webkit") ? "Meta" : "Control";

    await page.keyboard.press(`${modifier}+K`);
    await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();

    await page.keyboard.press("PageDown");
    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "open_live_api");

    await page.keyboard.press("PageDown");
    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "copy_session_key");

    await page.keyboard.press("PageUp");
    await expect(activePaletteCommand(page)).toHaveAttribute("data-command-id", "open_live_api");
  });

  test("direct shortcut triggers the command without palette selection", async ({ page }) => {
    await expect(page.locator("#detailPanelManifest")).toBeVisible();
    await page.keyboard.press("P");
    await expect(page.locator("#detailPanelPatch")).toBeVisible();
    await expect(page.locator('[data-testid="action-feedback"]')).toContainText("Focused patch guidance.");

    await page.keyboard.press("E");
    await expect(page.locator("#detailPanelCompare")).toBeVisible();
    await expect(page.locator('[data-testid="action-feedback"]')).toContainText("Focused excerpt compare.");

    await page.keyboard.press("H");
    await expect(page.locator("#detailPanelHandoff")).toBeVisible();
    await expect(page.locator('[data-testid="action-feedback"]')).toContainText("Focused handoff markdown.");
  });

  test("history export downloads the current session audit trail payload", async ({ page }) => {
    await page.keyboard.press("P");
    await page.keyboard.press("H");

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export Log" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/^aiss-command-history-.*\.json$/);
    const content = await readDownloadText(download);
    const payload = JSON.parse(content);

    expect(payload.schema_version).toBe("aiss-desktop-command-history/v1");
    expect(payload.history_session.id).toBeTruthy();
    expect(payload.history_session.started_at).toBeTruthy();
    expect(payload.view.filter).toBe("all");
    expect(payload.view.group_by).toBe("category");
    expect(payload.view.sort_order).toBe("desc");
    expect(payload.workbench.source_mode).toBe("fixtures");
    expect(payload.entries.length).toBeGreaterThanOrEqual(3);

    const titles = payload.entries.map((entry) => entry.title);
    expect(titles).toContain("Focus patch guidance");
    expect(titles).toContain("Focus handoff markdown");
    expect(titles).toContain("Export command history");

    const exportEntry = payload.entries.find((entry) => entry.title === "Export command history");
    expect(exportEntry.kind).toBe("success");
    expect(exportEntry.group).toBe("History");
    expect(exportEntry.source).toBe("toolbar");
    expect(typeof exportEntry.sequence).toBe("number");
  });
});

function activePaletteCommand(page) {
  return page.locator(".palette-command.is-active");
}

async function readDownloadText(download) {
  const stream = await download.createReadStream();
  return await new Promise((resolve, reject) => {
    let result = "";
    stream.setEncoding("utf-8");
    stream.on("data", (chunk) => {
      result += chunk;
    });
    stream.on("end", () => resolve(result));
    stream.on("error", reject);
  });
}

async function waitForWorkbenchReady(page) {
  await expect(page.locator("#detailTitle")).not.toHaveText("Loading…");
  await expect(page.locator("#detailTitle")).not.toHaveText("Load failed");
  await expect(page.locator("#detailTitle")).not.toHaveText("No session selected");
  await expect(page.locator("#copySessionKeyButton")).toBeEnabled();
}
