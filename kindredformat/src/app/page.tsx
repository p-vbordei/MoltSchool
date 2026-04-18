import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { loadContent } from "@/lib/content";

export default function Home() {
  const md = loadContent("kaf-spec-0.1.md");
  return (
    <article>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
