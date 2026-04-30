import { Check, CircleDot, Loader2 } from "lucide-react";
import { useI18n } from "../i18n";

type Props = {
  logs: string[];
};

export function TaskTimeline({ logs }: Props) {
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      {logs.map((log, index) => {
        const Icon = index === logs.length - 1 ? Loader2 : index === 0 ? CircleDot : Check;
        return (
          <div key={log} className="flex gap-3">
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-neon/30 bg-neon/10 text-neon">
              <Icon size={14} className={index === logs.length - 1 ? "animate-spin" : ""} />
            </div>
            <p className="pt-1 text-sm text-textWeak">{t(log)}</p>
          </div>
        );
      })}
    </div>
  );
}
