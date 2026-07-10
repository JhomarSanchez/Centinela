import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, MoreHorizontal, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "../api";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { Modal } from "../components/Modal";
import { PageHeader } from "../components/PageHeader";
import { ServiceDialog } from "../components/ServiceDialog";
import { StatusBadge } from "../components/StatusBadge";
import type { Service, ServiceCreate } from "../types";

export function ServicesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const services = useQuery({ queryKey: ["services"], queryFn: api.services });
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Service | null>(null);
  const [deleting, setDeleting] = useState<Service | null>(null);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["services"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    ]);
  };
  const save = useMutation({
    mutationFn: async (payload: ServiceCreate) => editing ? api.updateService(editing.id, payload) : api.createService(payload),
    onSuccess: async () => { setDialogOpen(false); setEditing(null); await refresh(); },
  });
  const remove = useMutation({ mutationFn: (id: number) => api.deleteService(id), onSuccess: async () => { setDeleting(null); await refresh(); } });
  const check = useMutation({ mutationFn: (id: number) => api.runCheck(id), onSuccess: refresh });

  const filtered = useMemo(() => services.data?.filter((service) => `${service.name} ${service.url}`.toLowerCase().includes(search.toLowerCase())) ?? [], [search, services.data]);
  if (services.isPending) return <LoadingState />;
  if (services.isError) return <ErrorState onRetry={() => void services.refetch()} />;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader eyebrow={t("services.eyebrow")} title={t("services.title")} subtitle={t("services.subtitle")} action={<button className="btn-primary" onClick={() => { setEditing(null); setDialogOpen(true); }}><Plus size={18} />{t("services.add")}</button>} />
      <div className="panel mb-4 flex items-center gap-3 px-4 py-3"><Search size={18} className="text-slate-400" /><input className="w-full border-0 bg-transparent text-sm outline-none" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("services.search")} aria-label={t("services.search")} /></div>
      {filtered.length === 0 ? <EmptyState title={t("services.empty")} /> : (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 dark:bg-slate-800/60"><tr><th className="px-4 py-3">{t("services.name")}</th><th className="px-4 py-3">{t("services.latest")}</th><th className="px-4 py-3">{t("services.availability")}</th><th className="px-4 py-3">{t("services.latency")}</th><th className="px-4 py-3 text-right">{t("services.actions")}</th></tr></thead>
              <tbody>{filtered.map((service) => <tr key={service.id} className="transition hover:bg-slate-50/70 dark:hover:bg-slate-800/30"><td className="table-cell"><Link to={`/services/${service.id}`} className="font-semibold text-slate-900 hover:text-teal-600 dark:text-white dark:hover:text-teal-300">{service.name}</Link><p className="mb-0 mt-1 max-w-md truncate font-mono text-[11px] text-slate-500">{service.url}</p></td><td className="table-cell"><StatusBadge status={service.latest_status} /></td><td className="table-cell font-semibold">{service.availability_24h == null ? "—" : `${service.availability_24h}%`}</td><td className="table-cell">{service.last_latency_ms == null ? "—" : `${service.last_latency_ms} ms`}</td><td className="table-cell"><div className="flex justify-end gap-1"><button className="rounded-lg p-2 text-slate-500 hover:bg-teal-500/10 hover:text-teal-600" title={t("services.checkNow")} onClick={() => check.mutate(service.id)}><Activity size={17} /></button><button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" title={t("common.edit")} onClick={() => { setEditing(service); setDialogOpen(true); }}><Pencil size={17} /></button><button className="rounded-lg p-2 text-slate-500 hover:bg-rose-500/10 hover:text-rose-500" title={t("common.delete")} onClick={() => setDeleting(service)}><Trash2 size={17} /></button><Link to={`/services/${service.id}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><MoreHorizontal size={17} /></Link></div></td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}
      <ServiceDialog open={dialogOpen} onOpenChange={setDialogOpen} service={editing} submitting={save.isPending} onSubmit={async (payload) => { await save.mutateAsync(payload); }} />
      <Modal open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)} title={t("services.deleteTitle")} description={t("services.deleteText")}><div className="flex justify-end gap-3"><button className="btn-secondary" onClick={() => setDeleting(null)}>{t("common.cancel")}</button><button className="btn-danger" disabled={remove.isPending} onClick={() => deleting && remove.mutate(deleting.id)}><Trash2 size={17} />{t("common.delete")}</button></div></Modal>
    </div>
  );
}
