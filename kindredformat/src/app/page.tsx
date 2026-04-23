import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { loadContent } from "@/lib/content";

export default function Home() {
  const md = loadContent("kaf-spec-0.1.md");
  return (
    <article>
      <aside className="plain-words">
        <p>
          <strong>In plain words:</strong> KAF is the file format for pages
          in a team&apos;s shared notebook for AI. Every page is signed by the
          teammate who wrote it, timestamped, and can expire if no one keeps
          it fresh. The technical spec follows.
        </p>
      </aside>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
