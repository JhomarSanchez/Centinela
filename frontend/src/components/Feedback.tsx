import { AlertCircle, LoaderCircle, Radar } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export function LoadingState() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-56 items-center justify-center gap-3 text-slate-500" role="status">
      <LoaderCircle className="animate-spin" size={20} /> {t("common.loading")}
    </div>
  );
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="panel flex min-h-48 flex-col items-center justify-center p-8 text-center">
      <AlertCircle className="mb-3 text-rose-500" size={28} />
      <p className="mt-0 text-sm text-slate-600 dark:text-slate-300">{t("common.loadError")}</p>
      {onRetry && <button className="btn-secondary" onClick={onRetry}>{t("common.retry")}</button>}
    </div>
  );
}

export function EmptyState({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="panel flex min-h-56 flex-col items-center justify-center p-8 text-center">
      <span className="mb-4 rounded-2xl bg-slate-100 p-4 text-slate-500 dark:bg-slate-800"><Radar size={30} /></span>
      <p className="mt-0 max-w-md text-sm text-slate-600 dark:text-slate-300">{title}</p>
      {action}
    </div>
  );
}
