"use client";
interface RepoFormProps { onSubmit: (githubUrl: string) => void; isLoading?: boolean; }
export default function RepoForm({ onSubmit, isLoading = false }: RepoFormProps) {
  return (
    <div className="flex flex-col gap-3">
      <input type="url" placeholder="https://github.com/owner/repo" disabled={isLoading}
        className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
      <button type="button" disabled={isLoading} onClick={() => {}}
        className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
        {isLoading ? "Indexing..." : "Index Repository"}
      </button>
    </div>
  );
}
