import { ChevronRight, ClipboardList, ShieldAlert } from "lucide-react";
import { errors, tasks } from "../data/mockData";
import { useI18n } from "../i18n";
import { StatusBadge } from "./StatusBadge";
import { TaskTimeline } from "./TaskTimeline";

type Props = {
  open: boolean;
  onToggle: () => void;
};

export function RightDrawer({ open, onToggle }: Props) {
  const { t } = useI18n();
  const task = tasks.find((item) => item.status === "running") ?? tasks[0];
  return (
    <aside
      className={`fixed inset-y-0 right-0 z-40 w-[360px] border-l border-white/10 bg-[#0A0F1C]/90 p-4 backdrop-blur-2xl transition-transform ${
        open ? "translate-x-0" : "translate-x-[310px]"
      } hidden xl:block`}
    >
      <button className="absolute -left-10 top-24 rounded-l-xl border border-r-0 border-white/10 bg-[#111827]/90 p-2 text-neon" onClick={onToggle}>
        <ChevronRight className={open ? "" : "rotate-180"} />
      </button>
      <div className="flex items-center gap-2 text-textMain">
        <ClipboardList size={19} className="text-neon" />
        <h2 className="font-bold">{t("Live Task Feed")}</h2>
      </div>
      <div className="mt-4 rounded-2xl border border-neon/20 bg-neon/5 p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="font-mono text-xs text-textWeak">{task.task_id}</p>
            <p className="mt-1 font-semibold text-textMain">{task.type}</p>
          </div>
          <StatusBadge status={task.status} />
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-gradient-to-r from-neon to-plasma" style={{ width: `${task.progress}%` }} />
        </div>
        <div className="mt-4">
          <TaskTimeline logs={task.node_logs} />
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2 text-textMain">
        <ShieldAlert size={19} className="text-danger" />
        <h2 className="font-bold">{t("Error Telemetry")}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {errors.slice(0, 3).map((error) => (
          <div key={error.id} className="rounded-2xl border border-danger/20 bg-danger/5 p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs text-danger">{error.error_code}</span>
              <StatusBadge status={error.level} />
            </div>
            <p className="mt-2 text-sm text-textWeak">{t(`errors.${error.error_code}`) === `errors.${error.error_code}` ? t(error.message) : t(`errors.${error.error_code}`)}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}
