import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p className="eyebrow mb-2 mt-0">{eyebrow}</p>
        <h1 className="m-0 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mb-0 mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">{subtitle}</p>
      </div>
      {action}
    </header>
  );
}
