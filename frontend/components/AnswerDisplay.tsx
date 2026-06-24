import type { QueryResponse } from "@/types";
import CitationCard from "./CitationCard";
interface AnswerDisplayProps { response: QueryResponse; }
export default function AnswerDisplay({ response }: AnswerDisplayProps) {
  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-600">Answer</p>
        <p className="text-sm leading-relaxed text-gray-800 whitespace-pre-wrap">{response.answer}</p>
      </div>
      {response.citations.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sources ({response.citations.length})</p>
          {response.citations.map((c, i) => <CitationCard key={c.id} citation={c} index={i + 1} />)}
        </div>
      )}
    </div>
  );
}
