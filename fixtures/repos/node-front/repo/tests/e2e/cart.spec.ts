import { expect, test } from "@playwright/test";
test("adds a product to the cart", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add to cart" }).first().click();
  await expect(page.getByTestId("cart-count")).toHaveText("1");
});
