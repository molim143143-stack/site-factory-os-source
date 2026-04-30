import { Copy, Eye, Pause, Play, Rocket, Search, Trash2, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { sites } from "../data/mockData";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";
import { PortalModal } from "../components/floating/PortalMenu";
import { useI18n } from "../i18n";

type Props = {
  onSiteDetail: (siteId: string) => void;
  onNavigate: (page: "cms" | "builder" | "deployments") => void;
  onSelectSite: (siteId: string) => void;
  onToast: (message: string) => void;
};

export function Sites({ onSiteDetail, onNavigate, onSelectSite, onToast }: Props) {
  const { t } = useI18n();
  const [refreshKey, setRefreshKey] = useState(0);
  const liveSitesFresh = useApiData(api.sites, { items: sites }, [refreshKey]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [type, setType] = useState("all");
  const filtered = useMemo(
    () =>
      liveSitesFresh.data.items.map((site: any) => ({
        ...site,
        alias: site.alias || site.site_id,
        type: site.type || site.site_type || "landing",
        dns: site.dns || site.status || "unknown",
        last_deploy_at: site.last_deploy_at || "never"
      })).filter((site) => {
        const matchQuery = [site.alias, site.domain, site.site_id].join(" ").toLowerCase().includes(query.toLowerCase());
        const matchStatus = status === "all" || site.status === status;
        const matchType = type === "all" || site.type === type;
        return matchQuery && matchStatus && matchType;
      }),
    [query, status, type, liveSitesFresh.data]
  );
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<any | null>(null);
  const [busySite, setBusySite] = useState("");
  const [alias, setAlias] = useState("V2 Proof Site");
  const [domain, setDomain] = useState(`v2-${Date.now()}.local.test`);
  const createSite = async () => {
    setCreating(true);
    try {
      const result = await api.createSite({ request_id: `web_site_${Date.now()}`, alias, domain, site_type: "shop", template_id: "shop1" });
      onToast(`${t("SITE_CREATED")} ${result.site.site_id}`);
      setRefreshKey((value) => value + 1);
      onSiteDetail(result.site.site_id);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setCreating(false);
    }
  };
  const openSite = (site: any) => {
    const url = site.public_url || site.github_pages_url || "";
    if (url) window.open(url, "_blank", "noopener,noreferrer");
    onToast(`${t("site.open")} ${url || site.site_id}`);
  };
  const goSitePage = (site: any, page: "cms" | "builder" | "deployments") => {
    onSelectSite(site.site_id);
    onNavigate(page);
    onToast(`${t(page === "cms" ? "site.cms" : page === "builder" ? "site.diy" : "site.deploy")} ${site.alias}`);
  };
  const deploySite = async (site: any) => {
    setBusySite(`deploy-${site.site_id}`);
    try {
      const result = await api.deployGithub(site.site_id, { request_id: `web_github_deploy_${Date.now()}` });
      setRefreshKey((value) => value + 1);
      onToast(`DEPLOY_GITHUB_OK ${result.public_url || result.github_pages_url || result.deployment?.live_url || site.site_id}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusySite("");
    }
  };
  const cloneSite = async (site: any) => {
    setBusySite(`clone-${site.site_id}`);
    try {
      const stamp = Date.now();
      const result = await api.cloneSite(site.site_id, { request_id: `web_clone_${stamp}`, alias: `${site.alias} Copy`, domain: `clone-${stamp}.local.test` });
      setRefreshKey((value) => value + 1);
      onToast(`SITE_CLONED ${result.site?.site_id || site.site_id}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusySite("");
    }
  };
  const togglePause = async (site: any) => {
    setBusySite(`pause-${site.site_id}`);
    try {
      const action = site.status === "inactive" ? api.resumeSite : api.pauseSite;
      const result = await action(site.site_id, { request_id: `web_site_status_${Date.now()}` });
      setRefreshKey((value) => value + 1);
      onToast(`SITE_STATUS_UPDATED ${result.site?.status || site.site_id}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusySite("");
    }
  };
  const deleteSite = async () => {
    if (!deleteTarget) return;
    setBusySite(`delete-${deleteTarget.site_id}`);
    try {
      const requestId = `web_delete_${Date.now()}`;
      await api.deleteSiteRequest(deleteTarget.site_id, { request_id: `${requestId}_request` });
      const result = await api.deleteSiteConfirm(deleteTarget.site_id, { request_id: `${requestId}_confirm` });
      setRefreshKey((value) => value + 1);
      onToast(`SITE_DELETED ${result.site?.site_id || deleteTarget.site_id}`);
      setDeleteTarget(null);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusySite("");
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Multi-site Fleet")}</p>
        <h1 className="page-title">{t("site.title")}</h1>
      </div>
      <GlassCard className="p-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_180px_180px_auto]">
          <label className="flex h-11 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-textWeak">
            <Search size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("site.search_placeholder")} className="w-full bg-transparent text-sm text-textMain outline-none" />
          </label>
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="form-select">
            <option value="all">{t("site.status_all")}</option>
            <option value="active">{t("active")}</option>
            <option value="deploying">{t("deploying")}</option>
            <option value="dns_pending">{t("dns_pending")}</option>
            <option value="error">{t("error")}</option>
          </select>
          <select value={type} onChange={(event) => setType(event.target.value)} className="form-select">
            <option value="all">{t("site.type_all")}</option>
            <option value="shop">{t("shop")}</option>
            <option value="blog">{t("blog")}</option>
            <option value="landing">{t("landing")}</option>
            <option value="catalog">{t("catalog")}</option>
          </select>
          <NeonButton onClick={createSite} disabled={creating} data-testid="create-site-button">{creating ? t("common.loading") : t("site.create")}</NeonButton>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <input className="form-input" data-testid="create-site-alias" value={alias} onChange={(event) => setAlias(event.target.value)} />
          <input className="form-input" data-testid="create-site-domain" value={domain} onChange={(event) => setDomain(event.target.value)} />
        </div>
      </GlassCard>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {filtered.map((site) => (
          <GlassCard key={site.site_id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-textMain">{site.alias}</h2>
                <p className="font-mono text-xs text-neon">{site.site_id}</p>
              </div>
              <StatusBadge status={site.status} />
            </div>
            <div className="mt-4 grid gap-2 text-sm text-textWeak">
              <span>{t("site.domain")}: <b className="text-textMain">{site.domain}</b></span>
              <span>{t("site.type")}: <b className="text-textMain">{site.type}</b></span>
              <span>{t("DNS")}: <b className="text-textMain">{site.dns}</b></span>
              <span>{t("site.last_deploy")}: <b className="text-textMain">{site.last_deploy_at}</b></span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-2">
              <NeonButton tone="primary" onClick={() => onSiteDetail(site.site_id)}><Eye size={15} />{t("site.detail")}</NeonButton>
              <NeonButton tone="ghost" data-testid={`site-open-${site.site_id}`} onClick={() => openSite(site)}>{t("site.open")}</NeonButton>
              <NeonButton tone="purple" data-testid={`site-cms-${site.site_id}`} onClick={() => goSitePage(site, "cms")}><Wrench size={15} />{t("site.cms")}</NeonButton>
              <NeonButton tone="purple" data-testid={`site-diy-${site.site_id}`} onClick={() => goSitePage(site, "builder")}>{t("site.diy")}</NeonButton>
              <NeonButton tone="warning" data-testid={`site-deploy-${site.site_id}`} onClick={() => deploySite(site)} disabled={busySite === `deploy-${site.site_id}`}><Rocket size={15} />{busySite === `deploy-${site.site_id}` ? t("common.loading") : t("site.deploy")}</NeonButton>
              <NeonButton tone="ghost" data-testid={`site-clone-${site.site_id}`} onClick={() => cloneSite(site)} disabled={busySite === `clone-${site.site_id}`}><Copy size={15} />{busySite === `clone-${site.site_id}` ? t("common.loading") : t("site.clone")}</NeonButton>
              <NeonButton tone={site.status === "inactive" ? "success" : "ghost"} data-testid={`site-pause-${site.site_id}`} onClick={() => togglePause(site)} disabled={busySite === `pause-${site.site_id}`}>
                {site.status === "inactive" ? <Play size={15} /> : <Pause size={15} />}
                {site.status === "inactive" ? t("site.resume") : t("site.pause")}
              </NeonButton>
              <NeonButton tone="danger" data-testid={`site-delete-${site.site_id}`} onClick={() => setDeleteTarget(site)}><Trash2 size={15} />{t("site.delete")}</NeonButton>
            </div>
          </GlassCard>
        ))}
      </div>
      <PortalModal open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <h2 className="text-xl font-black text-textMain">{t("site.delete_confirm_title")}</h2>
        <p className="mt-3 text-sm text-textWeak">{t("site.delete_confirm_body")}</p>
        <p className="mt-3 font-mono text-sm text-neon">{deleteTarget?.site_id}</p>
        <div className="mt-5 flex justify-end gap-2">
          <NeonButton tone="ghost" onClick={() => setDeleteTarget(null)}>{t("common.cancel")}</NeonButton>
          <NeonButton tone="danger" data-testid="site-delete-confirm" onClick={deleteSite} disabled={busySite === `delete-${deleteTarget?.site_id}`}>{busySite === `delete-${deleteTarget?.site_id}` ? t("common.loading") : t("site.delete_confirm_action")}</NeonButton>
        </div>
      </PortalModal>
    </div>
  );
}
