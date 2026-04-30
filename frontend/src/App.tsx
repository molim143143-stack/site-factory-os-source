import { useEffect, useMemo, useState } from "react";
import { RightDrawer } from "./components/RightDrawer";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { LoginPortalAnimation } from "./components/LoginPortalAnimation";
import { errors, sites, tasks } from "./data/mockData";
import { AdminBilling } from "./pages/AdminBilling";
import { BulkImport } from "./pages/BulkImport";
import { CMS } from "./pages/CMS";
import { Dashboard } from "./pages/Dashboard";
import { Deployments } from "./pages/Deployments";
import { DIYBuilder } from "./pages/DIYBuilder";
import { DNSDomain } from "./pages/DNSDomain";
import { ErrorCenter } from "./pages/ErrorCenter";
import { Languages } from "./pages/Languages";
import { LoginPage } from "./pages/LoginPage";
import { Membership } from "./pages/Membership";
import { PaymentLinks } from "./pages/PaymentLinks";
import { SEO } from "./pages/SEO";
import { SimplePage } from "./pages/SimplePage";
import { SiteDetail } from "./pages/SiteDetail";
import { Sites } from "./pages/Sites";
import { Tasks } from "./pages/Tasks";
import type { PageKey } from "./types";
import { useI18n } from "./i18n";
import { Z_INDEX } from "./constants/zIndex";

function App() {
  const { t } = useI18n();
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [currentSite, setCurrentSite] = useState(sites[0].site_id);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [builderFocusMode, setBuilderFocusMode] = useState(false);
  const [toast, setToast] = useState("System ready");
  const [authenticated, setAuthenticated] = useState(Boolean(localStorage.getItem("sfs_token")));
  const [booting, setBooting] = useState(false);
  const [username, setUsername] = useState("operator@sitefactory.ai");
  const taskCount = tasks.filter((task) => ["running", "queued", "retrying", "waiting_confirm"].includes(task.status)).length;
  const errorCount = errors.length;

  useEffect(() => {
    const expired = () => {
      setAuthenticated(false);
      setToast("AUTH_TOKEN_EXPIRED");
    };
    window.addEventListener("sfs-auth-expired", expired);
    return () => window.removeEventListener("sfs-auth-expired", expired);
  }, []);

  const page = useMemo(() => {
    const navigate = (key: string) => setActivePage(key as PageKey);
    const toastFn = (message: string) => setToast(message);
    switch (activePage) {
      case "dashboard":
        return <Dashboard onNavigate={navigate} onToast={toastFn} />;
      case "sites":
        return <Sites onSiteDetail={(siteId) => { setCurrentSite(siteId); setActivePage("siteDetail"); }} onNavigate={(page) => setActivePage(page as PageKey)} onSelectSite={setCurrentSite} onToast={toastFn} />;
      case "siteDetail":
        return <SiteDetail siteId={currentSite} onNavigate={navigate} onToast={toastFn} />;
      case "cms":
        return <CMS siteId={currentSite} onToast={toastFn} />;
      case "bulk":
        return <BulkImport siteId={currentSite} onToast={toastFn} />;
      case "builder":
        return <DIYBuilder siteId={currentSite} onToast={toastFn} focusMode={builderFocusMode} onFocusModeChange={setBuilderFocusMode} />;
      case "languages":
        return <Languages onToast={toastFn} />;
      case "seo":
        return <SEO siteId={currentSite} onToast={toastFn} />;
      case "dns":
        return <DNSDomain siteId={currentSite} onToast={toastFn} />;
      case "tasks":
        return <Tasks onToast={toastFn} />;
      case "errors":
        return <ErrorCenter onToast={toastFn} />;
      case "deployments":
        return <Deployments onToast={toastFn} />;
      case "payments":
        return <PaymentLinks onToast={toastFn} />;
      case "membership":
        return <Membership onToast={toastFn} />;
      case "adminBilling":
        return <AdminBilling onToast={toastFn} />;
      case "users":
        return <SimplePage title="Users & Roles" kicker="Access Control" description="Role-based access, Telegram operators, editors, viewers, and high-risk confirmation policies for production operations." />;
      case "settings":
        return <SimplePage title="Settings" kicker="System Tuning" description="Environment variables, API providers, deployment defaults, audit retention, and notification channels live here." />;
      default:
        return <Dashboard onNavigate={navigate} onToast={toastFn} />;
    }
  }, [activePage, builderFocusMode, currentSite]);

  if (!authenticated && !booting) {
    return <LoginPage onLogin={(name) => { setUsername(name); setBooting(true); }} onToast={setToast} />;
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-void text-textMain">
      {booting && <LoginPortalAnimation username={username} plan="Pro" onDone={() => { setBooting(false); setAuthenticated(true); setToast("Portal boot complete"); }} />}
      <div className="fixed inset-0 -z-10 grid-bg" />
      <div className="fixed left-1/4 top-0 -z-10 h-80 w-80 rounded-full bg-neon/10 blur-3xl" />
      <div className="fixed bottom-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-plasma/10 blur-3xl" />
      {!builderFocusMode && <Sidebar active={activePage} onNavigate={setActivePage} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />}
      <div className={builderFocusMode ? "" : `lg:pl-[260px] ${drawerOpen ? "xl:pr-[380px]" : "xl:pr-[50px]"}`}>
        {!builderFocusMode && <Topbar currentSite={currentSite} onSiteChange={setCurrentSite} onMenu={() => setSidebarOpen(true)} onToast={setToast} onNavigate={(page) => setActivePage(page as PageKey)} taskCount={taskCount} errorCount={errorCount} />}
        <main className={builderFocusMode ? "min-h-screen overflow-x-hidden p-3 pb-10" : "mx-auto max-w-[1680px] px-3 py-4 pb-24 sm:px-5 lg:py-6"}>{page}</main>
      </div>
      {!builderFocusMode && <RightDrawer open={drawerOpen} onToggle={() => setDrawerOpen(!drawerOpen)} />}
      {!builderFocusMode && <div className="fixed bottom-20 left-1/2 -translate-x-1/2 rounded-full border border-neon/30 bg-[#111827]/90 px-4 py-2 text-sm text-neon shadow-neon backdrop-blur-xl lg:bottom-5" style={{ zIndex: Z_INDEX.toast }}>
        {t(toast)}
      </div>}
      {!builderFocusMode && <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-white/10 bg-[#0A0F1C]/95 p-2 backdrop-blur-xl lg:hidden">
        {(["dashboard", "sites", "bulk", "tasks", "errors"] as PageKey[]).map((key) => (
          <button key={key} onClick={() => setActivePage(key)} className={`rounded-xl px-1 py-2 text-xs ${activePage === key ? "bg-neon/10 text-neon" : "text-textWeak"}`}>
            {t(`nav.${key === "bulk" ? "bulk_import" : key === "errors" ? "errors" : key}`)}
          </button>
        ))}
      </nav>}
    </div>
  );
}

export default App;
