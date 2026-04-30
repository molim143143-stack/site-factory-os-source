import { Copy, ExternalLink, Globe2, Languages, Pause, Rocket, SearchCode, Trash2, Wrench } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { deployments, errors, sites } from "../data/mockData";
import { useI18n } from "../i18n";

type Props = {
  siteId: string;
  onNavigate: (page: string) => void;
  onToast: (message: string) => void;
};

export function SiteDetail({ siteId, onNavigate, onToast }: Props) {
  const { t } = useI18n();
  const site = sites.find((item) => item.site_id === siteId) ?? sites[0];
  const siteDeployments = deployments.filter((deploy) => deploy.site_id === site.site_id);
  const siteErrors = errors.filter((error) => error.site_id === site.site_id);
  const actions = [
    { label: "Open Site", icon: ExternalLink, page: null },
    { label: "Edit CMS", icon: Wrench, page: "cms" },
    { label: "DIY Builder", icon: Wrench, page: "builder" },
    { label: "Bulk Import", icon: Copy, page: "bulk" },
    { label: "Languages", icon: Languages, page: "languages" },
    { label: "SEO", icon: SearchCode, page: "seo" },
    { label: "DNS", icon: Globe2, page: "dns" },
    { label: "Deploy", icon: Rocket, page: "deployments" },
    { label: "Clone", icon: Copy, page: null },
    { label: "Pause", icon: Pause, page: null },
    { label: "Delete", icon: Trash2, page: null, danger: true }
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="page-kicker">{t("Site Detail")}</p>
          <h1 className="page-title">{site.alias}</h1>
        </div>
        <StatusBadge status={site.status} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_.85fr]">
        <GlassCard className="p-5">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["site_id", site.site_id],
              ["alias", site.alias],
              ["domain", site.domain],
              ["repo", site.repo],
              ["template", site.template],
              ["status", site.status],
              ["default_language", site.default_language],
              ["enabled_languages", site.languages.join(", ")],
              ["last_deploy_at", site.last_deploy_at],
              ["DNS status", site.dns],
              ["GitHub status", site.github],
              ["error status", `${site.errors} open errors`]
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-textWeak">{t(label)}</p>
                <p className="mt-2 break-words font-mono text-sm text-textMain">{value}</p>
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard className="p-5">
          <h2 className="font-bold text-textMain">{t("Operations")}</h2>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <NeonButton key={action.label} tone={action.danger ? "danger" : "ghost"} onClick={() => action.page ? onNavigate(action.page) : onToast(`${t(action.label)} ${t("queued")}`)}>
                  <Icon size={15} />
                  {t(action.label)}
                </NeonButton>
              );
            })}
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <GlassCard className="p-4">
          <h2 className="mb-3 font-bold text-textMain">{t("Recent Deployments")}</h2>
          <div className="space-y-3">
            {siteDeployments.length ? siteDeployments.map((deploy) => (
              <div key={deploy.deploy_id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm text-neon">{deploy.deploy_id}</span>
                  <StatusBadge status={deploy.status} />
                </div>
                <p className="mt-2 text-xs text-textWeak">{deploy.commit_id} • {deploy.created_at}</p>
              </div>
            )) : <p className="text-sm text-textWeak">{t("No deployments yet.")}</p>}
          </div>
        </GlassCard>
        <GlassCard className="p-4" glow="danger">
          <h2 className="mb-3 font-bold text-textMain">{t("Error State")}</h2>
          <div className="space-y-3">
            {siteErrors.length ? siteErrors.map((error) => (
              <div key={error.id} className="rounded-xl border border-danger/20 bg-danger/5 p-3">
                <p className="font-mono text-sm text-danger">{error.error_code}</p>
                <p className="mt-1 text-sm text-textWeak">{error.message}</p>
              </div>
            )) : <p className="text-sm text-success">{t("No active errors detected.")}</p>}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
