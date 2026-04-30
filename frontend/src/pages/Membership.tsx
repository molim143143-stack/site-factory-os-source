import { CalendarClock, KeyRound, MessageCircle, MonitorSmartphone, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { AccessLevelBadge } from "../components/AccessLevelBadge";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { currentMembership, membershipPlans, serviceRequests } from "../data/mockData";
import { api, errorText, getUserId } from "../api/client";
import { useApiData } from "../api/useApiData";
import { useState } from "react";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

export function Membership({ onToast }: Props) {
  const { t } = useI18n();
  const plans = useApiData(api.membershipPlans, { plans: membershipPlans.map((plan) => ({ plan: plan.plan.toLowerCase(), name: plan.plan, limits: plan })) });
  const [license, setLicense] = useState("");
  const [result, setResult] = useState<any>(null);
  const [activeMembership, setActiveMembership] = useState<any>(() => {
    try {
      return JSON.parse(localStorage.getItem("sfs_membership") || "") || currentMembership;
    } catch {
      return currentMembership;
    }
  });
  const run = async (label: string, fn: () => Promise<any>) => {
    try {
      const response = await fn();
      if (response?.membership) {
        localStorage.setItem("sfs_membership", JSON.stringify(response.membership));
        setActiveMembership({ ...currentMembership, ...response.membership });
      }
      setResult(response);
      onToast(`${label} OK`);
    } catch (error) {
      onToast(errorText(error));
    }
  };
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Manual Billing Gateway")}</p>
        <h1 className="page-title">{t("Membership")}</h1>
      </div>
      <div className="grid gap-4 xl:grid-cols-[.9fr_1.1fr]">
        <GlassCard className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <AccessLevelBadge level={activeMembership.plan} />
              <h2 className="mt-4 text-2xl font-black text-textMain">{t("Current Plan")}</h2>
              <p className="text-textWeak">{activeMembership.user_id || activeMembership.username}</p>
            </div>
            <StatusBadge status={activeMembership.status} />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Metric label="到期时间" value={activeMembership.expires_at} icon={CalendarClock} />
            <Metric label="网站额度" value={`${activeMembership.used_sites ?? 0}/${activeMembership.site_limit}`} icon={ShieldCheck} />
            <Metric label="今日部署" value={`${activeMembership.deployments_today ?? 0}/${activeMembership.deploy_limit_per_day || activeMembership.deployment_limit_per_day}`} icon={ShieldCheck} />
            <Metric label="设备绑定" value={`${activeMembership.bound_devices ?? 0}/${activeMembership.device_limit}`} icon={MonitorSmartphone} />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <NeonButton data-testid="membership-upgrade-pro-button" onClick={() => run("SERVICE_REQUEST", () => api.serviceRequest({ request_id: `web_open_req_${Date.now()}`, user_id: getUserId(), target_plan: "pro", contact_method: "telegram", contact_value: "@operator", note: "UI request" }))}><MessageCircle size={15} />{t("联系客服开通 Pro")}</NeonButton>
            <NeonButton tone="purple" onClick={() => run("SERVICE_REQUEST", () => api.serviceRequest({ request_id: `web_open_req_ent_${Date.now()}`, user_id: getUserId(), target_plan: "enterprise", contact_method: "telegram", contact_value: "@operator", note: "UI request" }))}>{t("联系客服开通 Enterprise")}</NeonButton>
            <input className="form-input max-w-xs" data-testid="license-code-input" placeholder={t("SFS-PRO-30D-XXXXXX")} value={license} onChange={(event) => setLicense(event.target.value)} />
            <NeonButton tone="ghost" data-testid="license-activate-button" onClick={() => run("LICENSE_ACTIVATE", () => api.activateLicenseKey({ license_key: license }))}><KeyRound size={15} />{t("输入激活码")}</NeonButton>
          </div>
          {result && <pre className="mt-4 max-h-36 overflow-auto rounded-xl bg-black/30 p-2 text-xs text-textWeak" data-testid="membership-result">{JSON.stringify(result, null, 2)}</pre>}
        </GlassCard>
        <GlassCard className="p-5">
          <h2 className="font-bold text-textMain">{t("Feature Permissions")}</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {(activeMembership.features || currentMembership.features).map((feature: string) => <span key={feature} className="rounded-full border border-success/30 bg-success/10 px-3 py-1 text-sm text-success">{feature}</span>)}
          </div>
          <h3 className="mt-6 font-bold text-textMain">{t("Opening Requests")}</h3>
          <div className="mt-3 space-y-3">
            {serviceRequests.map((request) => (
              <div key={request.request_id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <div className="flex items-center justify-between gap-2"><span className="font-mono text-neon">{request.request_id}</span><StatusBadge status={request.status} /></div>
                <p className="mt-2 text-sm text-textWeak">{request.target_plan} • {request.contact_method}: {request.contact_value}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {plans.data.plans.map((item: any) => {
          const plan = item.limits?.siteLimit ? item.limits : { plan: item.name || item.plan, price: "Manual", siteLimit: item.limits?.site_limit, bulk: Boolean(item.limits?.can_use_bulk_import), telegram: Boolean(item.limits?.can_use_telegram), diy: item.limits?.can_use_diy_builder ? "Full" : "Basic preview", i18n: item.limits?.can_use_i18n ? "All languages" : "en only", deploys: `${item.limits?.deploy_limit_per_day} / day`, devices: item.limits?.device_limit };
          return (
          <GlassCard key={plan.plan} className="p-4">
            <h2 className="text-xl font-black text-textMain">{plan.plan}</h2>
            <p className="mt-1 text-neon">{plan.price}</p>
            <div className="mt-4 space-y-2 text-sm text-textWeak">
              <p>{t("网站数量")}：{plan.siteLimit}</p>
              <p>{t("Bulk Import")}：{String(plan.bulk)}</p>
              <p>{t("Telegram")}：{String(plan.telegram)}</p>
              <p>{t("DIY Builder")}：{plan.diy}</p>
              <p>{t("多语言")}：{plan.i18n}</p>
              <p>{t("部署次数")}：{plan.deploys}</p>
              <p>{t("设备")}：{plan.devices}</p>
            </div>
          </GlassCard>
        )})}
      </div>
    </div>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  const { t } = useI18n();
  return <div className="rounded-2xl border border-white/10 bg-white/5 p-3"><Icon className="text-neon" size={18} /><p className="mt-2 text-xs uppercase tracking-[0.16em] text-textWeak">{t(label)}</p><p className="mt-1 font-mono text-textMain">{value}</p></div>;
}
