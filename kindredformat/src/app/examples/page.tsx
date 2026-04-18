import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { loadContent } from "@/lib/content";

export default function Examples() {
  const md = loadContent("kaf-examples.md");
  return (
    <article>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
