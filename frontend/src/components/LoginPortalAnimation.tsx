import { useEffect, useState } from "react";
import { AccessLevelBadge } from "./AccessLevelBadge";
import { CyberScanLine } from "./CyberScanLine";
import { NeonParticleField } from "./NeonParticleField";
import { useI18n } from "../i18n";

type Props = {
  username: string;
  plan: string;
  onDone: () => void;
};

const modules = ["Build Engine", "Task Engine", "DNS Engine", "Deploy Engine", "Bulk Engine"];

export function LoginPortalAnimation({ username, plan, onDone }: Props) {
  const { t } = useI18n();
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const timers = [900, 1800, 3000, 4200].map((time, index) => window.setTimeout(() => setPhase(index + 1), time));
    const done = window.setTimeout(onDone, 5000);
    return () => {
      timers.forEach(window.clearTimeout);
      window.clearTimeout(done);
    };
  }, [onDone]);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center overflow-hidden bg-void">
      <div className="absolute inset-0 grid-bg scale-110 transition-transform duration-[3000ms]" style={{ transform: phase >= 2 ? "scale(0.86)" : "scale(1.08)" }} />
      <NeonParticleField />
      <CyberScanLine />
      <div className="relative z-10 w-full max-w-3xl px-5 text-center">
        <div className={`mx-auto h-52 w-52 rounded-full border border-neon/40 bg-[radial-gradient(circle,rgba(0,229,255,.28),rgba(124,77,255,.08),transparent_64%)] blur-[1px] transition-all duration-1000 ${phase >= 2 ? "scale-[2.7] opacity-80" : "scale-100 opacity-40"}`} />
        <div className="absolute inset-0 flex items-center justify-center">
          <div>
            {phase < 1 && (
              <div>
                <h1 className="text-4xl font-black text-neon md:text-6xl">{t("IDENTITY VERIFIED")}</h1>
                <p className="mt-3 text-textWeak">{t("身份验证通过")} • {username}</p>
              </div>
            )}
            {phase >= 1 && phase < 3 && (
              <div>
                <AccessLevelBadge level={plan} />
                <h1 className="mt-5 text-3xl font-black text-textMain md:text-5xl">{t("MEMBERSHIP ACTIVE")}</h1>
                <p className="mt-3 text-neon">{t("SYSTEM MODULES LOADING...")}</p>
                <div className="mt-6 grid gap-2 text-left">
                  {modules.map((module, index) => (
                    <div key={module} className="flex items-center justify-between rounded-xl border border-neon/20 bg-neon/5 px-4 py-2" style={{ opacity: phase >= 1 ? 1 : 0, transitionDelay: `${index * 120}ms` }}>
                      <span className="text-textWeak">{t(module)}</span>
                      <span className="font-mono text-success">{t("ONLINE")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {phase >= 3 && (
              <div className="animate-pulseGlow rounded-3xl border border-neon/40 bg-[#111827]/70 p-8 backdrop-blur-2xl">
                <h1 className="text-4xl font-black text-textMain md:text-6xl">{t("WELCOME TO SITE FACTORY OS")}</h1>
                <p className="mt-4 text-textWeak">{t("Control dashboard booting...")}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
