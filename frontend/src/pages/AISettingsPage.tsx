import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CheckCircle2, Cloud, Cpu, KeyRound, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "../api";
import { ErrorState, LoadingState } from "../components/Feedback";
import { PageHeader } from "../components/PageHeader";
import type { AISettingsUpdate } from "../types";

const providers = [
  { id: "ollama", label: "Ollama", detail: "Local · privado", icon: Cpu },
  { id: "openai", label: "OpenAI", detail: "Responses API", icon: Sparkles },
  { id: "anthropic", label: "Anthropic", detail: "Claude Messages API", icon: Cloud },
] as const;

export function AISettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["ai-settings"], queryFn: api.aiSettings });
  const [form, setForm] = useState<AISettingsUpdate>({ provider: "ollama", model: "llama3.1:8b", summary_language: "es", enabled: true, api_key: null });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (settings.data) setForm({ provider: settings.data.provider, model: settings.data.model, summary_language: settings.data.summary_language, enabled: settings.data.enabled, api_key: null });
  }, [settings.data]);

  const save = useMutation({ mutationFn: api.saveAISettings, onSuccess: async () => { setMessage(t("common.save")); setError(null); setForm((value) => ({ ...value, api_key: null })); await queryClient.invalidateQueries({ queryKey: ["ai-settings"] }); }, onError: (value) => { setError(value instanceof ApiError && value.status === 503 ? t("ai.secretWarning") : value.message); setMessage(null); } });
  const test = useMutation({ mutationFn: api.testAISettings, onSuccess: (value) => { setMessage(`${t("ai.testOk")} · ${value.latency_ms} ms`); setError(null); }, onError: (value) => { setError(value.message); setMessage(null); } });
  const remove = useMutation({ mutationFn: api.deleteAICredential, onSuccess: async () => { setMessage(t("ai.remove")); await queryClient.invalidateQueries({ queryKey: ["ai-settings"] }); } });

  if (settings.isPending) return <LoadingState />;
  if (settings.isError) return <ErrorState onRetry={() => void settings.refetch()} />;
  const credentialOk = settings.data.credential_configured;
  const submit = (event: FormEvent) => { event.preventDefault(); save.mutate({ ...form, api_key: form.api_key || null }); };

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader eyebrow={t("ai.eyebrow")} title={t("ai.title")} subtitle={t("ai.subtitle")} />
      <div className="grid gap-6 lg:grid-cols-[1fr_0.45fr]">
        <form className="panel p-5 sm:p-7" onSubmit={submit}>
          <fieldset className="m-0 border-0 p-0"><legend className="mb-3 text-sm font-semibold">{t("ai.provider")}</legend><div className="grid gap-3 sm:grid-cols-3">{providers.map(({ id, label, detail, icon: Icon }) => <button type="button" key={id} onClick={() => setForm((value) => ({ ...value, provider: id, model: id === "ollama" ? "llama3.1:8b" : "" }))} className={`rounded-xl border p-4 text-left transition ${form.provider === id ? "border-teal-500 bg-teal-500/10 ring-2 ring-teal-500/10" : "border-slate-200 hover:border-slate-400 dark:border-slate-700"}`}><Icon className={form.provider === id ? "text-teal-500" : "text-slate-500"} size={21} /><p className="mb-0 mt-3 text-sm font-semibold">{label}</p><p className="mb-0 mt-1 text-xs text-slate-500">{detail}</p></button>)}</div></fieldset>
          <div className="mt-6"><label className="field-label" htmlFor="ai-model">{t("ai.model")}</label><input id="ai-model" className="field font-mono" value={form.model} onChange={(event) => setForm((value) => ({ ...value, model: event.target.value }))} placeholder={form.provider === "openai" ? "gpt-…" : form.provider === "anthropic" ? "claude-…" : "llama3.1:8b"} required /></div>
          {form.provider !== "ollama" && <div className="mt-4"><label className="field-label" htmlFor="ai-key">{t("ai.apiKey")}</label><div className="relative"><KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={17} /><input id="ai-key" className="field pl-10" type="password" value={form.api_key ?? ""} onChange={(event) => setForm((value) => ({ ...value, api_key: event.target.value }))} placeholder={settings.data.api_key_hint ? `••••••••${settings.data.api_key_hint}` : "sk-…"} autoComplete="off" /></div><p className="mb-0 mt-1.5 text-xs text-slate-500">{t("ai.optionalKey")}</p></div>}
          <div className="mt-4"><label className="field-label" htmlFor="ai-language">{t("ai.language")}</label><select id="ai-language" className="field" value={form.summary_language} onChange={(event) => setForm((value) => ({ ...value, summary_language: event.target.value as "es" | "en" }))}><option value="es">Español</option><option value="en">English</option></select></div>
          <label className="mt-5 flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700"><span><span className="block text-sm font-semibold">{t("ai.enabled")}</span><span className="mt-1 block text-xs text-slate-500">{t("ai.disabledNote")}</span></span><input type="checkbox" className="h-5 w-5 accent-teal-500" checked={form.enabled} onChange={(event) => setForm((value) => ({ ...value, enabled: event.target.checked }))} /></label>
          {message && <p className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-500/10 p-3 text-sm text-emerald-600 dark:text-emerald-300"><CheckCircle2 size={17} />{message}</p>}{error && <p role="alert" className="mt-4 rounded-xl bg-rose-500/10 p-3 text-sm text-rose-600 dark:text-rose-300">{error}</p>}
          <div className="mt-6 flex flex-wrap gap-3"><button className="btn-primary" disabled={save.isPending}><ShieldCheck size={17} />{save.isPending ? t("common.loading") : t("common.save")}</button><button type="button" className="btn-secondary" disabled={test.isPending || !credentialOk} onClick={() => test.mutate()}><Bot size={17} />{test.isPending ? t("common.loading") : t("ai.test")}</button>{settings.data.api_key_hint && <button type="button" className="btn-secondary text-rose-500" disabled={remove.isPending} onClick={() => remove.mutate()}><Trash2 size={16} />{t("ai.remove")}</button>}</div>
        </form>
        <aside className="space-y-4"><div className={`panel p-5 ${credentialOk ? "border-emerald-500/30" : "border-amber-500/30"}`}><p className="m-0 flex items-center gap-2 text-sm font-semibold">{credentialOk ? <CheckCircle2 className="text-emerald-500" size={18} /> : <KeyRound className="text-amber-500" size={18} />}{credentialOk ? t("ai.configured") : t("ai.notConfigured")}</p>{settings.data.api_key_hint && <p className="mb-0 mt-2 font-mono text-xs text-slate-500">••••••••{settings.data.api_key_hint}</p>}</div><div className="panel p-5"><p className="m-0 flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="text-teal-500" size={18} />{t("ai.privacyTitle")}</p><p className="mb-0 mt-3 text-sm leading-6 text-slate-500">{t("ai.disclosure")}</p></div></aside>
      </div>
    </div>
  );
}
