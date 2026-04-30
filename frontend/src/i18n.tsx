import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import en from "./i18n/locales/en.json";
import es from "./i18n/locales/es.json";
import vi from "./i18n/locales/vi.json";
import zhCN from "./i18n/locales/zh-CN.json";

export type LanguageCode = "en" | "zh-CN" | "es" | "pt" | "ur-Latn" | "hi" | "de" | "vi" | "ja";

export const languageOptions: { code: LanguageCode; name: string }[] = [
  { code: "en", name: "English" },
  { code: "zh-CN", name: "中文" },
  { code: "es", name: "Español" },
  { code: "pt", name: "Português" },
  { code: "ur-Latn", name: "Romanized Urdu" },
  { code: "hi", name: "Hindi" },
  { code: "de", name: "Deutsch" },
  { code: "vi", name: "Tiếng Việt" },
  { code: "ja", name: "日本語" }
];

type Dict = Record<string, Partial<Record<LanguageCode, string>>>;
type LocaleTree = Record<string, unknown>;

const localeTrees: Partial<Record<LanguageCode, LocaleTree>> = {
  en,
  "zh-CN": zhCN,
  es,
  vi
};

function lookupLocale(tree: LocaleTree | undefined, key: string): string | undefined {
  if (!tree) return undefined;
  const direct = tree[key];
  if (typeof direct === "string") return direct;
  if (!key.includes(".")) return undefined;
  let value: unknown = tree;
  for (const part of key.split(".")) {
    if (!value || typeof value !== "object" || !(part in value)) return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return typeof value === "string" ? value : undefined;
}

const dict: Dict = {
  "System ready": { "zh-CN": "系统就绪", es: "Sistema listo", pt: "Sistema pronto", "ur-Latn": "System tayyar", hi: "सिस्टम तैयार", de: "System bereit", vi: "Hệ thống sẵn sàng", ja: "システム準備完了" },
  "Portal boot complete": { "zh-CN": "传送门启动完成", es: "Arranque del portal completo", pt: "Inicialização do portal concluída", "ur-Latn": "Portal boot mukammal", hi: "पोर्टल बूट पूरा", de: "Portalstart abgeschlossen", vi: "Khởi động cổng hoàn tất", ja: "ポータル起動完了" },
  "Dashboard": { "zh-CN": "控制台", es: "Panel", pt: "Painel", "ur-Latn": "Dashboard", hi: "डैशबोर्ड", de: "Dashboard", vi: "Bảng điều khiển", ja: "ダッシュボード" },
  "Sites": { "zh-CN": "网站", es: "Sitios", pt: "Sites", "ur-Latn": "Sites", hi: "साइटें", de: "Websites", vi: "Trang web", ja: "サイト" },
  "CMS": { "zh-CN": "内容管理", es: "CMS", pt: "CMS", "ur-Latn": "CMS", hi: "CMS", de: "CMS", vi: "CMS", ja: "CMS" },
  "DIY Builder": { "zh-CN": "DIY建站器", es: "Constructor DIY", pt: "Construtor DIY", "ur-Latn": "DIY Builder", hi: "DIY बिल्डर", de: "DIY-Builder", vi: "Trình dựng DIY", ja: "DIYビルダー" },
  "Bulk Import": { "zh-CN": "批量导入", es: "Importación masiva", pt: "Importação em massa", "ur-Latn": "Bulk Import", hi: "बल्क आयात", de: "Massenimport", vi: "Nhập hàng loạt", ja: "一括インポート" },
  "Languages": { "zh-CN": "多语言", es: "Idiomas", pt: "Idiomas", "ur-Latn": "Zubanein", hi: "भाषाएँ", de: "Sprachen", vi: "Ngôn ngữ", ja: "言語" },
  "SEO": { "zh-CN": "SEO", es: "SEO", pt: "SEO", "ur-Latn": "SEO", hi: "SEO", de: "SEO", vi: "SEO", ja: "SEO" },
  "DNS / Domain": { "zh-CN": "DNS / 域名", es: "DNS / Dominio", pt: "DNS / Domínio", "ur-Latn": "DNS / Domain", hi: "DNS / डोमेन", de: "DNS / Domain", vi: "DNS / Tên miền", ja: "DNS / ドメイン" },
  "Deployments": { "zh-CN": "部署记录", es: "Despliegues", pt: "Implantações", "ur-Latn": "Deployments", hi: "डिप्लॉयमेंट", de: "Bereitstellungen", vi: "Triển khai", ja: "デプロイ" },
  "Tasks": { "zh-CN": "任务中心", es: "Tareas", pt: "Tarefas", "ur-Latn": "Tasks", hi: "कार्य", de: "Aufgaben", vi: "Tác vụ", ja: "タスク" },
  "Error Center": { "zh-CN": "错误中心", es: "Centro de errores", pt: "Centro de erros", "ur-Latn": "Error Center", hi: "त्रुटि केंद्र", de: "Fehlerzentrum", vi: "Trung tâm lỗi", ja: "エラーセンター" },
  "Payment Links": { "zh-CN": "支付链接", es: "Enlaces de pago", pt: "Links de pagamento", "ur-Latn": "Payment Links", hi: "भुगतान लिंक", de: "Zahlungslinks", vi: "Liên kết thanh toán", ja: "支払いリンク" },
  "Membership": { "zh-CN": "会员中心", es: "Membresía", pt: "Assinatura", "ur-Latn": "Membership", hi: "सदस्यता", de: "Mitgliedschaft", vi: "Hội viên", ja: "メンバーシップ" },
  "Admin Billing": { "zh-CN": "人工开通管理", es: "Facturación admin", pt: "Faturamento admin", "ur-Latn": "Admin Billing", hi: "एडमिन बिलिंग", de: "Admin-Abrechnung", vi: "Quản lý thanh toán", ja: "管理者課金" },
  "Users & Roles": { "zh-CN": "用户与角色", es: "Usuarios y roles", pt: "Usuários e funções", "ur-Latn": "Users & Roles", hi: "उपयोगकर्ता और भूमिकाएँ", de: "Benutzer & Rollen", vi: "Người dùng & vai trò", ja: "ユーザーと権限" },
  "Settings": { "zh-CN": "系统设置", es: "Configuración", pt: "Configurações", "ur-Latn": "Settings", hi: "सेटिंग्स", de: "Einstellungen", vi: "Cài đặt", ja: "設定" },
  "AI Website Factory Control Plane": { "zh-CN": "AI 网站工厂控制平面", es: "Plano de control de fábrica web IA", pt: "Plano de controle da fábrica web IA", "ur-Latn": "AI Website Factory Control Plane", hi: "AI वेबसाइट फैक्टरी नियंत्रण", de: "KI-Webfabrik-Kontrollzentrum", vi: "Bảng điều khiển nhà máy web AI", ja: "AIウェブ工場制御面" },
  "Multi-site publishing, deployment telemetry, DNS intelligence, bulk validation, and multilingual release control in one command surface.": { "zh-CN": "多站点发布、部署监控、DNS 智能检测、批量校验与多语言发布控制", es: "Publicación multi-sitio, telemetría de despliegue, DNS inteligente, validación masiva y control multilingüe.", vi: "Xuất bản nhiều site, giám sát triển khai, DNS thông minh, xác thực hàng loạt và phát hành đa ngôn ngữ." },
  "Site Factory OS": { "zh-CN": "Site Factory OS", es: "Site Factory OS", pt: "Site Factory OS", "ur-Latn": "Site Factory OS", hi: "Site Factory OS", de: "Site Factory OS", vi: "Site Factory OS", ja: "Site Factory OS" },
  "Total Sites": { "zh-CN": "网站总数", es: "Sitios totales", pt: "Total de sites", "ur-Latn": "Total Sites", hi: "कुल साइटें", de: "Websites gesamt", vi: "Tổng số site", ja: "サイト総数" },
  "Active": { "zh-CN": "活跃", es: "Activo", pt: "Ativo", "ur-Latn": "Active", hi: "सक्रिय", de: "Aktiv", vi: "Hoạt động", ja: "アクティブ" },
  "DNS Issues": { "zh-CN": "DNS 异常", es: "Problemas DNS", pt: "Problemas DNS", "ur-Latn": "DNS Issues", hi: "DNS समस्याएँ", de: "DNS-Probleme", vi: "Sự cố DNS", ja: "DNS問題" },
  "Running Tasks": { "zh-CN": "运行中任务", es: "Tareas en ejecución", pt: "Tarefas em execução", "ur-Latn": "Running Tasks", hi: "चल रहे कार्य", de: "Laufende Aufgaben", vi: "Tác vụ đang chạy", ja: "実行中タスク" },
  "Failed Tasks": { "zh-CN": "失败任务", es: "Tareas fallidas", pt: "Tarefas falhadas", "ur-Latn": "Failed Tasks", hi: "विफल कार्य", de: "Fehlgeschlagene Aufgaben", vi: "Tác vụ lỗi", ja: "失敗タスク" },
  "Language Gaps": { "zh-CN": "语言缺失", es: "Faltantes de idioma", pt: "Lacunas de idioma", "ur-Latn": "Language Gaps", hi: "भाषा अंतर", de: "Sprachlücken", vi: "Thiếu ngôn ngữ", ja: "翻訳不足" },
  "Create Site": { "zh-CN": "创建网站", es: "Crear sitio", pt: "Criar site", "ur-Latn": "Site banao", hi: "साइट बनाएँ", de: "Website erstellen", vi: "Tạo site", ja: "サイト作成" },
  "Publish Article": { "zh-CN": "发布文章", es: "Publicar artículo", pt: "Publicar artigo", "ur-Latn": "Article publish", hi: "लेख प्रकाशित करें", de: "Artikel veröffentlichen", vi: "Xuất bản bài viết", ja: "記事公開" },
  "Publish Product": { "zh-CN": "发布商品", es: "Publicar producto", pt: "Publicar produto", "ur-Latn": "Product publish", hi: "उत्पाद प्रकाशित करें", de: "Produkt veröffentlichen", vi: "Xuất bản sản phẩm", ja: "商品公開" },
  "Check DNS": { "zh-CN": "检测 DNS", es: "Comprobar DNS", pt: "Verificar DNS", "ur-Latn": "DNS check", hi: "DNS जाँचें", de: "DNS prüfen", vi: "Kiểm tra DNS", ja: "DNS確認" },
  "Search site_id, alias, task, trace...": { "zh-CN": "搜索 site_id、别名、任务、trace...", es: "Buscar site_id, alias, tarea, trace...", pt: "Buscar site_id, alias, tarefa, trace...", "ur-Latn": "site_id, alias, task, trace search...", hi: "site_id, alias, task, trace खोजें...", de: "site_id, Alias, Aufgabe, Trace suchen...", vi: "Tìm site_id, alias, tác vụ, trace...", ja: "site_id、別名、タスク、traceを検索..." },
  "Quick Create": { "zh-CN": "快捷创建", es: "Creación rápida", pt: "Criação rápida", "ur-Latn": "Quick Create", hi: "त्वरित निर्माण", de: "Schnellerstellen", vi: "Tạo nhanh", ja: "クイック作成" },
  "Manual Billing Gateway": { "zh-CN": "人工收款网关", es: "Pasarela de pago manual", pt: "Gateway de cobrança manual", "ur-Latn": "Manual Billing Gateway", hi: "मैनुअल बिलिंग गेटवे", de: "Manuelles Abrechnungsportal", vi: "Cổng thanh toán thủ công", ja: "手動課金ゲートウェイ" },
  "Current Plan": { "zh-CN": "当前套餐", es: "Plan actual", pt: "Plano atual", "ur-Latn": "Current Plan", hi: "वर्तमान योजना", de: "Aktueller Plan", vi: "Gói hiện tại", ja: "現在のプラン" },
  "Feature Permissions": { "zh-CN": "功能权限", es: "Permisos de función", pt: "Permissões de recursos", "ur-Latn": "Feature Permissions", hi: "सुविधा अनुमतियाँ", de: "Funktionsrechte", vi: "Quyền tính năng", ja: "機能権限" },
  "Opening Requests": { "zh-CN": "开通申请记录", es: "Solicitudes de activación", pt: "Solicitações de ativação", "ur-Latn": "Opening Requests", hi: "सक्रियण अनुरोध", de: "Freischaltungsanträge", vi: "Yêu cầu mở gói", ja: "開通申請" },
  "Enter Control Cabin": { "zh-CN": "进入控制舱", es: "Entrar a cabina de control", pt: "Entrar na cabine de controle", "ur-Latn": "Control Cabin mein dakhil", hi: "कंट्रोल केबिन में प्रवेश", de: "Kontrollkabine betreten", vi: "Vào khoang điều khiển", ja: "制御キャビンへ入る" },
  "Website Factory Control System": { "zh-CN": "网站工厂控制系统", es: "Sistema de control de fábrica web", pt: "Sistema de controle da fábrica web", "ur-Latn": "Website Factory Control System", hi: "वेबसाइट फैक्टरी नियंत्रण प्रणाली", de: "Webfabrik-Steuerungssystem", vi: "Hệ thống điều khiển nhà máy web", ja: "ウェブ工場制御システム" },
  "登录": { en: "Login", es: "Iniciar sesión", pt: "Entrar", "ur-Latn": "Login", hi: "लॉगिन", de: "Anmelden", vi: "Đăng nhập", ja: "ログイン" },
  "联系客服开通": { en: "Contact support to activate", es: "Contactar soporte", pt: "Contatar suporte", "ur-Latn": "Support se rabta", hi: "सपोर्ट से संपर्क करें", de: "Support kontaktieren", vi: "Liên hệ hỗ trợ", ja: "サポートへ連絡" },
  "输入激活码": { en: "Enter license code", es: "Ingresar código", pt: "Inserir código", "ur-Latn": "License code daalen", hi: "लाइसेंस कोड डालें", de: "Lizenzcode eingeben", vi: "Nhập mã kích hoạt", ja: "ライセンスコード入力" },
  "账号 / 邮箱": { en: "Account / Email", es: "Cuenta / Email", pt: "Conta / Email", "ur-Latn": "Account / Email", hi: "खाता / ईमेल", de: "Konto / E-Mail", vi: "Tài khoản / Email", ja: "アカウント / メール" },
  "密码": { en: "Password", es: "Contraseña", pt: "Senha", "ur-Latn": "Password", hi: "पासवर्ड", de: "Passwort", vi: "Mật khẩu", ja: "パスワード" },
  "IDENTITY VERIFIED": { "zh-CN": "身份验证通过", es: "IDENTIDAD VERIFICADA", pt: "IDENTIDADE VERIFICADA", "ur-Latn": "IDENTITY VERIFIED", hi: "पहचान सत्यापित", de: "IDENTITÄT BESTÄTIGT", vi: "ĐÃ XÁC MINH DANH TÍNH", ja: "本人確認完了" },
  "MEMBERSHIP ACTIVE": { "zh-CN": "会员状态有效", es: "MEMBRESÍA ACTIVA", pt: "ASSINATURA ATIVA", "ur-Latn": "MEMBERSHIP ACTIVE", hi: "सदस्यता सक्रिय", de: "MITGLIEDSCHAFT AKTIV", vi: "HỘI VIÊN ĐANG HOẠT ĐỘNG", ja: "メンバーシップ有効" },
  "SYSTEM MODULES LOADING...": { "zh-CN": "系统模块加载中...", es: "CARGANDO MÓDULOS...", pt: "CARREGANDO MÓDULOS...", "ur-Latn": "SYSTEM MODULES LOADING...", hi: "मॉड्यूल लोड हो रहे हैं...", de: "SYSTEMMODULE WERDEN GELADEN...", vi: "ĐANG TẢI MÔ-ĐUN...", ja: "システムモジュール読込中..." },
  "WELCOME TO SITE FACTORY OS": { "zh-CN": "欢迎进入 SITE FACTORY OS", es: "BIENVENIDO A SITE FACTORY OS", pt: "BEM-VINDO AO SITE FACTORY OS", "ur-Latn": "WELCOME TO SITE FACTORY OS", hi: "SITE FACTORY OS में स्वागत है", de: "WILLKOMMEN BEI SITE FACTORY OS", vi: "CHÀO MỪNG ĐẾN SITE FACTORY OS", ja: "SITE FACTORY OSへようこそ" }
};

const commonWords: Dict = {
  "Create": { "zh-CN": "创建", es: "Crear", pt: "Criar", "ur-Latn": "Create", hi: "बनाएँ", de: "Erstellen", vi: "Tạo", ja: "作成" },
  "Open": { "zh-CN": "打开", es: "Abrir", pt: "Abrir", "ur-Latn": "Open", hi: "खोलें", de: "Öffnen", vi: "Mở", ja: "開く" },
  "Edit": { "zh-CN": "编辑", es: "Editar", pt: "Editar", "ur-Latn": "Edit", hi: "संपादित", de: "Bearbeiten", vi: "Sửa", ja: "編集" },
  "Delete": { "zh-CN": "删除", es: "Eliminar", pt: "Excluir", "ur-Latn": "Delete", hi: "हटाएँ", de: "Löschen", vi: "Xóa", ja: "削除" },
  "Deploy": { "zh-CN": "部署", es: "Desplegar", pt: "Implantar", "ur-Latn": "Deploy", hi: "डिप्लॉय", de: "Bereitstellen", vi: "Triển khai", ja: "デプロイ" },
  "Clone": { "zh-CN": "克隆", es: "Clonar", pt: "Clonar", "ur-Latn": "Clone", hi: "क्लोन", de: "Klonen", vi: "Nhân bản", ja: "複製" },
  "Pause": { "zh-CN": "暂停", es: "Pausar", pt: "Pausar", "ur-Latn": "Pause", hi: "रोकें", de: "Pausieren", vi: "Tạm dừng", ja: "一時停止" },
  "Resume": { "zh-CN": "恢复", es: "Reanudar", pt: "Retomar", "ur-Latn": "Resume", hi: "फिर शुरू", de: "Fortsetzen", vi: "Tiếp tục", ja: "再開" },
  "Retry": { "zh-CN": "重试", es: "Reintentar", pt: "Tentar novamente", "ur-Latn": "Retry", hi: "पुनः प्रयास", de: "Wiederholen", vi: "Thử lại", ja: "再試行" },
  "Cancel": { "zh-CN": "取消", es: "Cancelar", pt: "Cancelar", "ur-Latn": "Cancel", hi: "रद्द", de: "Abbrechen", vi: "Hủy", ja: "キャンセル" },
  "Confirm": { "zh-CN": "确认", es: "Confirmar", pt: "Confirmar", "ur-Latn": "Confirm", hi: "पुष्टि", de: "Bestätigen", vi: "Xác nhận", ja: "確認" },
  "Rollback": { "zh-CN": "回滚", es: "Revertir", pt: "Reverter", "ur-Latn": "Rollback", hi: "रोलबैक", de: "Rollback", vi: "Khôi phục", ja: "ロールバック" },
  "Preview": { "zh-CN": "预览", es: "Vista previa", pt: "Prévia", "ur-Latn": "Preview", hi: "पूर्वावलोकन", de: "Vorschau", vi: "Xem trước", ja: "プレビュー" },
  "Execute": { "zh-CN": "执行", es: "Ejecutar", pt: "Executar", "ur-Latn": "Execute", hi: "निष्पादित", de: "Ausführen", vi: "Thực thi", ja: "実行" },
  "Validate": { "zh-CN": "校验", es: "Validar", pt: "Validar", "ur-Latn": "Validate", hi: "सत्यापित", de: "Validieren", vi: "Xác thực", ja: "検証" },
  "Scan": { "zh-CN": "扫描", es: "Escanear", pt: "Escanear", "ur-Latn": "Scan", hi: "स्कैन", de: "Scannen", vi: "Quét", ja: "スキャン" },
  "Status": { "zh-CN": "状态", es: "Estado", pt: "Status", "ur-Latn": "Status", hi: "स्थिति", de: "Status", vi: "Trạng thái", ja: "状態" },
  "Actions": { "zh-CN": "操作", es: "Acciones", pt: "Ações", "ur-Latn": "Actions", hi: "कार्रवाइयाँ", de: "Aktionen", vi: "Thao tác", ja: "操作" },
  "Language": { "zh-CN": "语言", es: "Idioma", pt: "Idioma", "ur-Latn": "Language", hi: "भाषा", de: "Sprache", vi: "Ngôn ngữ", ja: "言語" },
  "Search": { "zh-CN": "搜索", es: "Buscar", pt: "Buscar", "ur-Latn": "Search", hi: "खोज", de: "Suchen", vi: "Tìm kiếm", ja: "検索" }
};

Object.assign(dict, commonWords);

const dynamicPrefixes = [
  ["Quick create opened", { "zh-CN": "快捷创建已打开", es: "Creación rápida abierta", pt: "Criação rápida aberta", "ur-Latn": "Quick create khul gaya", hi: "त्वरित निर्माण खुला", de: "Schnellerstellung geöffnet", vi: "Đã mở tạo nhanh", ja: "クイック作成を開きました" }],
  ["Task drawer synced", { "zh-CN": "任务抽屉已同步", es: "Panel de tareas sincronizado", pt: "Gaveta de tarefas sincronizada", "ur-Latn": "Task drawer synced", hi: "कार्य पैनल सिंक हुआ", de: "Aufgabenleiste synchronisiert", vi: "Ngăn tác vụ đã đồng bộ", ja: "タスクドロワー同期済み" }],
  ["Error center opened", { "zh-CN": "错误中心已打开", es: "Centro de errores abierto", pt: "Centro de erros aberto", "ur-Latn": "Error center opened", hi: "त्रुटि केंद्र खुला", de: "Fehlerzentrum geöffnet", vi: "Đã mở trung tâm lỗi", ja: "エラーセンターを開きました" }],
  ["Portal boot complete", dict["Portal boot complete"]]
] as const;

type I18nContextValue = {
  language: LanguageCode;
  setLanguage: (language: LanguageCode) => void;
  t: (text: string | number | null | undefined) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function translate(text: string | number | null | undefined, language: LanguageCode): string {
  if (text === null || text === undefined) return "";
  const raw = String(text);
  const localeValue = lookupLocale(localeTrees[language], raw) ?? lookupLocale(localeTrees.en, raw);
  if (localeValue) return localeValue;
  if (language === "en") return raw;
  const exact = dict[raw]?.[language];
  if (exact) return exact;
  for (const [prefix, translations] of dynamicPrefixes) {
    if (raw.startsWith(prefix)) {
      return translations[language] ?? raw;
    }
  }
  if (raw.includes(" queued")) {
    const suffix = {
      "zh-CN": "任务已加入队列",
      es: "tarea en cola",
      pt: "tarefa enfileirada",
      "ur-Latn": "task queue mein hai",
      hi: "कार्य कतार में है",
      de: "Aufgabe wurde eingereiht",
      vi: "tác vụ đã vào hàng đợi",
      ja: "タスクをキューに追加しました"
    }[language];
    return suffix ? `${raw.split(" ")[0]} ${suffix}` : raw;
  }
  if (raw.includes(" opened")) {
    const suffix = {
      "zh-CN": "已打开",
      es: "abierto",
      pt: "aberto",
      "ur-Latn": "khul gaya",
      hi: "खुला",
      de: "geöffnet",
      vi: "đã mở",
      ja: "を開きました"
    }[language];
    return suffix ? `${raw.split(" ")[0]} ${suffix}` : raw;
  }
  return raw;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<LanguageCode>(() => (localStorage.getItem("sfs_language") as LanguageCode) || "en");
  useEffect(() => {
    localStorage.setItem("sfs_language", language);
    document.documentElement.lang = language;
  }, [language]);
  const value = useMemo<I18nContextValue>(() => ({ language, setLanguage, t: (text) => translate(text, language) }), [language]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return context;
}

export function T({ children }: { children: string | number }) {
  const { t } = useI18n();
  return <>{t(children)}</>;
}
