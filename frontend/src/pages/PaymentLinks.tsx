import { CreditCard, Link2, ShieldCheck } from "lucide-react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { payments } from "../data/mockData";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

export function PaymentLinks({ onToast }: Props) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Checkout Links")}</p>
        <h1 className="page-title">{t("Payment Links")}</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {payments.map((payment) => (
          <GlassCard key={payment.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-textMain">{payment.provider}</p>
                <p className="font-mono text-xs text-neon">{payment.id}</p>
              </div>
              <CreditCard className="text-plasma" />
            </div>
            <div className="mt-4 space-y-2 text-sm text-textWeak">
              <p>{t("site")}: {payment.site_id}</p>
              <p>{t("product")}: {payment.product}</p>
              <p>{t("button")}: {Object.values(payment.button).join(" / ")}</p>
            </div>
            <div className="mt-3"><StatusBadge status={payment.status} /></div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <NeonButton tone="ghost" onClick={() => onToast(`${t("Open")} ${payment.url}`)}><Link2 size={14} />{t("Open")}</NeonButton>
              <NeonButton tone="success" onClick={() => onToast(`${t("Checking")} ${payment.id}`)}><ShieldCheck size={14} />{t("Check")}</NeonButton>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
