import { render, screen } from "@testing-library/vue";
import { describe, expect, it } from "vitest";
import AppButton from "./AppButton.vue";

describe("AppButton", () => {
  it("renders its label", () => {
    render(AppButton, { props: { label: "Ajouter" } });
    expect(screen.getByRole("button", { name: "Ajouter" })).toBeTruthy();
  });
});
