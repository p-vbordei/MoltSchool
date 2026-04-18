import { readFileSync } from "node:fs";
import { join } from "node:path";

/** Read a markdown file from `/content/` at build time. */
export function loadContent(filename: string): string {
  const path = join(process.cwd(), "content", filename);
  return readFileSync(path, "utf8");
}
