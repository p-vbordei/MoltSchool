import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LandingPage from "@/app/page";

describe("LandingPage", () => {
  it("renders the tagline", () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/Your agent now knows what your kindred knows/i)
    ).toBeInTheDocument();
  });

  it("renders the three feature cards", () => {
    render(<LandingPage />);
    expect(
      screen.getByRole("heading", { name: /Signed artifacts/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Private by default/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Cross-vendor/i })
    ).toBeInTheDocument();
  });

  it("renders the create-a-kindred CTA pointing to /login", () => {
    render(<LandingPage />);
    const cta = screen.getByRole("link", { name: /Create a kindred/i });
    expect(cta).toHaveAttribute("href", "/login");
  });
});
