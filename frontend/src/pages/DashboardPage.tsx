import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowRight, Gauge, Server, ShieldAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "../api";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function DashboardPage() {
  const { t } = useTranslation();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard, refetchInterval: 15_000 });
  const services = useQuery({ queryKey: ["services"], queryFn: api.services, refetchInterval: 15_000 });
  const incidents = useQuery({ queryKey: ["incidents", "open"], queryFn: () => api.incidents(true), refetchInterval: 15_000 });

  if (dashboard.isPending || services.isPending || incidents.isPending) return <LoadingState />;
  if (dashboard.isError || services.isError || incidents.isError) return <ErrorState onRetry={() => void dashboard.refetch()} />;
  const data = dashboard.data;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader eyebrow={t("dashboard.eyebrow")} title={t("dashboard.title")} subtitle={t("dashboard.subtitle")} />
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Métricas principales">
        <MetricCard label={t("dashboard.total")} value={data.total_services} icon={Server} tone="blue" />
        <MetricCard label={t("dashboard.healthy")} value={data.up_services} detail={t("dashboard.healthDetail", { degraded: data.degraded_services, down: data.down_services })} icon={Activity} />
        <MetricCard label={t("dashboard.incidents")} value={data.active_incidents} icon={ShieldAlert} tone={data.active_incidents ? "rose" : "teal"} />
        <MetricCard label={t("dashboard.availability")} value={data.availability_24h == null ? "—" : `${data.availability_24h}%`} icon={Gauge} tone="amber" />
      </section>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <section>
          <div className="mb-3 flex items-center justify-between"><h2 className="m-0 text-lg font-semibold">{t("dashboard.fleet")}</h2><Link to="/services" className="text-sm font-semibold text-teal-600 hover:text-teal-500 dark:text-teal-300">{t("nav.services")} <ArrowRight className="inline" size={15} /></Link></div>
          {services.data.length === 0 ? (
            <EmptyState title={t("dashboard.empty")} action={<Link to="/services" className="btn-primary mt-3">{t("dashboard.addFirst")}</Link>} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {services.data.map((service) => (
                <Link to={`/services/${service.id}`} key={service.id} className="panel-hover p-5 text-inherit no-underline">
                  <div className="flex items-start justify-between gap-3"><div><p className="m-0 font-semibold">{service.name}</p><p className="mb-0 mt-1 max-w-[18rem] truncate font-mono text-[11px] text-slate-500">{service.url}</p></div><StatusBadge status={service.latest_status} compact /></div>
                  <div className="mt-5 flex items-end justify-between"><div><p className="m-0 text-xs text-slate-500">{t("services.availability")}</p><p className="mb-0 mt-1 text-xl font-bold">{service.availability_24h == null ? "—" : `${service.availability_24h}%`}</p></div><p className="m-0 text-xs text-slate-500">{service.last_latency_ms == null ? "—" : `${service.last_latency_ms} ms`}</p></div>
                </Link>
              ))}
            </div>
          )}
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between"><h2 className="m-0 text-lg font-semibold">{t("dashboard.latestIncidents")}</h2><Link to="/incidents" className="text-sm font-semibold text-teal-600 dark:text-teal-300">{t("common.view")}</Link></div>
          <div className="panel divide-y divide-slate-100 overflow-hidden dark:divide-slate-800">
            {incidents.data.length === 0 ? <p className="m-0 p-6 text-sm text-slate-500">{t("dashboard.quiet")}</p> : incidents.data.slice(0, 5).map((incident) => {
              const service = services.data.find((item) => item.id === incident.service_id);
              return <Link to="/incidents" key={incident.id} className="block p-4 text-inherit no-underline transition hover:bg-slate-50 dark:hover:bg-slate-800/50"><div className="flex items-center justify-between gap-3"><p className="m-0 text-sm font-semibold">{service?.name ?? `#${incident.service_id}`}</p><span className="h-2 w-2 rounded-full bg-rose-500" /></div><p className="mb-0 mt-1 text-xs text-slate-500">{formatDate(incident.started_at)}</p><p className="mb-0 mt-3 line-clamp-2 text-sm leading-5 text-slate-600 dark:text-slate-300">{incident.ai_summary ?? t("incidents.noSummary")}</p></Link>;
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
