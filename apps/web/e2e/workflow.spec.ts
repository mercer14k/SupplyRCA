import { test, expect } from "@playwright/test";
test("investigate, inspect evidence, review, persist, export and browse data", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Supplier receipt shortfall" }),
  ).toBeVisible();
  await expect(page.getByText("64.8%", { exact: true })).toBeVisible();
  if (process.env.CAPTURE_SCREENSHOTS)
    await page.screenshot({
      path: "../../docs/screenshots/workspace.png",
      fullPage: true,
    });
  await page
    .getByRole("button", { name: "Source evidence", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: /P-SKU-001/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Raw source record" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(page.getByText("accepted", { exact: true })).toBeVisible();
  await page.getByText("Analyst notes", { exact: true }).click();
  await page
    .getByRole("textbox", { name: "Investigation note" })
    .fill("Receipt history verified in end-to-end test.");
  await page.getByRole("button", { name: "Save annotation" }).click();
  await expect(page.getByText("annotated", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Investigation narrative" }).click();
  await expect(page.getByText(/Deterministic narrative/)).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export report", exact: true })
    .click();
  expect((await downloadPromise).suggestedFilename()).toMatch(
    /supplyrca-.*\.md/,
  );
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page.getByRole("button", { name: "Open", exact: true }).first().click();
  await page.getByRole("tab", { name: /Contributing factors/ }).click();
  await expect(page.getByText("annotated", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Data & validation", exact: true })
    .click();
  await expect(page.getByText("All checks passed")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search raw records" })
    .fill("D-SKU-001-2024-04-20");
  await expect(
    page.getByRole("cell", { name: "D-SKU-001-2024-04-20", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Known boundaries" }),
  ).toBeVisible();
  expect(failures).toEqual([]);
});
test("responsive screen has no horizontal page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Supplier receipt shortfall" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  if (process.env.CAPTURE_SCREENSHOTS)
    await page.screenshot({
      path: "../../docs/screenshots/mobile.png",
      fullPage: true,
    });
});
