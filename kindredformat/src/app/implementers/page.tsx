import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { loadContent } from "@/lib/content";

export default function Implementers() {
  const md = loadContent("kaf-implementers-guide.md");
  return (
    <article>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
