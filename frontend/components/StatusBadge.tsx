import type { RepoStatus } from "@/types";

interface StatusBadgeProps {
  status: RepoStatus;
}

const CONFIG: Record<RepoStatus, { color: string; glow: string; label: string; dot: string }> = {
  pending:  { color: "text-terminal-amber", glow: "",                         label: "PENDING",   dot: "bg-terminal-amber" },
  indexing: { color: "text-terminal-amber", glow: "",                         label: "INDEXING",  dot: "bg-terminal-amber animate-pulse-slow" },
  ready:    { color: "text-terminal-green", glow: "text-glow-green",          label: "READY",     dot: "bg-terminal-green" },
  failed:   { color: "text-terminal-red",   glow: "",                         label: "FAILED",    dot: "bg-terminal-red" },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const { color, glow, label, dot } = CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-widest ${color} ${glow}`}>
      <span className={`h-1.5 w-1.5 ${dot}`} />
      {label}
    </span>
  );
}