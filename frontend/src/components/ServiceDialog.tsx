import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import type { Service, ServiceCreate } from "../types";
import { Modal } from "./Modal";

const schema = z.object({
  name: z.string().trim().min(1).max(200),
  url: z.string().url(),
  check_interval_seconds: z.number().int().min(5).max(86400),
});

type FormValues = z.infer<typeof schema>;

export function ServiceDialog({
  open,
  onOpenChange,
  service,
  submitting,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  service?: Service | null;
  submitting: boolean;
  onSubmit: (payload: ServiceCreate) => Promise<void>;
}) {
  const { t } = useTranslation();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", url: "", check_interval_seconds: 60 },
  });

  useEffect(() => {
    reset(service ? {
      name: service.name,
      url: service.url,
      check_interval_seconds: service.check_interval_seconds,
    } : { name: "", url: "", check_interval_seconds: 60 });
  }, [service, reset, open]);

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={service ? t("common.edit") : t("services.add")} description={t("services.subtitle")}>
      <form className="space-y-4" onSubmit={handleSubmit(async (values) => onSubmit(values))}>
        <div><label className="field-label" htmlFor="service-name">{t("services.name")}</label><input id="service-name" className="field" {...register("name")} autoFocus />{errors.name && <p className="mt-1 text-xs text-rose-500">{t("services.nameRequired")}</p>}</div>
        <div><label className="field-label" htmlFor="service-url">{t("services.url")}</label><input id="service-url" className="field font-mono" placeholder="https://example.com/health" {...register("url")} />{errors.url && <p className="mt-1 text-xs text-rose-500">{t("services.urlInvalid")}</p>}</div>
        <div><label className="field-label" htmlFor="service-interval">{t("services.interval")}</label><input id="service-interval" className="field" type="number" min={5} max={86400} {...register("check_interval_seconds", { valueAsNumber: true })} /></div>
        <div className="flex justify-end gap-3 pt-2"><button type="button" className="btn-secondary" onClick={() => onOpenChange(false)}>{t("common.cancel")}</button><button className="btn-primary" disabled={submitting}>{submitting ? t("common.loading") : t("common.save")}</button></div>
      </form>
    </Modal>
  );
}
