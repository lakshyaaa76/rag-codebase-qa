import type { ChunkCitation } from "@/types";
interface CitationCardProps { citation: ChunkCitation; index: number; }
export default function CitationCard({ citation, index }: CitationCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-gray-100 bg-gray-50 px-4 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-semibold text-blue-700">[{index}]</span>
          <span className="truncate text-xs font-mono text-gray-700">{citation.file_path}</span>
          <span className="flex-shrink-0 text-xs text-gray-400">L{citation.start_line}-{citation.end_line}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {citation.language && <span className="rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600">{citation.language}</span>}
          <span className="text-xs text-gray-400">{(citation.score * 100).toFixed(0)}% match</span>
        </div>
      </div>
      <pre className="overflow-x-auto p-4 text-xs leading-relaxed text-gray-800">
        <code>{citation.content}</code>
      </pre>
    </div>
  );
}
