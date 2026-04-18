import { describe, it, expect } from "vitest";
import { safeMarkdown } from "@/lib/sanitize";

describe("safeMarkdown", () => {
  it("renders basic markdown to HTML", () => {
    const html = safeMarkdown("# hello\n\nthis is **bold**");
    expect(html).toContain("<h1");
    expect(html).toContain("hello");
    expect(html).toContain("<strong>bold</strong>");
  });

  it("strips <script> tags", () => {
    const html = safeMarkdown(
      "ok\n\n<script>alert('xss')</script>\n\ndone"
    );
    expect(html).not.toContain("<script");
    expect(html).not.toContain("alert");
  });

  it("strips inline event handlers and javascript: URLs", () => {
    const html = safeMarkdown(
      `[click](javascript:alert('x')) <img src=x onerror=alert(1)>`
    );
    expect(html.toLowerCase()).not.toContain("javascript:");
    expect(html.toLowerCase()).not.toContain("onerror");
  });

  it("strips iframes and embeds", () => {
    const html = safeMarkdown(
      `<iframe src="https://evil.example"></iframe>\n<embed src="x">`
    );
    expect(html).not.toContain("<iframe");
    expect(html).not.toContain("<embed");
  });

  it("returns empty string for empty input", () => {
    expect(safeMarkdown("")).toBe("");
  });
});
