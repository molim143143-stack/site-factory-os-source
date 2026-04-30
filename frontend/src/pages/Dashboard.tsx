import { AlertTriangle, Boxes, CheckCircle2, Globe2, Languages, Rocket, TerminalSquare, Zap } from "lucide-react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useApiData } from "../api/useApiData";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatCard } from "../components/StatCard";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

type Props = {
  onNavigate: (page: string) => void;
  onToast: (message: string) => void;
};

export function Dashboard({ onNavigate, onToast }: Props) {
  const { t } = useI18n();
  const system = useApiData(api.systemStatus, { sites: 0, sites_active: 0, deployments: 0, errors: 0, dns_issues: 0, language_gaps: 0, tasks_running: 0, tasks_failed: 0 });
  const liveDeployments = useApiData(api.deployments, { items: [] });
  const liveErrors = useApiData(api.errors, { items: [] });
  const active = system.data.sites_active;
  const running = system.data.tasks_running;
  const failed = system.data.tasks_failed;
  const dnsIssues = system.data.dns_issues;
  const trendData = [
    { day: t("Sites"), tasks: system.data.sites, deploys: system.data.deployments, failed },
    { day: t("Tasks"), tasks: running + failed, deploys: system.data.deployments, failed },
    { day: t("Errors"), tasks: running, deploys: system.data.deployments, failed: system.data.errors }
  ];
  const statusDistribution = [
    { name: "active", value: active },
    { name: "dns issues", value: dnsIssues },
    { name: "failed", value: failed },
    { name: "errors", value: system.data.errors }
  ].filter((item) => item.value > 0);
  const colors = ["#00E5FF", "#7C4DFF", "#FFB300", "#FF3D71", "#00FF95"];

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-3xl border border-neon/20 bg-gradient-to-br from-neon/10 via-plasma/10 to-transparent p-5 shadow-neon md:p-7">
        <div className="scanline" />
        <p className="text-xs uppercase tracking-[0.35em] text-neon">{t("AI Website Factory Control Plane")}</p>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <h1 className="max-w-4xl text-3xl font-black text-textMain md:text-5xl">{t("Site Factory OS")}</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-textWeak md:text-base">
              {t("Multi-site publishing, deployment telemetry, DNS intelligence, bulk validation, and multilingual release control in one command surface.")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {["Create Site", "Bulk Import", "DIY Builder", "Publish Article", "Publish Product", "Check DNS"].map((label) => (
              <NeonButton key={label} tone={label.includes("Bulk") ? "purple" : "primary"} onClick={() => onToast(`${label} action queued`)}>
                <Zap size={15} />
                {t(label)}
              </NeonButton>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <StatCard label={t("Total Sites")} value={system.data.sites} hint={t("Live API / SQLite")} icon={Boxes} />
        <StatCard label={t("Active")} value={active} hint={t("Live and healthy")} icon={CheckCircle2} tone="green" />
        <StatCard label={t("DNS Issues")} value={dnsIssues} hint={t("Need operator action")} icon={Globe2} tone="amber" />
        <StatCard label={t("Running Tasks")} value={running} hint={t("Worker pipeline")} icon={TerminalSquare} tone="purple" />
        <StatCard label={t("Failed Tasks")} value={failed} hint={t("Retry available")} icon={AlertTriangle} tone="red" />
        <StatCard label={t("Language Gaps")} value={system.data.language_gaps} hint={t("Missing fields")} icon={Languages} tone="amber" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <GlassCard className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-textMain">{t("Task Trend")}</h2>
            <StatusBadge status="live" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <XAxis dataKey="day" stroke="#8FA3BF" />
                <YAxis stroke="#8FA3BF" />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(0,229,255,.25)", color: "#E5F7FF" }} />
                <Line type="monotone" dataKey="tasks" stroke="#00E5FF" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="deploys" stroke="#00FF95" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="failed" stroke="#FF3D71" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <h2 className="mb-4 font-bold text-textMain">{t("Site Status Distribution")}</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusDistribution} dataKey="value" nameKey="name" innerRadius={58} outerRadius={100}>
                  {statusDistribution.map((_, index) => (
                    <Cell key={index} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(0,229,255,.25)" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <GlassCard className="p-4">
          <div className="mb-4 flex items-center gap-2">
            <Rocket size={18} className="text-neon" />
            <h2 className="font-bold text-textMain">{t("Recent Deployments")}</h2>
          </div>
          <div className="space-y-3">
            {liveDeployments.data.items.slice(0, 4).map((deploy: any) => (
              <div key={deploy.deploy_id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 p-3">
                <div>
                  <p className="font-mono text-sm text-textMain">{deploy.deploy_id}</p>
                  <p className="text-xs text-textWeak">{deploy.commit_id} • {deploy.created_at}</p>
                </div>
                <StatusBadge status={deploy.status} />
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard className="p-4" glow="danger">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-danger" />
            <h2 className="font-bold text-textMain">{t("Recent Errors")}</h2>
          </div>
          <div className="space-y-3">
            {liveErrors.data.items.slice(0, 4).map((error: any) => (
              <button key={error.error_id} onClick={() => onNavigate("errors")} className="w-full rounded-2xl border border-danger/15 bg-danger/5 p-3 text-left transition hover:border-danger/40 hover:shadow-danger">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-sm text-danger">{error.error_code}</span>
                  <StatusBadge status={error.severity} />
                </div>
                <p className="mt-1 text-sm text-textWeak">{t(`errors.${error.error_code}`) === `errors.${error.error_code}` ? t(error.message) : t(`errors.${error.error_code}`)}</p>
              </button>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
