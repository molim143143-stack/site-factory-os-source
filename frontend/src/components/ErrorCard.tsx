import { AlertTriangle, RefreshCcw } from "lucide-react";
import { errors } from "../data/mockData";
import { GlassCard } from "./GlassCard";
import { NeonButton } from "./NeonButton";
import { StatusBadge } from "./StatusBadge";
import { useI18n } from "../i18n";

type Props = {
  error: (typeof errors)[number];
  onAction?: (message: string) => void;
};

export function ErrorCard({ error, onAction }: Props) {
  const { t } = useI18n();
  const message = t(`errors.${error.error_code}`);
  return (
    <GlassCard glow={error.severity === "CRITICAL" ? "danger" : "cyan"} className="p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-xl border border-danger/30 bg-danger/10 p-2 text-danger">
          <AlertTriangle size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-bold text-danger">{error.error_code}</span>
            <StatusBadge status={error.level} />
            <StatusBadge status={error.severity} />
          </div>
          <p className="mt-2 text-sm text-textMain">{message === `errors.${error.error_code}` ? t(error.message) : message}</p>
          <div className="mt-3 grid gap-2 text-xs text-textWeak sm:grid-cols-2">
            <span>{t("Trace")}: {error.trace_id}</span>
            <span>{t("task")}: {error.task_id}</span>
            <span>{t("retryable")}: {String(error.retryable)}</span>
            <span>{t("action required")}: {String(error.user_action_required)}</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <NeonButton tone="danger" onClick={() => onAction?.(`Retry scheduled for ${error.error_code}`)}>
              <RefreshCcw size={15} />
              {t("Retry")}
            </NeonButton>
            <NeonButton tone="ghost" onClick={() => onAction?.(`Trace copied: ${error.trace_id}`)}>
              {t("Trace")}
            </NeonButton>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
