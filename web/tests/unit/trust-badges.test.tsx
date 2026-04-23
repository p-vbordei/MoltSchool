import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrustBadges } from "@/components/trust-badges";

const NOW = new Date("2026-04-23T12:00:00Z");

describe("TrustBadges", () => {
  it("shows N/threshold bless count", () => {
    render(
      <TrustBadges blessingsCount={3} blessThreshold={2} now={NOW} />
    );
    expect(screen.getByText("3/2")).toBeInTheDocument();
  });

  it("styles reached threshold differently from unreached", () => {
    const { container: reached } = render(
      <TrustBadges blessingsCount={3} blessThreshold={2} now={NOW} />
    );
    const { container: unreached } = render(
      <TrustBadges blessingsCount={1} blessThreshold={2} now={NOW} />
    );
    expect(reached.innerHTML).toContain("tier-blessed");
    expect(unreached.innerHTML).not.toContain("tier-blessed");
  });

  it("omits bless badge when counts not supplied", () => {
    render(<TrustBadges validUntil="2026-06-01T00:00:00Z" now={NOW} />);
    expect(screen.queryByText(/\//)).not.toBeInTheDocument();
  });

  it("renders 'expires in 39d' for a distant expiry", () => {
    render(<TrustBadges validUntil="2026-06-01T12:00:00Z" now={NOW} />);
    expect(screen.getByText(/expires in 39d/)).toBeInTheDocument();
  });

  it("renders 'expires in 3d' with critical styling when <7 days", () => {
    const { container } = render(
      <TrustBadges validUntil="2026-04-26T12:00:00Z" now={NOW} />
    );
    expect(screen.getByText(/expires in 3d/)).toBeInTheDocument();
    expect(container.innerHTML).toContain("orange");
  });

  it("renders 'expired Nd ago' when past valid_until", () => {
    render(<TrustBadges validUntil="2026-04-20T12:00:00Z" now={NOW} />);
    expect(screen.getByText(/expired 3d ago/)).toBeInTheDocument();
  });

  it("renders nothing when no props given", () => {
    const { container } = render(<TrustBadges now={NOW} />);
    expect(container.querySelector("span")).toBeNull();
  });
});
