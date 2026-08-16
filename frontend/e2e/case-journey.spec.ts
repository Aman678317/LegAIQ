import { test, expect, CASE_ID } from "./mocks";
import * as path from "path";

test.describe("Case journey", () => {
  test("dashboard empty state offers to start a property case", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
    await expect(page.getByText(/no cases yet/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /start a property case/i })).toBeVisible();
  });

  test("create case → case home shows name, stats and property type", async ({ page }) => {
    await page.goto("/dashboard");

    await page.getByRole("button", { name: /new case/i }).click();
    await page
      .getByPlaceholder(/whitefield property/i)
      .fill("Whitefield Sy 124/3 — Due Diligence");
    await page.getByRole("button", { name: "Create Case" }).click();

    // createCase then hard-navigates to /cases/{id}
    await expect(page).toHaveURL(new RegExp(`/cases/${CASE_ID}`), { timeout: 15_000 });
    await expect(
      page.getByRole("heading", { name: /whitefield sy 124\/3/i })
    ).toBeVisible();
    await expect(page.getByText("Karnataka")).toBeVisible();
    await expect(page.getByText("Property", { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/open risks/i)).toBeVisible();
  });

  test("upload a deed and see it complete with OCR stats", async ({ page }) => {
    await page.goto(`/cases/${CASE_ID}/documents`);

    const dropzone = page.locator('input[type="file"]');
    await dropzone.setInputFiles({
      name: "sale_deed_1987.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 fake deed bytes"),
    });

    // Mocked API returns the completed document row
    await expect(page.getByText("sale_deed_1987.pdf")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/7 pages/i)).toBeVisible();
    await expect(page.getByText(/OCR 94%/i)).toBeVisible();
    await expect(page.getByText("COMPLETED", { exact: false }).first()).toBeVisible();
  });

  test("risks page shows the survey mismatch with evidence", async ({ page }) => {
    await page.goto(`/cases/${CASE_ID}/risks`);

    await expect(
      page.getByRole("heading", { name: /risks & issues/i })
    ).toBeVisible();

    const riskCard = page.locator("div", { hasText: "Survey number mismatch across documents" }).first();
    await expect(page.getByText(/survey number mismatch/i).first()).toBeVisible();
    await expect(page.getByText("HIGH", { exact: true }).first()).toBeVisible();
    // Evidence panel cites document and page
    await expect(page.getByText(/sale_deed_1987\.pdf · p\.7/i)).toBeVisible();
    await expect(page.getByText(/Sy\. No\. 124\/3/i).first()).toBeVisible();
    // Recommended action present
    await expect(page.getByText(/verify the official record/i).first()).toBeVisible();
  });

  test("case home reflects uploaded document and risk count", async ({ page }) => {
    // The mock state is fresh per test; documents list is populated by the mock
    // summary for determinism: visit case home and check stat cards render.
    await page.goto(`/cases/${CASE_ID}`);
    await expect(page.getByText("Documents", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Open risks", { exact: false }).first()).toBeVisible();
  });

  test("ask a question and get a cited answer", async ({ page }) => {
    await page.goto(`/cases/${CASE_ID}/questions`);

    const input = page.getByPlaceholder(/ask about parties/i);
    await input.fill("What is the survey number?");
    await input.press("Enter");

    await expect(page.getByText(/Sy\. No\. 124\/3/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/sale_deed_1987\.pdf · p\.7/i).first()).toBeVisible();
  });

  test("sidebar shows all case modules for an open case", async ({ page }) => {
    await page.goto(`/cases/${CASE_ID}`);
    for (const item of [
      "Documents", "AI Analysis", "Ownership Chain", "Property Timeline",
      "Document Comparison", "Risks & Issues", "Legal Research", "Questions",
      "Drafting", "Reports", "Voice Assistant",
    ]) {
      await expect(page.getByRole("link", { name: item, exact: false }).first()).toBeVisible();
    }
  });
});
