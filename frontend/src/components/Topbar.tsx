import { Bell, Bug, Menu, Plus, Search, UserCircle } from "lucide-react";
import { useRef, useState } from "react";
import { clearSession } from "../api/client";
import { Z_INDEX } from "../constants/zIndex";
import { sites } from "../data/mockData";
import { languageOptions, type LanguageCode, useI18n } from "../i18n";
import { PortalMenu } from "./floating/PortalMenu";
import { NeonButton } from "./NeonButton";

type Props = {
  currentSite: string;
  onSiteChange: (id: string) => void;
  onMenu: () => void;
  onToast: (message: string) => void;
  onNavigate: (page: "sites" | "cms" | "bulk") => void;
  taskCount: number;
  errorCount: number;
};

export function Topbar({ currentSite, onSiteChange, onMenu, onToast, onNavigate, taskCount, errorCount }: Props) {
  const { language, setLanguage, t } = useI18n();
  const [openMenu, setOpenMenu] = useState<"" | "site" | "language" | "quick" | "tasks" | "errors" | "user">("");
  const siteRef = useRef<HTMLButtonElement | null>(null);
  const languageRef = useRef<HTMLButtonElement | null>(null);
  const quickRef = useRef<HTMLButtonElement | null>(null);
  const tasksRef = useRef<HTMLButtonElement | null>(null);
  const errorsRef = useRef<HTMLButtonElement | null>(null);
  const userRef = useRef<HTMLButtonElement | null>(null);
  const currentSiteName = sites.find((site) => site.site_id === currentSite)?.alias || currentSite;
  const close = () => setOpenMenu("");
  return (
    <header className="sticky top-0 flex h-16 items-center gap-3 border-b border-white/10 bg-void/70 px-3 backdrop-blur-2xl lg:px-5" style={{ zIndex: Z_INDEX.header }}>
      <button className="rounded-lg border border-white/10 bg-white/5 p-2 text-textMain lg:hidden" onClick={onMenu}>
        <Menu size={20} />
      </button>
      <button ref={siteRef} className="h-10 max-w-[170px] truncate rounded-lg border border-neon/20 bg-[#101827] px-3 text-left text-sm text-textMain outline-none focus:border-neon sm:max-w-[260px]" onClick={() => setOpenMenu(openMenu === "site" ? "" : "site")}>
        {currentSiteName}
      </button>
      <PortalMenu open={openMenu === "site"} anchor={siteRef.current} onClose={close} width={280}>
        <p className="px-3 py-2 text-xs uppercase tracking-[0.18em] text-textWeak">{t("topbar.current_site")}</p>
        {sites.map((site) => (
          <button key={site.site_id} className={`w-full rounded-xl px-3 py-2 text-left hover:bg-neon/10 ${site.site_id === currentSite ? "text-neon" : "text-textMain"}`} onClick={() => { onSiteChange(site.site_id); close(); }}>
            <span className="block font-bold">{site.alias}</span>
            <span className="block font-mono text-xs text-textWeak">{site.site_id}</span>
          </button>
        ))}
      </PortalMenu>

      <label className="hidden h-10 flex-1 items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 text-textWeak md:flex">
        <Search size={17} />
        <input className="w-full bg-transparent text-sm text-textMain outline-none placeholder:text-textWeak" placeholder={t("topbar.global_search")} />
      </label>

      <NeonButton ref={quickRef as any} className="hidden sm:inline-flex" onClick={() => setOpenMenu(openMenu === "quick" ? "" : "quick")}>
        <Plus size={16} />
        {t("topbar.quick_create")}
      </NeonButton>
      <PortalMenu open={openMenu === "quick"} anchor={quickRef.current} onClose={close} width={230}>
        <button data-testid="quick-create-site" className="w-full rounded-xl px-3 py-2 text-left text-textMain hover:bg-neon/10 hover:text-neon" onClick={() => { onNavigate("sites"); onToast("topbar.create_site"); close(); }}>{t("topbar.create_site")}</button>
        <button data-testid="quick-new-article" className="w-full rounded-xl px-3 py-2 text-left text-textMain hover:bg-neon/10 hover:text-neon" onClick={() => { onNavigate("cms"); onToast("topbar.new_article"); close(); }}>{t("topbar.new_article")}</button>
        <button data-testid="quick-bulk-import" className="w-full rounded-xl px-3 py-2 text-left text-textMain hover:bg-neon/10 hover:text-neon" onClick={() => { onNavigate("bulk"); onToast("topbar.bulk_import"); close(); }}>{t("topbar.bulk_import")}</button>
      </PortalMenu>
      <button
        ref={languageRef}
        className="h-10 rounded-lg border border-neon/20 bg-[#101827] px-2 text-sm text-textMain outline-none focus:border-neon"
        aria-label={t("topbar.language")}
        onClick={() => setOpenMenu(openMenu === "language" ? "" : "language")}
      >
        {language}
      </button>
      <PortalMenu open={openMenu === "language"} anchor={languageRef.current} onClose={close} width={230}>
        {languageOptions.map((item) => (
          <button key={item.code} className={`w-full rounded-xl px-3 py-2 text-left hover:bg-neon/10 ${item.code === language ? "text-neon" : "text-textMain"}`} onClick={() => { setLanguage(item.code as LanguageCode); close(); }}>
            {item.code} · {item.name}
          </button>
        ))}
      </PortalMenu>
      <button ref={tasksRef} aria-label={t("topbar.tasks")} className="relative rounded-lg border border-white/10 bg-white/5 p-2 text-neon hover:shadow-neon" onClick={() => setOpenMenu(openMenu === "tasks" ? "" : "tasks")}>
        <Bell size={19} />
        <span className="absolute -right-1 -top-1 rounded-full bg-neon px-1.5 text-[10px] font-bold text-void">{taskCount}</span>
      </button>
      <PortalMenu open={openMenu === "tasks"} anchor={tasksRef.current} onClose={close} width={260}>
        <p className="px-3 py-2 font-bold text-neon">{t("topbar.tasks")}</p>
        <button className="w-full rounded-xl px-3 py-2 text-left hover:bg-neon/10" onClick={() => { onToast("Task drawer synced"); close(); }}>{taskCount} {t("status.running")}</button>
      </PortalMenu>
      <button ref={errorsRef} aria-label={t("topbar.errors")} className="relative rounded-lg border border-white/10 bg-white/5 p-2 text-danger hover:shadow-danger" onClick={() => setOpenMenu(openMenu === "errors" ? "" : "errors")}>
        <Bug size={19} />
        <span className="absolute -right-1 -top-1 rounded-full bg-danger px-1.5 text-[10px] font-bold text-white">{errorCount}</span>
      </button>
      <PortalMenu open={openMenu === "errors"} anchor={errorsRef.current} onClose={close} width={260}>
        <p className="px-3 py-2 font-bold text-danger">{t("topbar.errors")}</p>
        <button className="w-full rounded-xl px-3 py-2 text-left hover:bg-danger/10" onClick={() => { onToast("Error center opened"); close(); }}>{errorCount} {t("nav.errors")}</button>
      </PortalMenu>
      <button ref={userRef} aria-label={t("topbar.user_menu")} className="rounded-lg border border-white/10 bg-white/5 p-2 text-textMain" onClick={() => setOpenMenu(openMenu === "user" ? "" : "user")}>
        <UserCircle size={22} />
      </button>
      <PortalMenu open={openMenu === "user"} anchor={userRef.current} onClose={close} width={220}>
        <button className="w-full rounded-xl px-3 py-2 text-left hover:bg-neon/10" onClick={() => { onToast("topbar.profile"); close(); }}>{t("topbar.profile")}</button>
        <button className="w-full rounded-xl px-3 py-2 text-left text-danger hover:bg-danger/10" onClick={() => { clearSession(); window.dispatchEvent(new CustomEvent("sfs-auth-expired")); close(); }}>{t("topbar.logout")}</button>
      </PortalMenu>
    </header>
  );
}
