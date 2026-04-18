import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProvenanceChip } from "@/components/provenance-chip";

describe("ProvenanceChip", () => {
  it("shows Blessed label for blessed tier", () => {
    render(<ProvenanceChip tier="blessed" author="pk_owner_alice" />);
    expect(screen.getByText("Blessed")).toBeInTheDocument();
  });

  it("defaults to Observed when tier missing", () => {
    render(<ProvenanceChip />);
    expect(screen.getByText("Observed")).toBeInTheDocument();
  });

  it("truncates long pubkeys", () => {
    render(
      <ProvenanceChip tier="peer" author="pk_owner_abcdefghijklmnopqrstuv" />
    );
    // 8 chars + ellipsis + last 4
    expect(screen.getByText(/pk_owner…rstuv|pk_owner…/i)).toBeInTheDocument();
  });

  it("shows outcome counts when present", () => {
    render(
      <ProvenanceChip
        tier="peer"
        author="pk_agent_x"
        outcomes={{ positive: 7, negative: 2 }}
      />
    );
    expect(screen.getByText(/7 helped/)).toBeInTheDocument();
    expect(screen.getByText(/2 reverted/)).toBeInTheDocument();
  });
});
