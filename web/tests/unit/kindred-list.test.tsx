import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KindredList } from "@/components/kindred-list";

describe("KindredList", () => {
  it("shows empty state when no kindreds", () => {
    render(<KindredList kindreds={[]} />);
    expect(screen.getByText(/No kindreds yet/i)).toBeInTheDocument();
  });

  it("renders each kindred with slug and counts", () => {
    render(
      <KindredList
        kindreds={[
          {
            slug: "coven",
            display_name: "The Coven",
            description: "witchy things",
            member_count: 4,
            artifact_count: 12,
          },
          { slug: "brewers", display_name: "Brewers", member_count: 2 },
        ]}
      />
    );
    expect(screen.getByText("The Coven")).toBeInTheDocument();
    expect(screen.getByText("/coven")).toBeInTheDocument();
    expect(screen.getByText("4 members")).toBeInTheDocument();
    expect(screen.getByText("12 artifacts")).toBeInTheDocument();
    expect(screen.getByText("Brewers")).toBeInTheDocument();
    expect(screen.getByText("2 members")).toBeInTheDocument();
  });

  it("kindred card links to /dashboard/<slug>", () => {
    render(
      <KindredList
        kindreds={[{ slug: "coven", display_name: "Coven" }]}
      />
    );
    const link = screen.getByRole("link", { name: /Coven/i });
    expect(link).toHaveAttribute("href", "/dashboard/coven");
  });
});
