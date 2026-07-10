import { AlertTriangle, CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

type Status = "up" | "degraded" | "down" | null | undefined;

const styles = {
  up: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  degraded: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  down: "border-rose-500/20 bg-rose-500/10 text-rose-700 dark:text-rose-300",
  unknown: "border-slate-500/20 bg-slate-500/10 text-slate-600 dark:text-slate-300",
};

export function StatusBadge({ status, compact = false }: { status: Status; compact?: boolean }) {
  const { t } = useTranslation();
  const key = status ?? "unknown";
  const Icon =
    key === "up" ? CheckCircle2 : key === "degraded" ? AlertTriangle : key === "down" ? XCircle : CircleHelp;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[key]}`}
      aria-label={t(`status.${key}`)}
    >
      <Icon size={13} aria-hidden="true" />
      {!compact && t(`status.${key}`)}
    </span>
  );
}
