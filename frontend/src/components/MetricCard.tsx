import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "teal",
}: {
  label: string;
  value: string | number;
  detail?: string;
  icon: LucideIcon;
  tone?: "teal" | "blue" | "rose" | "amber";
}) {
  const tones = {
    teal: "bg-teal-500/10 text-teal-600 dark:text-teal-300",
    blue: "bg-sky-500/10 text-sky-600 dark:text-sky-300",
    rose: "bg-rose-500/10 text-rose-600 dark:text-rose-300",
    amber: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
  };
  return (
    <article className="panel p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="m-0 text-sm text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mb-0 mt-2 text-3xl font-bold tracking-tight">{value}</p>
          {detail && <p className="mb-0 mt-2 text-xs text-slate-500">{detail}</p>}
        </div>
        <span className={`rounded-xl p-2.5 ${tones[tone]}`}><Icon size={20} aria-hidden="true" /></span>
      </div>
    </article>
  );
}
