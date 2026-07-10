import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowLeft, Clock3, Gauge, Timer } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "../api";
import { ErrorState, LoadingState } from "../components/Feedback";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";

function dateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function ServiceDetailPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const serviceId = Number(useParams().serviceId);
  const [hours, setHours] = useState<24 | 168 | 720>(24);
  const services = useQuery({ queryKey: ["services"], queryFn: api.services });
  const checks = useQuery({ queryKey: ["checks", serviceId], queryFn: () => api.checks(serviceId), enabled: Number.isFinite(serviceId) });
  const timeline = useQuery({ queryKey: ["timeline", serviceId, hours], queryFn: () => api.timeline(serviceId, hours), enabled: Number.isFinite(serviceId) });
  const run = useMutation({ mutationFn: () => api.runCheck(serviceId), onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["checks", serviceId] }),
      queryClient.invalidateQueries({ queryKey: ["timeline", serviceId] }),
      queryClient.invalidateQueries({ queryKey: ["services"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    ]);
  } });

  if (services.isPending || checks.isPending || timeline.isPending) return <LoadingState />;
  const service = services.data?.find((item) => item.id === serviceId);
  if (!service || services.isError || checks.isError || timeline.isError) return <ErrorState />;
  const chartData = timeline.data.points.map((point) => ({ ...point, label: dateTime(point.bucket_start) }));
  const latencies = timeline.data.points.map((point) => point.average_latency_ms).filter((value): value is number => value != null);
  const averageLatency = latencies.length ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : null;

  return (
    <div className="mx-auto max-w-7xl">
      <Link to="/services" className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-teal-600 dark:hover:text-teal-300"><ArrowLeft size={16} />{t("detail.back")}</Link>
      <header className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><div className="mb-3 flex items-center gap-3"><StatusBadge status={service.latest_status} /><span className="font-mono text-xs text-slate-500">ID {service.id}</span></div><h1 className="m-0 text-3xl font-bold tracking-tight sm:text-4xl">{service.name}</h1><p className="mb-0 mt-2 break-all font-mono text-xs text-slate-500">{service.url}</p></div><button className="btn-primary" disabled={run.isPending} onClick={() => run.mutate()}><Activity size={18} />{run.isPending ? t("common.loading") : t("detail.checkNow")}</button></header>
      <section className="grid gap-4 sm:grid-cols-3"><MetricCard label={t("detail.availability")} value={service.availability_24h == null ? "—" : `${service.availability_24h}%`} icon={Gauge} /><MetricCard label={t("detail.latency")} value={averageLatency == null ? "—" : `${averageLatency} ms`} icon={Timer} tone="blue" /><MetricCard label={t("detail.interval")} value={`${service.check_interval_seconds}s`} detail={service.last_checked_at ? `${t("detail.last")}: ${dateTime(service.last_checked_at)}` : undefined} icon={Clock3} tone="amber" /></section>
      <section className="panel mt-7 p-5 sm:p-6"><div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><h2 className="m-0 text-lg font-semibold">{t("detail.history")}</h2><div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">{([[24, "detail.period24"], [168, "detail.period7"], [720, "detail.period30"]] as const).map(([value, label]) => <button key={value} onClick={() => setHours(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${hours === value ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white" : "text-slate-500"}`}>{t(label)}</button>)}</div></div>{chartData.length === 0 ? <div className="grid h-72 place-items-center text-sm text-slate-500">{t("detail.noData")}</div> : <div className="h-72 w-full"><ResponsiveContainer><ComposedChart data={chartData} margin={{ left: -20, right: 12 }}><defs><linearGradient id="availabilityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3}/><stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#64748b22" /><XAxis dataKey="label" tick={{ fontSize: 10 }} minTickGap={32} /><YAxis yAxisId="left" domain={[0, 100]} tick={{ fontSize: 10 }} /><YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12, color: "white" }} /><Area yAxisId="left" type="monotone" dataKey="availability_percent" name={`${t("detail.availability")} %`} stroke="#2dd4bf" fill="url(#availabilityFill)" strokeWidth={2} /><Line yAxisId="right" type="monotone" dataKey="average_latency_ms" name={`${t("services.latency")} ms`} stroke="#38bdf8" dot={false} strokeWidth={2} /></ComposedChart></ResponsiveContainer></div>}</section>
      <section className="panel mt-7 overflow-hidden"><div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800"><h2 className="m-0 text-lg font-semibold">{t("detail.recentChecks")}</h2></div><div className="overflow-x-auto"><table className="w-full text-left"><thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-800/60"><tr><th className="px-4 py-3">{t("detail.status")}</th><th className="px-4 py-3">{t("detail.date")}</th><th className="px-4 py-3">HTTP</th><th className="px-4 py-3">{t("services.latency")}</th></tr></thead><tbody>{checks.data.map((check) => <tr key={check.id}><td className="table-cell"><StatusBadge status={check.status} /></td><td className="table-cell">{dateTime(check.checked_at)}</td><td className="table-cell font-mono">{check.http_code ?? "—"}</td><td className="table-cell">{check.latency_ms == null ? "—" : `${check.latency_ms} ms`}</td></tr>)}</tbody></table></div></section>
    </div>
  );
}
