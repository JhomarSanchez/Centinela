import {
  Bot,
  ExternalLink,
  Gauge,
  Languages,
  LogOut,
  Menu,
  Moon,
  Radar,
  Server,
  Sun,
  TriangleAlert,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

const nav = [
  { to: "/", label: "nav.overview", icon: Gauge, end: true },
  { to: "/services", label: "nav.services", icon: Server },
  { to: "/incidents", label: "nav.incidents", icon: TriangleAlert },
  { to: "/settings/ai", label: "nav.ai", icon: Bot },
];

export function AppShell({ onLogout }: { onLogout: () => Promise<void> }) {
  const { t, i18n } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem("centinela-theme") !== "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("centinela-theme", dark ? "dark" : "light");
  }, [dark]);

  const setLanguage = () => {
    const next = i18n.language.startsWith("es") ? "en" : "es";
    void i18n.changeLanguage(next);
    localStorage.setItem("centinela-language", next);
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 px-5 py-6">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-400 text-slate-950 shadow-glow">
          <Radar size={22} aria-hidden="true" />
        </span>
        <div><p className="m-0 text-lg font-bold">{t("app.name")}</p><p className="m-0 text-[11px] text-slate-400">CONTROL CENTER</p></div>
      </div>
      <nav className="flex-1 space-y-1 px-3" aria-label="Principal">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                isActive ? "bg-teal-400/10 text-teal-300" : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`
            }
          ><Icon size={18} />{t(label)}</NavLink>
        ))}
      </nav>
      <div className="space-y-1 border-t border-slate-800 p-3">
        <a href="http://localhost:3000" target="_blank" rel="noreferrer" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white">
          <ExternalLink size={17} />{t("nav.grafana")}
        </a>
        <button onClick={() => void onLogout()} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white">
          <LogOut size={17} />{t("nav.logout")}
        </button>
      </div>
    </div>
  );

  return (
    <div className="app-background min-h-screen bg-slate-50 text-slate-900 dark:bg-[#07101d] dark:text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-800 bg-[#091321] lg:block">{sidebar}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/70" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} />
          <aside className="relative h-full w-72 bg-[#091321] text-white">{sidebar}<button className="absolute right-4 top-4" onClick={() => setMobileOpen(false)}><X /></button></aside>
        </div>
      )}
      <div className="lg:pl-64">
        <div className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/80 px-4 backdrop-blur-xl dark:border-slate-800 dark:bg-[#07101d]/80 sm:px-8">
          <button className="btn-secondary !min-h-9 !p-2 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menú"><Menu size={19} /></button>
          <p className="hidden text-xs text-slate-500 sm:block">{t("app.tagline")}</p>
          <div className="ml-auto flex items-center gap-2">
            <button className="btn-secondary !min-h-9 !p-2" onClick={setLanguage} aria-label="Cambiar idioma"><Languages size={18} /><span className="text-xs uppercase">{i18n.language.slice(0, 2)}</span></button>
            <button className="btn-secondary !min-h-9 !p-2" onClick={() => setDark((value) => !value)} aria-label="Cambiar tema">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
          </div>
        </div>
        <main className="noise-grid min-h-[calc(100vh-4rem)] px-4 py-7 sm:px-8 lg:px-10"><Outlet /></main>
      </div>
    </div>
  );
}
