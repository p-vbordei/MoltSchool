import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArtifactCard } from "@/components/artifact-card";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("ArtifactCard", () => {
  const base = {
    content_id: "bafybeigdyrabcdefghijklmnopqr",
    logical_name: "Espresso recipe",
    type: "moltflow/fact",
    tier: "blessed" as const,
    author_pubkey: "pk_owner_user123",
  };

  it("renders logical_name, type, and blessed provenance", () => {
    render(<ArtifactCard artifact={base} kindredSlug="coven" />);
    expect(screen.getByText("Espresso recipe")).toBeInTheDocument();
    expect(screen.getByText(/moltflow\/fact/i)).toBeInTheDocument();
    expect(screen.getByText(/Blessed/)).toBeInTheDocument();
  });

  it("renders markdown content safely (XSS payload stripped)", () => {
    const malicious =
      "Normal text\n\n<script>window.stolen='yes'</script>\n\n[bad](javascript:alert(1))";
    const { container } = render(
      <ArtifactCard
        artifact={{ ...base, content: malicious }}
        kindredSlug="coven"
      />
    );
    const html = container.innerHTML;
    expect(html).not.toContain("<script");
    expect(html.toLowerCase()).not.toContain("javascript:");
  });

  it("renders tags when provided", () => {
    render(
      <ArtifactCard
        artifact={{ ...base, tags: ["coffee", "morning"] }}
        kindredSlug="coven"
      />
    );
    expect(screen.getByText("#coffee")).toBeInTheDocument();
    expect(screen.getByText("#morning")).toBeInTheDocument();
  });
});
