const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api/v1";

export function getToken() {
  return localStorage.getItem("sfs_token") || "";
}

export function getUserId() {
  return localStorage.getItem("sfs_user_id") || "";
}

export function setSession(session: { token: string; user: { user_id: string; username: string; role?: string }; membership?: any }) {
  localStorage.setItem("sfs_token", session.token);
  if ((session as any).refresh_token) localStorage.setItem("sfs_refresh_token", (session as any).refresh_token);
  localStorage.setItem("sfs_user_id", session.user.user_id);
  localStorage.setItem("sfs_username", session.user.username);
  localStorage.setItem("sfs_role", session.user.role || "operator");
  if (session.membership) localStorage.setItem("sfs_membership", JSON.stringify(session.membership));
}

export function clearSession() {
  localStorage.removeItem("sfs_token");
  localStorage.removeItem("sfs_refresh_token");
  localStorage.removeItem("sfs_user_id");
  localStorage.removeItem("sfs_username");
  localStorage.removeItem("sfs_role");
  localStorage.removeItem("sfs_membership");
}

function withUser(payload: Record<string, unknown> = {}) {
  const userId = getUserId();
  return userId ? { ...payload, user_id: userId } : payload;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers || {})
    },
    ...options
  });
  const body = await response.json();
  if (!response.ok && body?.error?.error_code === "AUTH_TOKEN_EXPIRED" && path !== "/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, options);
  }
  if (!response.ok) {
    if (body?.error?.error_code === "AUTH_TOKEN_EXPIRED" || body?.error?.error_code === "AUTH_TOKEN_INVALID" || body?.error?.error_code === "AUTH_UNAUTHORIZED") {
      clearSession();
      window.dispatchEvent(new CustomEvent("sfs-auth-expired"));
    }
    throw body;
  }
  return body as T;
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("sfs_refresh_token");
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  if (!response.ok) {
    clearSession();
    window.dispatchEvent(new CustomEvent("sfs-auth-expired"));
    return false;
  }
  setSession(await response.json());
  return true;
}

export const api = {
  health: () => request<{ status: string }>("/system/health"),
  systemStatus: () => request<{ sites: number; sites_active: number; deployments: number; errors: number; dns_issues: number; language_gaps: number; tasks_running: number; tasks_failed: number }>("/system/status"),
  sites: () => request<{ items: any[] }>("/sites"),
  site: (siteId: string) => request<any>(`/sites/${siteId}`),
  tasks: () => request<{ items: any[] }>("/tasks"),
  retryTask: (taskId: string) => request<any>(`/tasks/${taskId}/retry`, { method: "POST" }),
  errors: () => request<{ items: any[] }>("/errors"),
  deployments: () => request<{ items: any[] }>("/deployments"),
  auditLogs: () => request<{ items: any[] }>("/audit-logs"),
  membershipPlans: () => request<{ plans: any[] }>("/membership/plans"),
  login: (username: string, password: string, captcha?: { captcha_id: string; captcha_answer: string }) => request<any>("/auth/login", { method: "POST", body: JSON.stringify({ username, password, ...(captcha || {}) }) }),
  refresh: (refresh_token: string) => request<any>("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token }) }),
  register: (username: string, password: string, email?: string) => request<any>("/auth/register", { method: "POST", body: JSON.stringify({ username, password, email, trial_days: 3 }) }),
  createSite: (payload: Record<string, unknown>) => request<any>("/sites", { method: "POST", body: JSON.stringify(withUser(payload)) }),
  cloneSite: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/clone`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  pauseSite: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/pause`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  resumeSite: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/resume`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  deleteSiteRequest: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/delete-request`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  deleteSiteConfirm: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/delete-confirm`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  domains: (siteId: string) => request<{ items: any[] }>(`/sites/${siteId}/domains`),
  dnsCheck: (domain: string, payload: Record<string, unknown>) => request<any>(`/domains/${domain}/ns-check`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  articles: (siteId: string) => request<{ items: any[] }>(`/sites/${siteId}/articles`),
  createArticle: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/articles`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  publishArticle: (articleId: string, payload: Record<string, unknown>) => request<any>(`/articles/${articleId}/publish`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  products: (siteId: string) => request<{ items: any[] }>(`/sites/${siteId}/products`),
  createProduct: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/products`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  publishProduct: (productId: string, payload: Record<string, unknown>) => request<any>(`/products/${productId}/publish`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  payments: (siteId: string) => request<{ items: any[] }>(`/sites/${siteId}/payments`),
  createPayment: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/payments`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  bindPayment: (productId: string, payload: Record<string, unknown>) => request<any>(`/products/${productId}/payment-bind`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  createBulkJob: (payload: Record<string, unknown>) => request<any>("/bulk/jobs", { method: "POST", body: JSON.stringify(withUser(payload)) }),
  bulkScan: (jobId: string, payload: Record<string, unknown>) => request<any>(`/bulk/jobs/${jobId}/scan`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  bulkValidate: (jobId: string, payload: Record<string, unknown>) => request<any>(`/bulk/jobs/${jobId}/validate`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  bulkPreview: (jobId: string) => request<any>(`/bulk/jobs/${jobId}/preview`, { method: "POST" }),
  bulkExecute: (jobId: string, payload: Record<string, unknown>) => request<any>(`/bulk/jobs/${jobId}/execute`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  bulkRetryFailed: (jobId: string, payload: Record<string, unknown>) => request<any>(`/bulk/jobs/${jobId}/retry-failed`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  pages: (siteId: string) => request<{ items: any[] }>(`/sites/${siteId}/pages`),
  page: (pageId: string) => request<any>(`/pages/${pageId}`),
  createPage: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/pages`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  updatePage: (pageId: string, payload: Record<string, unknown>) => request<any>(`/pages/${pageId}`, { method: "PATCH", body: JSON.stringify(withUser(payload)) }),
  publishPage: (pageId: string, payload: Record<string, unknown>) => request<any>(`/pages/${pageId}/publish`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  rollbackPage: (pageId: string, payload: Record<string, unknown>) => request<any>(`/pages/${pageId}/rollback`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  enableLanguage: (siteId: string, code: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/i18n/languages/${code}/enable`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  serviceRequest: (payload: Record<string, unknown>) => request<any>("/membership/service-requests", { method: "POST", body: JSON.stringify(withUser(payload)) }),
  serviceRequests: () => request<{ items: any[] }>("/membership/service-requests"),
  markServiceRequestPaid: (requestId: string, payload: Record<string, unknown>) => request<any>(`/admin/billing/service-requests/${requestId}/mark-paid`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  activateServiceRequest: (requestId: string, payload: Record<string, unknown>) => request<any>(`/admin/billing/service-requests/${requestId}/activate`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  rejectServiceRequest: (requestId: string, payload: Record<string, unknown>) => request<any>(`/admin/billing/service-requests/${requestId}/reject`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  activateLicense: (payload: Record<string, unknown>) => request<any>("/membership/license-codes/activate", { method: "POST", body: JSON.stringify({ ...payload, user_id: payload.user_id || getUserId() }) }),
  activateLicenseKey: (payload: Record<string, unknown>) => request<any>("/license/activate", { method: "POST", body: JSON.stringify(payload) }),
  generateLicense: (payload: Record<string, unknown>) => request<any>("/admin/billing/license-codes", { method: "POST", body: JSON.stringify(payload) }),
  adminLicenses: () => request<{ items: any[] }>("/admin/billing/license-codes"),
  createAdminLicense: (payload: Record<string, unknown>) => request<any>("/admin/license/create", { method: "POST", body: JSON.stringify(payload) }),
  adminActivateUser: (payload: Record<string, unknown>) => request<any>("/admin/user/activate", { method: "POST", body: JSON.stringify(payload) }),
  createSeo: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/seo`, { method: "PATCH", body: JSON.stringify(withUser(payload)) }),
  siteSeo: (siteId: string) => request<any>(`/sites/${siteId}/seo`),
  generateSitemap: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/sitemap/generate`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  deploy: (siteId: string, payload: Record<string, unknown>) => request<any>(`/sites/${siteId}/deployments`, { method: "POST", body: JSON.stringify(withUser(payload)) }),
  deployGithub: (siteId: string, payload: Record<string, unknown>) => request<any>("/deploy/github", { method: "POST", body: JSON.stringify(withUser({ ...payload, site_id: siteId })) }),
  deployStatus: (siteId: string) => request<any>(`/deploy/status/${siteId}`),
  deployLogs: (siteId: string) => request<any>(`/deploy/logs/${siteId}`),
  templateLibrary: () => request<{ items: any[] }>("/builder/templates")
};

export function errorText(error: any) {
  const code = error?.error?.error_code || error?.error_code;
  return code ? `errors.${code}` : "errors.UNKNOWN_ERROR";
}
