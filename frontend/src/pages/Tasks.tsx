import { Check, RotateCcw, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { TaskTimeline } from "../components/TaskTimeline";
import { tasks } from "../data/mockData";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";
import { useI18n } from "../i18n";

type Props = { onToast: (message: string) => void };

const statuses = ["pending", "queued", "running", "waiting_confirm", "retrying", "success", "failed", "cancelled", "rollback_running", "rollback_success", "rollback_failed"];

export function Tasks({ onToast }: Props) {
  const { t } = useI18n();
  const liveTasks = useApiData(api.tasks, { items: tasks });
  const [refresh, setRefresh] = useState(0);
  const liveTasksFresh = useApiData(api.tasks, { items: tasks }, [refresh]);
  const retry = async (taskId: string) => {
    try {
      await api.retryTask(taskId);
      onToast(`${t("TASK_RETRY OK")} ${taskId}`);
      setRefresh((value) => value + 1);
    } catch (error) {
      onToast(errorText(error));
    }
  };
  const taskRows = liveTasksFresh.data.items.map((task: any) => ({
    ...task,
    type: task.type || task.task_type,
    progress: task.progress ?? 0,
    current_node: task.current_node || "TaskCreateNode",
    node_logs: task.node_logs || ["Task loaded from API"],
    retry_count: task.retry_count ?? 0,
    error_code: task.error_code || ""
  }));
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Execution Fabric")}</p>
        <h1 className="page-title">{t("Tasks")}</h1>
      </div>
      <GlassCard className="p-4">
        <div className="flex flex-wrap gap-2">
          {statuses.map((status) => <StatusBadge key={status} status={status} />)}
        </div>
      </GlassCard>
      <div className="grid gap-4 xl:grid-cols-[1fr_.85fr]">
        <GlassCard className="p-4">
          <div className="overflow-x-auto">
            <table className="cyber-table">
              <thead><tr><th>{t("task_id")}</th><th>{t("type")}</th><th>{t("site")}</th><th>{t("node")}</th><th>{t("progress")}</th><th>{t("status")}</th><th>{t("actions")}</th></tr></thead>
              <tbody>
                {taskRows.map((task) => (
                  <tr key={task.task_id}>
                    <td className="font-mono text-neon">{task.task_id}</td>
                    <td>{task.type}</td>
                    <td>{task.site_id}</td>
                    <td>{task.current_node}</td>
                    <td><div className="h-2 w-28 rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-neon to-plasma" style={{ width: `${task.progress}%` }} /></div></td>
                    <td><StatusBadge status={task.status} /></td>
                    <td><div className="flex gap-2"><NeonButton tone="ghost" data-testid={`task-retry-${task.task_id}`} onClick={() => retry(task.task_id)}><RotateCcw size={14} /></NeonButton><NeonButton tone="danger" onClick={() => onToast(`${t("Cancel")} ${task.task_id}`)}><X size={14} /></NeonButton><NeonButton tone="success" onClick={() => onToast(`${t("Confirm")} ${task.task_id}`)}><Check size={14} /></NeonButton></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("Task Detail")}</h2>
          <div className="mt-4 space-y-2 text-sm text-textWeak">
            <p>{t("task_id")}: <span className="font-mono text-neon">{taskRows[0]?.task_id}</span></p>
            <p>{t("request_id")}: {taskRows[0]?.request_id}</p>
            <p>{t("trace_id")}: {taskRows[0]?.trace_id}</p>
            <p>{t("error_code")}: <span className="text-danger">{taskRows[0]?.error_code}</span></p>
            <p>{t("retry_count")}: {taskRows[0]?.retry_count}</p>
          </div>
          <div className="mt-5">
            <TaskTimeline logs={taskRows[0]?.node_logs || []} />
          </div>
          <NeonButton className="mt-5 w-full" tone="purple" onClick={() => onToast(`${t("Rollback")} ${taskRows[0]?.task_id || ""}`)} data-testid="task-rollback-button"><ShieldCheck size={15} />{t("Rollback")}</NeonButton>
        </GlassCard>
      </div>
    </div>
  );
}
