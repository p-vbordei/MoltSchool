import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InstallCTAs } from "@/components/install-ctas";

describe("InstallCTAs", () => {
  it("renders Claude Code, CLI, and ChatGPT cards", () => {
    render(
      <InstallCTAs inviteUrl="https://kindred.sh/k/coven?inv=abc" inviteToken="abc" />
    );
    expect(screen.getByText("Claude Code")).toBeInTheDocument();
    expect(screen.getByText("CLI")).toBeInTheDocument();
    expect(screen.getByText("ChatGPT")).toBeInTheDocument();
    expect(screen.getByText(/Coming soon/i)).toBeInTheDocument();
  });

  it("embeds the invite token in the Claude Code one-liner", () => {
    render(
      <InstallCTAs inviteUrl="https://kindred.sh/k/coven?inv=abc" inviteToken="abc" />
    );
    expect(
      screen.getByText(/curl kindred.sh\/install \| sh -s -- join abc/)
    ).toBeInTheDocument();
  });

  it("copies the command when Copy is clicked", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    render(
      <InstallCTAs inviteUrl="https://kindred.sh/k/coven?inv=tok" inviteToken="tok" />
    );
    const copyButtons = screen.getAllByRole("button", { name: /Copy/i });
    fireEvent.click(copyButtons[0]);
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(
        "curl kindred.sh/install | sh -s -- join tok"
      )
    );
  });
});
