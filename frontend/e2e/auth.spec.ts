import { test, expect } from "./mocks";

test.describe("Authentication", () => {
  test("landing page shows hero and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("AI for Legal Work");
    await expect(page.getByRole("link", { name: /start a property case/i }).first()).toBeVisible();
  });

  test("login form submits and lands on the dashboard", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

    await page.getByLabel("Email", { exact: false }).fill("lawyer@e2e.test");
    await page.getByLabel("Password", { exact: false }).fill("correct-horse-battery");
    await page.getByRole("button", { name: "Sign in" }).click();

    // signInWithPassword is mocked to return a session; app pushes /dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
  });

  test("signup page renders and validates password length hint", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();
    await expect(page.getByPlaceholder(/at least 8 characters/i)).toBeVisible();
  });
});
