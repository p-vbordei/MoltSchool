/**
 * Safe markdown rendering for artifact content.
 *
 * Pipeline: marked (markdown -> HTML) -> sanitize-html (strict allow-list).
 *
 * Deviation from plan: plan called for DOMPurify, but isomorphic-dompurify
 * pulls jsdom which fails to bundle under Next.js 15 (missing internal CSS
 * file during page-data collection). sanitize-html is a pure-JS allow-list
 * sanitizer with equivalent XSS guarantees for our usecase. It strips any
 * element/attribute not on the allow-list, including all <script>, inline
 * event handlers, javascript: URLs, <iframe>, <style>, <object>, <embed>,
 * and <svg>. We also filter href/src schemes to http(s)/mailto.
 */

import sanitizeHtml from "sanitize-html";
import { marked } from "marked";

const SANITIZE_CONFIG: sanitizeHtml.IOptions = {
  allowedTags: [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "em", "b", "i", "u", "del", "s",
    "ul", "ol", "li",
    "blockquote", "code", "pre",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
  ],
  allowedAttributes: {
    a: ["href", "title", "rel"],
    img: ["src", "alt", "title"],
    code: ["class"], // for language-xxx highlighting
    pre: ["class"],
  },
  allowedSchemes: ["http", "https", "mailto"],
  allowedSchemesAppliedToAttributes: ["href", "src"],
  disallowedTagsMode: "discard",
  transformTags: {
    a: sanitizeHtml.simpleTransform("a", { rel: "noopener noreferrer ugc" }),
  },
};

export function safeMarkdown(content: string): string {
  if (!content) return "";
  const raw = marked.parse(content, { async: false, breaks: true }) as string;
  return sanitizeHtml(raw, SANITIZE_CONFIG);
}
