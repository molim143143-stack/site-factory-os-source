import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { useI18n } from "../i18n";
import { useState } from "react";

type Props = {
  title: string;
  kicker: string;
  description: string;
};

export function SimplePage({ title, kicker, description }: Props) {
  const { t } = useI18n();
  const [opened, setOpened] = useState(false);
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t(kicker)}</p>
        <h1 className="page-title">{t(title)}</h1>
      </div>
      <GlassCard className="p-6">
        <p className="max-w-3xl text-textWeak">{t(description)}</p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {["Role Matrix", "Operator Sessions", "Risk Confirmations"].map((item) => (
            <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <h2 className="font-bold text-textMain">{t(item)}</h2>
              <p className="mt-2 text-sm text-textWeak">{t("Ready for API integration and policy wiring.")}</p>
            </div>
          ))}
        </div>
        <NeonButton className="mt-6" onClick={() => setOpened((value) => !value)} data-testid="simple-open-console-button">{t("Open Console")}</NeonButton>
        {opened && <p className="mt-3 rounded-2xl border border-neon/20 bg-neon/10 p-3 text-sm text-neon" data-testid="simple-open-console-result">{t("Ready for API integration and policy wiring.")}</p>}
      </GlassCard>
    </div>
  );
}
