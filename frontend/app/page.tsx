"use client";

import RepoForm from "@/components/RepoForm";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-gray-900">
          Ask questions about any GitHub repository
        </h1>
        <p className="text-sm text-gray-500">
          Paste a public GitHub URL to index the codebase, then ask natural-language questions.
        </p>
      </div>
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <p className="mb-4 text-sm font-medium text-gray-700">GitHub Repository URL</p>
        {/* TODO (Phase 8): wire submission, polling, and navigation */}
        <RepoForm onSubmit={(_url) => {}} />
      </div>
    </div>
  );
}
