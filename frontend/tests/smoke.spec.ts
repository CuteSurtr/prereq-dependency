import { expect, test } from "@playwright/test";

test("loads the app and navigates to a course via search", async ({ page }) => {
  await page.goto("/");

  // Title and graph data load
  await expect(page.getByRole("heading", { name: /UCSD Prereq Graph/ })).toBeVisible();
  await expect(page.getByText(/courses across Tier 1 majors/)).toBeVisible({ timeout: 10_000 });

  // Default focus is CSE 110 — its sidebar header should be visible.
  await expect(page.getByText("Software Engineering").first()).toBeVisible();

  // Search and pick a course.
  await page.getByTestId("search-input").fill("MATH 20A");
  const results = page.getByTestId("search-results");
  await expect(results).toBeVisible();
  await results.getByRole("button", { name: /MATH 20A/ }).first().click();

  // After selecting, the focus course title for MATH 20A should appear in the sidebar.
  await expect(page.getByText("Calculus for Science and Engineering").first()).toBeVisible();
});
