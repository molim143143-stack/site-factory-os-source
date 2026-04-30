import { AlertTriangle, CheckCircle2, Download, FileArchive, Play, RotateCcw, ScanLine, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { api, errorText } from "../api/client";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

type Props = {
  siteId: string;
  onToast: (message: string) => void;
};

const steps = ["Scan", "Validate", "Preview", "Execute"];

export function BulkImport({ siteId, onToast }: Props) {
  const { t } = useI18n();
  const [activeStep, setActiveStep] = useState(0);
  const [rootPath, setRootPath] = useState(`C:\\bot\\web\\sample_data\\productization_v2\\bulk_good`);
  const [jobId, setJobId] = useState("");
  const [scan, setScan] = useState<any>(null);
  const [validate, setValidate] = useState<any>(null);
  const [preview, setPreview] = useState<any>(null);
  const [execute, setExecute] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const membership = JSON.parse(localStorage.getItem("sfs_membership") || "{\"plan\":\"trial\"}");
  const canExecute = membership.plan !== "trial" && Boolean(membership.can_use_bulk_import ?? true);

  const run = async (label: string, fn: () => Promise<any>, step: number) => {
    setBusy(label);
    try {
      const result = await fn();
      onToast(`${label} OK`);
      setActiveStep(step);
      return result;
    } catch (error) {
      onToast(errorText(error));
      return null;
    } finally {
      setBusy("");
    }
  };

  const createJob = async () => {
    const result = await run("BULK_JOB_CREATE", () => api.createBulkJob({ request_id: `web_bulk_job_${Date.now()}`, root_path: rootPath }), 0);
    if (result?.bulk_job?.bulk_job_id) setJobId(result.bulk_job.bulk_job_id);
  };
  const scanJob = async () => jobId && setScan(await run("BULK_SCAN", () => api.bulkScan(jobId, { request_id: `web_bulk_scan_${Date.now()}`, site_id: siteId }), 0));
  const validateJob = async () => jobId && setValidate(await run("BULK_VALIDATE", () => api.bulkValidate(jobId, { request_id: `web_bulk_validate_${Date.now()}`, site_id: siteId }), 1));
  const previewJob = async () => jobId && setPreview(await run("BULK_PREVIEW", () => api.bulkPreview(jobId), 2));
  const executeJob = async () => jobId && setExecute(await run("BULK_EXECUTE", () => api.bulkExecute(jobId, { request_id: `web_bulk_execute_${Date.now()}`, site_id: siteId }), 3));
  const retryFailed = async () => jobId && setPreview(await run("BULK_RETRY_FAILED", () => api.bulkRetryFailed(jobId, { request_id: `web_bulk_retry_${Date.now()}`, site_id: siteId }), activeStep));

  const errors = validate?.errors || preview?.errors || [];
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Bulk Pipeline")}</p>
        <h1 className="page-title">{t("Bulk Import")}</h1>
      </div>
      <GlassCard className="border-warning/25 bg-warning/5 p-4" glow="purple">
        <div className="flex gap-3">
          <ShieldCheck className="mt-1 text-warning" />
          <div>
            <h2 className="font-bold text-warning">{t("Bulk Import must validate everything before execution.")}</h2>
            <p className="mt-1 text-sm text-textWeak">{t("Bulk Import 必须先全部校验通过，才能执行导入。禁止边导入边报错。")}</p>
          </div>
        </div>
      </GlassCard>
      <div className="grid gap-4 xl:grid-cols-[.9fr_1.1fr]">
        <GlassCard className="p-5">
          <div className="flex min-h-[260px] flex-col items-center justify-center rounded-3xl border border-dashed border-neon/35 bg-neon/5 p-6 text-center">
            <FileArchive size={48} className="text-neon animate-float" />
            <h2 className="mt-4 text-xl font-black text-textMain">{t("bulk_upload folder path")}</h2>
            <input type="file" className="mt-4 text-sm text-textWeak" data-testid="bulk-file-upload" onChange={(event) => event.target.files?.[0] && onToast(`BULK_FILE_SELECTED ${event.target.files[0].name}`)} />
            <input className="form-input mt-4" data-testid="bulk-root-path" value={rootPath} onChange={(event) => setRootPath(event.target.value)} />
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <NeonButton onClick={createJob} disabled={busy === "BULK_JOB_CREATE"} data-testid="bulk-create-job-button">{t("Create Job")}</NeonButton>
              <NeonButton tone="ghost" onClick={() => onToast(t("Example Structure"))} data-testid="bulk-example-structure-button"><Download size={15} />{t("Example Structure")}</NeonButton>
            </div>
            {jobId && <p className="mt-3 font-mono text-neon" data-testid="bulk-job-id">{jobId}</p>}
          </div>
        </GlassCard>
        <GlassCard className="p-5">
          <h2 className="mb-5 font-bold text-textMain">{t("Pipeline Stage")}</h2>
          <div className="grid gap-3 sm:grid-cols-4">
            {steps.map((step, index) => (
              <button key={step} onClick={() => setActiveStep(index)} className={`rounded-2xl border p-4 text-left transition ${index <= activeStep ? "border-neon/40 bg-neon/10 text-neon shadow-neon" : "border-white/10 bg-white/5 text-textWeak"}`}>
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl border border-current/30">
                  {index < activeStep ? <CheckCircle2 size={18} /> : <ScanLine size={18} />}
                </div>
                <p className="font-bold">{t(step)}</p>
              </button>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <NeonButton onClick={scanJob} data-testid="bulk-scan-button"><ScanLine size={15} />{t("Scan")}</NeonButton>
            <NeonButton tone="purple" onClick={validateJob} data-testid="bulk-validate-button">{t("Validate")}</NeonButton>
            <NeonButton tone="ghost" onClick={previewJob} data-testid="bulk-preview-button">{t("Preview")}</NeonButton>
            <NeonButton tone="success" onClick={executeJob} disabled={!canExecute} data-testid="bulk-execute-button"><Play size={15} />{t("Execute")}</NeonButton>
          </div>
          {!canExecute && <p className="mt-3 text-sm text-danger" data-testid="bulk-trial-disabled">{t("MEMBERSHIP_FEATURE_NOT_ALLOWED: Trial cannot execute Bulk Import.")}</p>}
          <pre className="mt-4 max-h-48 overflow-auto rounded-xl bg-black/30 p-3 text-xs text-textWeak" data-testid="bulk-result">{JSON.stringify({ scan, validate, preview, execute }, null, 2)}</pre>
        </GlassCard>
      </div>
      <GlassCard className="p-4" glow="danger">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 font-bold text-textMain"><AlertTriangle size={18} className="text-danger" />{t("Error Report")}</h2>
          <div className="flex gap-2"><a className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-white/10 px-3 text-sm text-textMain" href="/reports/bulk_result.json" download><Download size={15} />{t("Download Report")}</a><NeonButton tone="danger" onClick={retryFailed} data-testid="bulk-retry-failed-button"><RotateCcw size={15} />{t("Retry Failed Items")}</NeonButton></div>
        </div>
        <div className="overflow-x-auto">
          <table className="cyber-table">
            <thead><tr><th>{t("error_code")}</th><th>{t("message")}</th><th>{t("file")}</th><th>{t("line")}</th><th>{t("severity")}</th></tr></thead>
            <tbody>
              {errors.map((error: any) => (
                <tr key={`${error.error_code}-${error.file}`}>
                  <td className="font-mono text-danger">{error.error_code}</td>
                  <td>{error.message}</td>
                  <td className="font-mono text-neon">{error.file}</td>
                  <td>{error.line}</td>
                  <td><StatusBadge status="ERROR" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
