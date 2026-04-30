import { Download, Filter } from "lucide-react";
import { ErrorCard } from "../components/ErrorCard";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { errors } from "../data/mockData";
import { api } from "../api/client";
import { useApiData } from "../api/useApiData";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

export function ErrorCenter({ onToast }: Props) {
  const { t } = useI18n();
  const liveErrors = useApiData(api.errors, { items: errors });
  const errorRows = liveErrors.data.items.map((error: any) => ({
    id: error.error_id || error.id,
    level: error.priority || error.level || (error.severity === "CRITICAL" ? "P0" : error.severity === "ERROR" ? "P1" : error.severity === "WARNING" ? "P2" : "P3"),
    site_id: error.site_id || "system",
    task_id: error.task_id || "",
    error_code: error.code || error.error_code,
    message: error.message,
    severity: error.severity,
    retryable: Boolean(error.retryable),
    user_action_required: Boolean(error.user_action_required),
    trace_id: error.trace_id || ""
  }));
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="page-kicker">{t("Failure Intelligence")}</p>
          <h1 className="page-title">{t("Error Center")}</h1>
        </div>
        <div className="flex gap-2"><NeonButton tone="ghost" onClick={() => onToast(t("Filters"))} data-testid="error-filters-button"><Filter size={15} />{t("Filters")}</NeonButton><NeonButton tone="danger" onClick={() => onToast(t("Error log exported"))}><Download size={15} />{t("Export Logs")}</NeonButton></div>
      </div>
      <GlassCard className="p-4">
        <div className="flex flex-wrap gap-2">
          {["P0", "P1", "P2", "P3", "P4", "site filter", "task filter"].map((item) => <button key={item} className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-textWeak hover:border-danger/30 hover:text-danger" onClick={() => onToast(`${t("Filters")} ${t(item)}`)}>{t(item)}</button>)}
        </div>
      </GlassCard>
      <div className="grid gap-4 xl:grid-cols-2">
        {errorRows.map((error) => <ErrorCard key={error.id} error={error} onAction={onToast} />)}
      </div>
    </div>
  );
}
