import type { RepoStatus } from "@/types";
interface StatusBadgeProps { status: RepoStatus; }
const STYLES: Record<RepoStatus, string> = {
  pending: "bg-gray-100 text-gray-600", indexing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700", failed: "bg-red-100 text-red-700",
};
const LABELS: Record<RepoStatus, string> = {
  pending: "Pending", indexing: "Indexing...", ready: "Ready", failed: "Failed",
};
export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {status === "indexing" && <span className="mr-1.5 h-2 w-2 animate-pulse rounded-full bg-yellow-500" />}
      {LABELS[status]}
    </span>
  );
}
