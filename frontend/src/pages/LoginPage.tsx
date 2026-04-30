import { KeyRound, MessageCircle, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { NeonButton } from "../components/NeonButton";
import { NeonParticleField } from "../components/NeonParticleField";
import { api, errorText, setSession } from "../api/client";
import { languageOptions, type LanguageCode, useI18n } from "../i18n";

type Props = {
  onLogin: (username: string) => void;
  onToast: (message: string) => void;
};

export function LoginPage({ onLogin, onToast }: Props) {
  const { language, setLanguage, t } = useI18n();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("candy2000");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("candy2000");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [captcha, setCaptcha] = useState<{ captcha_id: string; question: string } | null>(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async () => {
    setLoading(true);
    try {
      if (mode === "register") {
        if (password.length < 6) {
          onToast("errors.PASSWORD_TOO_SHORT");
          return;
        }
        if (password !== confirmPassword) {
          onToast("errors.PASSWORD_CONFIRM_MISMATCH");
          return;
        }
        await api.register(username, password, email);
      }
      const session = await api.login(username, password, captcha ? { captcha_id: captcha.captcha_id, captcha_answer: captchaAnswer } : undefined);
      setSession(session);
      setCaptcha(null);
      setCaptchaAnswer("");
      onLogin(username);
    } catch (error: any) {
      const code = error?.error?.error_code;
      if (code === "CAPTCHA_REQUIRED") {
        setCaptcha(error.error.details?.captcha || null);
        onToast("errors.CAPTCHA_REQUIRED");
      } else if (code === "LOGIN_RATE_LIMITED") {
        onToast("errors.LOGIN_RATE_LIMITED");
      } else {
        onToast(errorText(error));
      }
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void p-4">
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as LanguageCode)}
        className="absolute right-4 top-4 z-20 h-10 rounded-lg border border-neon/20 bg-[#101827] px-3 text-sm text-textMain outline-none focus:border-neon"
        aria-label={t("Language")}
      >
        {languageOptions.map((item) => (
          <option key={item.code} value={item.code}>{item.code} · {item.name}</option>
        ))}
      </select>
      <div className="absolute inset-0 grid-bg" />
      <NeonParticleField />
      <div className="relative z-10 grid w-full max-w-6xl overflow-hidden rounded-[32px] border border-neon/20 bg-[#111827]/55 shadow-neon backdrop-blur-2xl lg:grid-cols-[1.05fr_.95fr]">
        <div className="relative min-h-[520px] overflow-hidden p-8 md:p-12">
          <div className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-neon/15 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-plasma/15 blur-3xl" />
          <div className="relative">
            <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-3xl border border-neon/40 bg-neon/10 text-neon shadow-neon">
              <ShieldCheck size={34} />
            </div>
            <p className="page-kicker">{t("Website Factory Control System")}</p>
            <h1 className="mt-3 text-5xl font-black leading-tight text-textMain md:text-7xl">{t("Site Factory OS")}</h1>
            <p className="mt-5 max-w-xl text-textWeak">{t("Login launches a membership-aware control cockpit: AuthNode, MembershipNode, QuotaNode, PermissionNode, then Task Engine.")}</p>
            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              {["Manual payment only", "License code activation", "Trial / Pro / Enterprise", "Portal Boot Sequence"].map((item) => (
                <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-textWeak">
                  <Sparkles className="mb-2 text-neon" size={18} />
                  {t(item)}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="border-t border-white/10 bg-[#0A0F1C]/40 p-6 md:p-10 lg:border-l lg:border-t-0">
          <h2 className="text-2xl font-black text-textMain">{t(mode === "login" ? "Enter Control Cabin" : "login.create_account")}</h2>
          <p className="mt-2 text-sm text-textWeak">{t(mode === "login" ? "账号密码或 Telegram 绑定登录，进入前验证会员状态。" : "login.register_hint")}</p>
          <div className="mt-8 space-y-5">
            <label><span className="form-label">{t("账号 / 邮箱")}</span><input className="form-input" data-testid="login-username" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
            {mode === "register" && <label><span className="form-label">{t("Email")}</span><input className="form-input" data-testid="register-email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>}
            <label><span className="form-label">{t("密码")}</span><input className="form-input" data-testid="login-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {mode === "register" && <label><span className="form-label">{t("login.confirm_password")}</span><input className="form-input" data-testid="register-confirm-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>}
            {captcha && (
              <label>
                <span className="form-label">{t("login.captcha")}: {captcha.question}</span>
                <input className="form-input" value={captchaAnswer} onChange={(event) => setCaptchaAnswer(event.target.value)} />
              </label>
            )}
            <NeonButton className="w-full" onClick={submit} disabled={loading} data-testid="login-submit"><KeyRound size={16} />{loading ? t("登录中...") : t(mode === "login" ? "登录" : "login.register_and_enter")}</NeonButton>
            <NeonButton tone="ghost" className="w-full" onClick={() => { const next = mode === "login" ? "register" : "login"; setMode(next); setUsername(next === "login" ? "candy2000" : ""); setPassword(next === "login" ? "candy2000" : ""); setConfirmPassword(""); setEmail(""); setCaptcha(null); }}>{t(mode === "login" ? "login.no_account" : "login.have_account")}</NeonButton>
            <div className="grid grid-cols-2 gap-2">
              <NeonButton tone="purple" onClick={() => onToast(t("客服开通申请已打开"))}><MessageCircle size={15} />{t("联系客服开通")}</NeonButton>
              <NeonButton tone="ghost" onClick={() => onToast(t("激活码输入框已打开"))}>{t("输入激活码")}</NeonButton>
            </div>
            <NeonButton tone="ghost" className="w-full" onClick={() => onToast(t("Telegram bind login waiting"))}>{t("Telegram 绑定登录")}</NeonButton>
          </div>
        </div>
      </div>
    </div>
  );
}
