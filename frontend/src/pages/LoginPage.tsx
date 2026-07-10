import { Eye, EyeOff, LockKeyhole, Radar, ShieldCheck } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";

export function LoginPage({ onLogin }: { onLogin: () => Promise<unknown> }) {
  const { t, i18n } = useTranslation();
  const [apiKey, setApiKey] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(false);
    try {
      await api.login(apiKey);
      setApiKey("");
      await onLogin();
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const toggleLanguage = () => {
    const next = i18n.language.startsWith("es") ? "en" : "es";
    void i18n.changeLanguage(next);
    localStorage.setItem("centinela-language", next);
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#06101c] text-white">
      <div className="noise-grid absolute inset-0 opacity-80" />
      <div className="absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-teal-400/10 blur-3xl" />
      <div className="absolute -bottom-52 right-0 h-[38rem] w-[38rem] rounded-full bg-sky-500/10 blur-3xl" />
      <button className="absolute right-5 top-5 z-20 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold uppercase text-slate-300 hover:bg-slate-800" onClick={toggleLanguage}>
        {i18n.language.startsWith("es") ? "EN" : "ES"}
      </button>
      <div className="relative z-10 mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-14 lg:grid-cols-[1.15fr_0.85fr]">
        <section>
          <div className="mb-8 flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-teal-400 text-slate-950 shadow-glow"><Radar size={27} /></span>
            <div><p className="m-0 text-2xl font-bold">Centinela</p><p className="m-0 font-mono text-[10px] tracking-[0.24em] text-teal-300">SERVICE INTELLIGENCE</p></div>
          </div>
          <p className="eyebrow mb-4">{t("login.eyebrow")}</p>
          <h1 className="m-0 max-w-2xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">{t("login.title")}</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-400 sm:text-lg">{t("login.description")}</p>
          <div className="mt-10 grid max-w-lg gap-3 text-sm text-slate-300 sm:grid-cols-2">
            <div className="flex items-center gap-2"><ShieldCheck className="text-teal-300" size={18} />{t("login.featureData")}</div>
            <div className="flex items-center gap-2"><LockKeyhole className="text-teal-300" size={18} />{t("login.featureSecrets")}</div>
          </div>
        </section>
        <section className="rounded-3xl border border-slate-700/80 bg-slate-900/75 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
          <div className="mb-7"><p className="m-0 text-xl font-semibold">{t("login.adminTitle")}</p><p className="mb-0 mt-2 text-sm text-slate-400">{t("login.adminDescription")}</p></div>
          <form onSubmit={(event) => void submit(event)}>
            <label className="field-label !text-slate-300" htmlFor="api-key">{t("login.label")}</label>
            <div className="relative">
              <input id="api-key" className="field !border-slate-700 !bg-slate-950 pr-12 !text-white" type={show ? "text" : "password"} value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={t("login.placeholder")} autoComplete="current-password" required autoFocus />
              <button type="button" onClick={() => setShow((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white" aria-label="Mostrar clave">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>
            {error && <p role="alert" className="mb-0 mt-3 text-sm text-rose-300">{t("login.error")}</p>}
            <button className="btn-primary mt-5 w-full" disabled={loading || !apiKey}>{loading ? t("common.loading") : t("login.submit")}</button>
            <p className="mb-0 mt-4 text-center text-xs text-slate-500">{t("login.privacy")}</p>
          </form>
        </section>
      </div>
    </main>
  );
}
