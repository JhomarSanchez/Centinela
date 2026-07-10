import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Radar } from "lucide-react";
import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api";
import { AppShell } from "./components/AppShell";
import { LoginPage } from "./pages/LoginPage";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })),
);
const ServicesPage = lazy(() =>
  import("./pages/ServicesPage").then((module) => ({ default: module.ServicesPage })),
);
const ServiceDetailPage = lazy(() =>
  import("./pages/ServiceDetailPage").then((module) => ({ default: module.ServiceDetailPage })),
);
const IncidentsPage = lazy(() =>
  import("./pages/IncidentsPage").then((module) => ({ default: module.IncidentsPage })),
);
const AISettingsPage = lazy(() =>
  import("./pages/AISettingsPage").then((module) => ({ default: module.AISettingsPage })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false },
  },
});

function RoutedApp() {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["session"], queryFn: api.session, retry: false });

  useEffect(() => {
    const expire = () => client.setQueryData(["session"], null);
    window.addEventListener("centinela:logout", expire);
    return () => window.removeEventListener("centinela:logout", expire);
  }, [client]);

  if (session.isPending) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#07101d] text-teal-300" role="status">
        <div className="text-center"><Radar className="mx-auto mb-4" size={38} /><LoaderCircle className="mx-auto animate-spin" /></div>
      </div>
    );
  }

  if (!session.data) {
    return <LoginPage onLogin={() => session.refetch()} />;
  }

  const logout = async () => {
    await api.logout();
    client.clear();
    client.setQueryData(["session"], null);
  };

  return (
    <Suspense fallback={<div className="grid min-h-64 place-items-center"><LoaderCircle className="animate-spin text-teal-500" /></div>}>
    <Routes>
      <Route element={<AppShell onLogout={logout} />}>
        <Route index element={<DashboardPage />} />
        <Route path="services" element={<ServicesPage />} />
        <Route path="services/:serviceId" element={<ServiceDetailPage />} />
        <Route path="incidents" element={<IncidentsPage />} />
        <Route path="settings/ai" element={<AISettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </Suspense>
  );
}

export default function App() {
  return <QueryClientProvider client={queryClient}><RoutedApp /></QueryClientProvider>;
}
