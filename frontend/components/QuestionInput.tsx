"use client";
interface QuestionInputProps { onSubmit: (question: string) => void; isLoading?: boolean; disabled?: boolean; }
export default function QuestionInput({ onSubmit, isLoading = false, disabled = false }: QuestionInputProps) {
  return (
    <div className="flex gap-2">
      <input type="text" placeholder="Ask a question about this codebase..." disabled={isLoading || disabled}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
      <button type="button" disabled={isLoading || disabled} onClick={() => {}}
        className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors whitespace-nowrap">
        {isLoading ? "Thinking..." : "Ask"}
      </button>
    </div>
  );
}
