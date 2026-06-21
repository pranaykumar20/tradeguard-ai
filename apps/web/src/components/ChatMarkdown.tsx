"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-2 mt-4 first:mt-0 text-base font-semibold text-white">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2 mt-4 first:mt-0 text-[15px] font-semibold text-white">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-3.5 first:mt-0 text-sm font-semibold tracking-wide text-teal">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mb-1.5 mt-3 first:mt-0 text-sm font-semibold text-white/90">{children}</h4>
  ),
  p: ({ children }) => <p className="mb-2.5 last:mb-0 text-sm leading-relaxed text-white/90">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="text-white/80 italic">{children}</em>,
  ul: ({ children }) => <ul className="mb-3 space-y-2 pl-1 last:mb-0">{children}</ul>,
  ol: ({ children }) => (
    <ol className="mb-3 list-decimal space-y-2 pl-5 last:mb-0 marker:text-teal/70">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-sm leading-relaxed text-white/90 [&>p]:mb-0">{children}</li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-2 border-teal/40 bg-white/[0.03] py-2 pl-3 pr-2 text-sm italic text-white/75">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-white/10" />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-teal underline decoration-teal/40 underline-offset-2 hover:text-teal/80"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code className="block overflow-x-auto rounded-lg border border-white/10 bg-[#07111f] p-3 text-xs leading-relaxed text-teal/90">
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.85em] text-teal">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-3 overflow-x-auto rounded-lg border border-white/10 bg-[#07111f] p-3 last:mb-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-white/10 last:mb-0">
      <table className="w-full min-w-[240px] border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-white/[0.05] text-white/70">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-white/10">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-white/[0.02]">{children}</tr>,
  th: ({ children }) => (
    <th className="px-3 py-2 font-semibold uppercase tracking-wide text-[10px]">{children}</th>
  ),
  td: ({ children }) => <td className="px-3 py-2 text-white/85">{children}</td>,
};

type ChatMarkdownProps = {
  content: string;
  className?: string;
};

export function ChatMarkdown({ content, className = "" }: ChatMarkdownProps) {
  return (
    <div className={`tg-chat-md ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
