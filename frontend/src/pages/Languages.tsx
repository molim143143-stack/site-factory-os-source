import { FileText, Languages as LanguagesIcon, Package, Rocket } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { languageCompletion } from "../data/mockData";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

export function Languages({ onToast }: Props) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("I18n Matrix")}</p>
        <h1 className="page-title">{t("Languages")}</h1>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_.8fr]">
        <GlassCard className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-textMain">{t("Language Completeness")}</h2>
            <span className="rounded-full border border-neon/30 bg-neon/10 px-3 py-1 text-sm text-neon">{t("default: en")}</span>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={languageCompletion}>
                <XAxis dataKey="code" stroke="#8FA3BF" />
                <YAxis stroke="#8FA3BF" />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(0,229,255,.25)" }} />
                <Bar dataKey="completion" fill="#00E5FF" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("Views")}</h2>
          <div className="mt-4 grid gap-3">
            {[["By Page", FileText], ["By Product", Package], ["By Article", FileText]].map(([label, Icon]) => (
              <button key={label as string} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4 text-left text-textMain hover:border-neon/30" onClick={() => onToast(`${t("Open")} ${t(label as string)}`)}>
                <span className="flex items-center gap-3"><Icon size={18} className="text-neon" />{t(label as string)}</span>
                <span className="text-textWeak">{t("Open")}</span>
              </button>
            ))}
          </div>
        </GlassCard>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {languageCompletion.map((lang) => (
          <GlassCard key={lang.code} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-textMain">{lang.name}</p>
                <p className="font-mono text-xs text-neon">{lang.code}</p>
              </div>
              <LanguagesIcon className="text-plasma" />
            </div>
            <div className="mt-4 h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-neon to-success" style={{ width: `${lang.completion}%` }} />
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="text-textWeak">{lang.completion}% {t("complete")}</span>
              <span className="text-warning">{lang.missing} {t("missing")}</span>
            </div>
            <NeonButton className="mt-4 w-full" tone={lang.completion === 100 ? "success" : "warning"} onClick={() => onToast(`Publish ${lang.code} queued`)}>
              <Rocket size={15} />{t("Publish Language")}
            </NeonButton>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
