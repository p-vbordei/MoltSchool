import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LandingPage from "@/app/page";
import { metadata } from "@/app/layout";

describe("LandingPage", () => {
  it("renders the tagline", () => {
    render(<LandingPage />);
    expect(
      screen.getByRole("heading", {
        name: /Write once\. Every AI on your team knows\./i,
      })
    ).toBeInTheDocument();
  });

  it("renders the plain-language subtitle", () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/A shared notebook for your team/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Every teammate's AI reads it/i)
    ).toBeInTheDocument();
  });

  it("renders the three feature cards in plain language", () => {
    render(<LandingPage />);
    expect(
      screen.getByRole("heading", { name: /Write once, share once/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Old pages fade/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Works with any AI/i })
    ).toBeInTheDocument();
  });

  it("renders the create-your-notebook CTA pointing to /login", () => {
    render(<LandingPage />);
    const cta = screen.getByRole("link", { name: /Create your notebook/i });
    expect(cta).toHaveAttribute("href", "/login");
  });

  it("does not expose internal jargon in the public pitch", () => {
    const { container } = render(<LandingPage />);
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/grimoire/i);
    expect(text).not.toMatch(/facilitator/i);
    expect(text).not.toMatch(/Ed25519/i);
    expect(text).not.toMatch(/signed artifacts/i);
    expect(text).not.toMatch(/cryptographic provenance/i);
    expect(text).not.toMatch(/knowledge co-op/i);
  });
});

describe("Root layout metadata", () => {
  it("uses plain-language title and description", () => {
    expect(metadata.title).toMatch(/shared notebook/i);
    expect(metadata.description).toMatch(/Write once/i);
    expect(metadata.description).toMatch(/every teammate/i);
  });

  it("does not expose internal jargon in title or description", () => {
    const haystack = `${String(metadata.title)} ${String(metadata.description)}`;
    expect(haystack).not.toMatch(/grimoire/i);
    expect(haystack).not.toMatch(/facilitator/i);
    expect(haystack).not.toMatch(/knowledge co-op/i);
    expect(haystack).not.toMatch(/signed, trusted memory/i);
  });
});
