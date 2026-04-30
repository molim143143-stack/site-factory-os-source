import { CheckCircle2, Clock, RadioTower, ShieldAlert, XCircle, Zap } from "lucide-react";
import { useI18n } from "../i18n";

type Props = {
  status: string;
};

export function StatusBadge({ status }: Props) {
  const { t } = useI18n();
  const normalized = status.toLowerCase();
  const config = normalized.includes("success") || normalized === "active" || normalized === "published"
    ? { icon: CheckCircle2, cls: "border-success/30 bg-success/10 text-success" }
    : normalized.includes("running") || normalized.includes("deploying") || normalized === "queued"
      ? { icon: Zap, cls: "border-neon/30 bg-neon/10 text-neon" }
      : normalized.includes("pending") || normalized.includes("waiting") || normalized.includes("retrying")
        ? { icon: Clock, cls: "border-warning/30 bg-warning/10 text-warning" }
        : normalized.includes("dns")
          ? { icon: RadioTower, cls: "border-plasma/30 bg-plasma/10 text-[#bba7ff]" }
          : normalized.includes("error") || normalized.includes("failed")
            ? { icon: XCircle, cls: "border-danger/30 bg-danger/10 text-danger" }
            : { icon: ShieldAlert, cls: "border-white/15 bg-white/5 text-textWeak" };
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${config.cls}`}>
      <Icon size={13} />
      {t(`status.${status}`)}
    </span>
  );
}
