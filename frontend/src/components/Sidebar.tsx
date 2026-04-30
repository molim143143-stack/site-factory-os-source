import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Brush,
  CreditCard,
  FileText,
  Globe2,
  HandCoins,
  Languages,
  LayoutDashboard,
  Rocket,
  SearchCode,
  Settings,
  ShieldCheck,
  TerminalSquare,
  Users,
  Workflow
} from "lucide-react";
import { Z_INDEX } from "../constants/zIndex";
import { useI18n } from "../i18n";
import type { PageKey } from "../types";

const nav = [
  { key: "dashboard", titleKey: "nav.dashboard", icon: LayoutDashboard },
  { key: "sites", titleKey: "nav.sites", icon: Boxes },
  { key: "cms", titleKey: "nav.cms", icon: FileText },
  { key: "builder", titleKey: "nav.builder", icon: Brush },
  { key: "bulk", titleKey: "nav.bulk_import", icon: Workflow },
  { key: "languages", titleKey: "nav.languages", icon: Languages },
  { key: "seo", titleKey: "nav.seo", icon: SearchCode },
  { key: "dns", titleKey: "nav.dns", icon: Globe2 },
  { key: "deployments", titleKey: "nav.deployments", icon: Rocket },
  { key: "tasks", titleKey: "nav.tasks", icon: TerminalSquare },
  { key: "errors", titleKey: "nav.errors", icon: AlertTriangle },
  { key: "payments", titleKey: "nav.payments", icon: CreditCard },
  { key: "membership", titleKey: "nav.members", icon: ShieldCheck },
  { key: "adminBilling", titleKey: "nav.manual_open", icon: HandCoins },
  { key: "users", titleKey: "nav.users", icon: Users },
  { key: "settings", titleKey: "nav.settings", icon: Settings }
] as const;

type Props = {
  active: PageKey;
  onNavigate: (page: PageKey) => void;
  open: boolean;
  onClose: () => void;
};

export function Sidebar({ active, onNavigate, open, onClose }: Props) {
  const { t } = useI18n();
  return (
    <>
      <div className={`fixed inset-0 bg-black/60 backdrop-blur-sm lg:hidden ${open ? "block" : "hidden"}`} style={{ zIndex: Z_INDEX.sidebar - 1 }} onClick={onClose} />
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[260px] border-r border-white/10 bg-[#0A0F1C]/90 p-4 backdrop-blur-2xl transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ zIndex: Z_INDEX.sidebar }}
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-neon/40 bg-neon/10 text-neon shadow-neon">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="text-lg font-black text-textMain">{t("Site Factory")}</div>
            <div className="text-xs uppercase tracking-[0.28em] text-neon">{t("OS Control")}</div>
          </div>
        </div>

        <nav className="space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const selected = active === item.key;
            return (
              <button
                key={item.key}
                onClick={() => {
                  onNavigate(item.key);
                  onClose();
                }}
                className={`group flex min-h-11 w-full items-center gap-3 rounded-xl border px-3 text-left text-sm transition-all ${
                  selected
                    ? "border-neon/40 bg-neon/10 text-neon shadow-neon"
                    : "border-transparent text-textWeak hover:border-white/10 hover:bg-white/5 hover:text-textMain"
                }`}
              >
                <Icon size={18} className={selected ? "text-neon" : "text-textWeak group-hover:text-neon"} />
                <span>{t(item.titleKey)}</span>
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
