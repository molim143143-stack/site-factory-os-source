import type { LucideIcon } from "lucide-react";
import { GlassCard } from "./GlassCard";

type Props = {
  label: string;
  value: string | number;
  hint: string;
  icon: LucideIcon;
  tone?: "cyan" | "purple" | "green" | "amber" | "red";
};

export function StatCard({ label, value, hint, icon: Icon, tone = "cyan" }: Props) {
  const colors = {
    cyan: "text-neon bg-neon/10",
    purple: "text-[#c8b8ff] bg-plasma/10",
    green: "text-success bg-success/10",
    amber: "text-warning bg-warning/10",
    red: "text-danger bg-danger/10"
  };
  return (
    <GlassCard className="group p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-textWeak">{label}</p>
          <div className="mt-3 text-3xl font-black text-textMain">{value}</div>
          <p className="mt-2 text-sm text-textWeak">{hint}</p>
        </div>
        <div className={`rounded-xl p-3 ${colors[tone]} transition-transform group-hover:scale-110`}>
          <Icon size={22} />
        </div>
      </div>
    </GlassCard>
  );
}
