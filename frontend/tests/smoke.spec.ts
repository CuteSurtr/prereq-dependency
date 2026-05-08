import { expect, test } from "@playwright/test";

test("loads the app and navigates to a course via search", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /UCSD Prereq Graph/ })).toBeVisible();
  await expect(page.getByText(/courses across UCSD/)).toBeVisible({ timeout: 10_000 });

  await expect(page.getByText("Software Engineering").first()).toBeVisible();

  await page.getByTestId("search-input").fill("MATH 20A");
  const results = page.getByTestId("search-results");
  await expect(results).toBeVisible();
  await results.getByRole("button", { name: /MATH 20A/ }).first().click();

  await expect(page.getByText("Calculus for Science and Engineering").first()).toBeVisible();
});
