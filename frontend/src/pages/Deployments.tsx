import { GitCommit, RotateCcw, ScrollText } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { deployments } from "../data/mockData";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

export function Deployments({ onToast }: Props) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Release Ledger")}</p>
        <h1 className="page-title">{t("Deployments")}</h1>
      </div>
      <GlassCard className="p-4">
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead><tr><th>{t("deploy_id")}</th><th>{t("site")}</th><th>{t("commit_id")}</th><th>{t("previous")}</th><th>{t("type")}</th><th>{t("status")}</th><th>{t("created")}</th><th>{t("actions")}</th></tr></thead>
            <tbody>
              {deployments.map((deploy) => (
                <tr key={deploy.deploy_id}>
                  <td className="font-mono text-neon">{deploy.deploy_id}</td>
                  <td>{deploy.site_id}</td>
                  <td><span className="inline-flex items-center gap-1"><GitCommit size={14} />{deploy.commit_id}</span></td>
                  <td>{deploy.previous_commit_id}</td>
                  <td>{deploy.type}</td>
                  <td><StatusBadge status={deploy.status} /></td>
                  <td>{deploy.created_at}</td>
                  <td><div className="flex gap-2"><NeonButton tone="purple" onClick={() => onToast(`Rollback ${deploy.deploy_id} requires confirmation`)}><RotateCcw size={14} />{t("Rollback")}</NeonButton><NeonButton tone="ghost"><ScrollText size={14} />{t("Logs")}</NeonButton></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
