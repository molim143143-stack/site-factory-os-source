import { BookOpen, CheckCircle2, Globe2, Link2, RadioTower, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { sites } from "../data/mockData";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";
import { useI18n } from "../i18n";

type Props = { siteId: string; onToast: (message: string) => void };

export function DNSDomain({ siteId, onToast }: Props) {
  const { t } = useI18n();
  const site = useApiData(() => api.site(siteId), sites[0] as any, [siteId]);
  const [result, setResult] = useState<any>(null);
  const check = async (domain: string) => {
    try {
      const response = await api.dnsCheck(domain, { request_id: `web_dns_${Date.now()}` });
      setResult(response);
      onToast("DNS_CHECK OK");
    } catch (error) {
      onToast(errorText(error));
    }
  };
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Domain Operations")}</p>
        <h1 className="page-title">{t("DNS / Domain")}</h1>
      </div>
      <GlassCard className="border-warning/25 bg-warning/5 p-4">
        <div className="flex gap-3">
          <BookOpen className="mt-1 text-warning" />
          <div>
            <h2 className="font-bold text-warning">{t("Name.com first version is guidance only.")}</h2>
            <p className="mt-1 text-sm text-textWeak">{t("第一版 Name.com 只做 NS 设置指引，不做自动购买域名。")}</p>
          </div>
        </div>
      </GlassCard>
      <div className="grid gap-4 xl:grid-cols-[.8fr_1.2fr]">
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("Add Domain")}</h2>
          <div className="mt-4 space-y-4">
            <label><span className="form-label">{t("Domain")}</span><input className="form-input" placeholder={t("example.com")} /></label>
            <label><span className="form-label">{t("Site")}</span><select className="form-select w-full">{sites.slice(0, 5).map((site) => <option key={site.site_id}>{site.alias}</option>)}</select></label>
            <NeonButton className="w-full" onClick={() => onToast("Cloudflare zone create task queued")}><Globe2 size={15} />{t("Create Cloudflare Zone")}</NeonButton>
            <NeonButton className="w-full" tone="success" data-testid="dns-check-current-button" onClick={() => check(site.data.domain)}><CheckCircle2 size={15} />{t("Check Current DNS")}</NeonButton>
            {result && <pre className="max-h-32 overflow-auto rounded-xl bg-black/30 p-2 text-xs text-textWeak" data-testid="dns-result">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("DNS Workflow")}</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {[
              ["Get NS", "ns1.cloudflare-mock.com / ns2.cloudflare-mock.com", RadioTower],
              ["Set NS at Name.com", "Manual operator step", BookOpen],
              ["Check NS", "Detect propagation", CheckCircle2],
              ["Bind GitHub Pages", "CNAME + Pages binding", Link2],
              ["Check SSL", "Certificate active", ShieldCheck],
              ["Check Access", "Live URL probe", Globe2]
            ].map(([title, desc, Icon]) => (
              <div key={title as string} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <Icon className="text-neon" />
                <h3 className="mt-3 font-bold text-textMain">{t(title as string)}</h3>
                <p className="mt-1 text-sm text-textWeak">{t(desc as string)}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
      <GlassCard className="p-4">
        <h2 className="mb-4 font-bold text-textMain">{t("Domain Status")}</h2>
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead><tr><th>{t("domain")}</th><th>{t("site")}</th><th>DNS</th><th>SSL</th><th>{t("action")}</th></tr></thead>
            <tbody>
              {sites.slice(0, 8).map((site) => (
                <tr key={site.site_id}><td>{site.domain}</td><td>{site.alias}</td><td><StatusBadge status={site.dns} /></td><td><StatusBadge status={site.dns === "active" ? "active" : "pending"} /></td><td><NeonButton tone="ghost" onClick={() => check(site.domain)}>{t("Check")}</NeonButton></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
