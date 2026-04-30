import { CheckCircle2, KeyRound, Plus, XCircle } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { licenseCodes, serviceRequests } from "../data/mockData";
import { api, errorText } from "../api/client";
import { useState } from "react";
import { useI18n } from "../i18n";
import { useApiData } from "../api/useApiData";

type Props = { onToast: (message: string) => void };

export function AdminBilling({ onToast }: Props) {
  const { t } = useI18n();
  const [result, setResult] = useState<any>(null);
  const [activationResult, setActivationResult] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [userId, setUserId] = useState("user_candy2000");
  const [plan, setPlan] = useState("vip");
  const [durationDays, setDurationDays] = useState(30);
  const requests = useApiData(api.serviceRequests, { items: serviceRequests }, [refreshKey]);
  const licenses = useApiData(api.adminLicenses, { items: licenseCodes }, [refreshKey]);
  const generate = async (plan: string, days: number) => {
    try {
      setBusy(`license-${plan}`);
      const response = await api.createAdminLicense({ plan, duration_days: days, count: 1 });
      setResult(response);
      setRefreshKey((value) => value + 1);
      onToast(`LICENSE_GENERATED ${response.keys?.[0] || response.license?.code || "OK"}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  const activateUser = async () => {
    try {
      setBusy("activate-user");
      const response = await api.adminActivateUser({ user_id: userId, plan, duration_days: durationDays });
      setActivationResult(response);
      setRefreshKey((value) => value + 1);
      onToast(`USER_ACTIVATED ${response.user_id}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  const updateRequest = async (request: any, action: "paid" | "activate" | "reject") => {
    setBusy(`${action}-${request.request_id}`);
    try {
      const payload = { request_id: `web_billing_${action}_${Date.now()}`, admin_id: "user_candy2000", duration_days: 30 };
      const response = action === "paid"
        ? await api.markServiceRequestPaid(request.request_id, payload)
        : action === "activate"
          ? await api.activateServiceRequest(request.request_id, payload)
          : await api.rejectServiceRequest(request.request_id, payload);
      setRefreshKey((value) => value + 1);
      onToast(`BILLING_${action.toUpperCase()} ${response.request?.request_id || request.request_id}`);
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Admin Manual Activation")}</p>
        <h1 className="page-title">{t("Admin Billing")}</h1>
      </div>
      <GlassCard className="p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-bold text-textMain">{t("Opening Requests")}</h2>
          <NeonButton data-testid="admin-manual-activate" onClick={activateUser} disabled={busy === "activate-user"}><Plus size={15} />{busy === "activate-user" ? t("common.loading") : t("Manual Activate")}</NeonButton>
        </div>
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead><tr><th>{t("request_id")}</th><th>{t("user")}</th><th>{t("target_plan")}</th><th>{t("contact")}</th><th>{t("status")}</th><th>{t("note")}</th><th>{t("actions")}</th></tr></thead>
            <tbody>
              {requests.data.items.map((request: any) => (
                <tr key={request.request_id}>
                  <td className="font-mono text-neon">{request.request_id}</td>
                  <td>{request.user_id}</td>
                  <td>{request.target_plan}</td>
                  <td>{request.contact_method}: {request.contact_value}</td>
                  <td><StatusBadge status={request.status} /></td>
                  <td>{request.note}</td>
                  <td><div className="flex gap-2"><NeonButton tone="warning" data-testid={`billing-paid-${request.request_id}`} onClick={() => updateRequest(request, "paid")} disabled={busy === `paid-${request.request_id}`}><CheckCircle2 size={14} />{t("Paid")}</NeonButton><NeonButton tone="success" data-testid={`billing-open-30d-${request.request_id}`} onClick={() => updateRequest(request, "activate")} disabled={busy === `activate-${request.request_id}`}>{t("Open 30D")}</NeonButton><NeonButton tone="danger" data-testid={`billing-reject-${request.request_id}`} onClick={() => updateRequest(request, "reject")} disabled={busy === `reject-${request.request_id}`}><XCircle size={14} />{t("Reject")}</NeonButton></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
      <GlassCard className="p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-bold text-textMain">{t("License Codes")}</h2>
          <div className="flex gap-2"><NeonButton data-testid="admin-generate-pro-license" onClick={() => generate("pro", 30)} disabled={busy === "license-pro"}><KeyRound size={15} />{busy === "license-pro" ? t("common.loading") : t("Generate PRO-30D")}</NeonButton><NeonButton tone="purple" data-testid="admin-generate-enterprise-license" onClick={() => generate("vip", 30)} disabled={busy === "license-vip"}>{busy === "license-vip" ? t("common.loading") : t("Generate ENTERPRISE-30D")}</NeonButton></div>
        </div>
        {result && <pre className="mb-4 max-h-36 overflow-auto rounded-xl bg-black/30 p-2 text-xs text-textWeak" data-testid="admin-license-result">{JSON.stringify(result, null, 2)}</pre>}
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead><tr><th>{t("code")}</th><th>{t("plan")}</th><th>{t("duration")}</th><th>{t("status")}</th><th>{t("used_by")}</th><th>{t("created_by")}</th><th>{t("actions")}</th></tr></thead>
            <tbody>
              {licenses.data.items.map((license: any) => (
                <tr key={license.code}>
                  <td className="font-mono text-neon">{license.code}</td>
                  <td>{license.plan}</td>
                  <td>{license.duration_days} {t("days")}</td>
                  <td><StatusBadge status={license.status} /></td>
                  <td>{license.used_by || "-"}</td>
                  <td>{license.created_by}</td>
                  <td><NeonButton tone="ghost" data-testid={`copy-license-${license.code}`} onClick={() => { void navigator.clipboard?.writeText(license.code); onToast(`LICENSE_COPIED ${license.code}`); }}>{t("Copy")}</NeonButton></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
      <GlassCard className="p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-bold text-textMain">{t("Admin User Activation")}</h2>
          <NeonButton data-testid="admin-activate-user-button" tone="success" onClick={activateUser} disabled={busy === "activate-user"}>
            <CheckCircle2 size={15} />{busy === "activate-user" ? t("common.loading") : t("Activate Account")}
          </NeonButton>
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          <label className="block"><span className="form-label">{t("user_id")}</span><input className="form-input" data-testid="admin-activate-user-id" value={userId} onChange={(event) => setUserId(event.target.value)} /></label>
          <label className="block"><span className="form-label">{t("plan")}</span><select className="form-select w-full" data-testid="admin-activate-plan" value={plan} onChange={(event) => setPlan(event.target.value)}><option value="free">{t("Free")}</option><option value="basic">{t("Basic")}</option><option value="pro">{t("Pro")}</option><option value="vip">{t("VIP")}</option><option value="admin">{t("Admin")}</option></select></label>
          <label className="block"><span className="form-label">{t("duration")}</span><input className="form-input" data-testid="admin-activate-days" type="number" min={1} value={durationDays} onChange={(event) => setDurationDays(Number(event.target.value) || 1)} /></label>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-textWeak">{t("vip/admin can create licenses and activate accounts.")}</div>
        </div>
        {activationResult && <pre className="mt-4 max-h-36 overflow-auto rounded-xl bg-black/30 p-2 text-xs text-textWeak" data-testid="admin-activation-result">{JSON.stringify(activationResult, null, 2)}</pre>}
      </GlassCard>
    </div>
  );
}
