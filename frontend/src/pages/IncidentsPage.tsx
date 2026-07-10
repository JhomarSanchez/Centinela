import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CheckCircle2, Clock3, Code2, RefreshCw, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { Modal } from "../components/Modal";
import { PageHeader } from "../components/PageHeader";
import type { Incident } from "../types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function duration(incident: Incident) {
  const end = incident.resolved_at ? new Date(incident.resolved_at).getTime() : Date.now();
  const minutes = Math.max(1, Math.round((end - new Date(incident.started_at).getTime()) / 60000));
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

export function IncidentsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<"all" | "open" | "resolved">("all");
  const [selected, setSelected] = useState<Incident | null>(null);
  const [showContext, setShowContext] = useState(false);
  const incidents = useQuery({ queryKey: ["incidents", "all"], queryFn: () => api.incidents() });
  const services = useQuery({ queryKey: ["services"], queryFn: api.services });
  const context = useQuery({ queryKey: ["incident-context", selected?.id], queryFn: () => api.incidentContext(selected!.id), enabled: Boolean(selected && showContext) });
  const retry = useMutation({ mutationFn: (id: number) => api.retryIncident(id), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["incidents"] }); } });

  const filtered = useMemo(() => incidents.data?.filter((incident) => filter === "all" || (filter === "open" ? !incident.resolved_at : Boolean(incident.resolved_at))) ?? [], [filter, incidents.data]);
  if (incidents.isPending || services.isPending) return <LoadingState />;
  if (incidents.isError || services.isError) return <ErrorState onRetry={() => void incidents.refetch()} />;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader eyebrow={t("incidents.eyebrow")} title={t("incidents.title")} subtitle={t("incidents.subtitle")} />
      <div className="mb-5 inline-flex rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800">{(["all", "open", "resolved"] as const).map((value) => <button key={value} onClick={() => setFilter(value)} className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${filter === value ? "bg-white shadow-sm dark:bg-slate-700" : "text-slate-500"}`}>{t(`common.${value}`)}</button>)}</div>
      {filtered.length === 0 ? <EmptyState title={t("incidents.empty")} /> : <div className="space-y-4">{filtered.map((incident) => {
        const service = services.data.find((item) => item.id === incident.service_id);
        const open = !incident.resolved_at;
        return <article key={incident.id} className="panel-hover overflow-hidden"><div className={`h-1 ${open ? "bg-rose-500" : "bg-emerald-500"}`} /><div className="p-5 sm:p-6"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><div className="flex items-center gap-2"><span className={`rounded-lg p-2 ${open ? "bg-rose-500/10 text-rose-500" : "bg-emerald-500/10 text-emerald-500"}`}>{open ? <TriangleAlert size={18} /> : <CheckCircle2 size={18} />}</span><div><h2 className="m-0 text-lg font-semibold">{service?.name ?? `${t("incidents.service")} #${incident.service_id}`}</h2><p className="mb-0 mt-1 font-mono text-xs text-slate-500">INC-{String(incident.id).padStart(4, "0")}</p></div></div></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${open ? "bg-rose-500/10 text-rose-500" : "bg-emerald-500/10 text-emerald-500"}`}>{open ? t("common.open") : t("common.resolved")}</span></div><div className="mt-5 grid gap-5 border-t border-slate-100 pt-5 dark:border-slate-800 lg:grid-cols-[0.35fr_1fr]"><div className="space-y-3 text-sm text-slate-500"><p className="m-0 flex items-center gap-2"><Clock3 size={15} />{formatDate(incident.started_at)}</p><p className="m-0">{t("incidents.duration")}: <strong className="text-slate-700 dark:text-slate-200">{duration(incident)}</strong></p><p className="m-0">IA: <strong className="uppercase text-slate-700 dark:text-slate-200">{incident.ai_provider ?? "—"}</strong></p></div><div><p className="mb-2 mt-0 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500"><Bot size={15} />{t("incidents.ai")}</p><p className="m-0 text-sm leading-6 text-slate-700 dark:text-slate-200">{incident.ai_summary ?? t("incidents.noSummary")}</p><div className="mt-4 flex flex-wrap gap-2"><button className="btn-secondary !min-h-9 !px-3 !py-1.5" onClick={() => { setSelected(incident); setShowContext(false); }}>{t("common.view")}</button>{incident.ai_status !== "processing" && <button className="btn-secondary !min-h-9 !px-3 !py-1.5" disabled={retry.isPending} onClick={() => retry.mutate(incident.id)}><RefreshCw size={14} />{t("incidents.regenerate")}</button>}</div></div></div></div></article>;
      })}</div>}
      <Modal open={Boolean(selected)} onOpenChange={(open) => { if (!open) { setSelected(null); setShowContext(false); } }} title={selected ? `INC-${String(selected.id).padStart(4, "0")}` : t("incidents.incident")} description={selected ? `${services.data.find((item) => item.id === selected.service_id)?.name ?? ""} · ${formatDate(selected.started_at)}` : undefined}>{selected && <div className="space-y-5"><div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-950"><p className="mb-2 mt-0 flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><Bot size={15} />{t("incidents.ai")}</p><p className="m-0 text-sm leading-6">{selected.ai_summary ?? t("incidents.noSummary")}</p></div><dl className="grid grid-cols-2 gap-3 text-sm"><div><dt className="text-slate-500">{t("incidents.aiStatus")}</dt><dd className="m-0 mt-1 font-semibold">{selected.ai_status}</dd></div><div><dt className="text-slate-500">{t("incidents.model")}</dt><dd className="m-0 mt-1 font-semibold">{selected.ai_model ?? "—"}</dd></div><div><dt className="text-slate-500">{t("incidents.attempts")}</dt><dd className="m-0 mt-1 font-semibold">{selected.ai_attempt_count}</dd></div><div><dt className="text-slate-500">{t("incidents.aiLatency")}</dt><dd className="m-0 mt-1 font-semibold">{selected.ai_latency_ms == null ? "—" : `${selected.ai_latency_ms} ms`}</dd></div></dl><button className="btn-secondary w-full" onClick={() => setShowContext((value) => !value)}><Code2 size={16} />{t("incidents.context")}</button>{showContext && <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-300">{context.isPending ? t("common.loading") : context.data?.raw_context ?? "—"}</pre>}</div>}</Modal>
    </div>
  );
}
