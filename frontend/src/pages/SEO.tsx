import { FileSearch, Globe, SearchCode } from "lucide-react";
import { useEffect, useState } from "react";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { languageCompletion, sites } from "../data/mockData";
import { useI18n } from "../i18n";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";

type Props = { siteId: string; onToast: (message: string) => void };

export function SEO({ siteId, onToast }: Props) {
  const { t } = useI18n();
  const [refreshKey, setRefreshKey] = useState(0);
  const seo = useApiData(() => api.siteSeo(siteId), { sitemap: [], hreflang: [] }, [siteId, refreshKey]);
  const [language, setLanguage] = useState("en");
  const [title, setTitle] = useState("Best Online Shop");
  const [description, setDescription] = useState("Buy quality products online with multilingual checkout.");
  const [slug, setSlug] = useState("/");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    const row = seo.data.sitemap?.find((item: any) => item.language_code === language);
    if (row) {
      setTitle(row.title || title);
      setDescription(row.description || description);
      setSlug(row.slug || slug);
    }
  }, [seo.data, language]);
  const saveSeo = async () => {
    setBusy("save");
    try {
      await api.createSeo(siteId, { request_id: `web_seo_${Date.now()}`, language_code: language, title, description, slug });
      await api.generateSitemap(siteId, { request_id: `web_sitemap_${Date.now()}` });
      setRefreshKey((value) => value + 1);
      onToast("SEO_UPDATED");
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="space-y-5">
      <div>
        <p className="page-kicker">{t("Search Graph")}</p>
        <h1 className="page-title">{t("SEO")}</h1>
      </div>
      <div className="grid gap-4 xl:grid-cols-[.9fr_1.1fr]">
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("SEO Editor")}</h2>
          <div className="mt-4 space-y-4">
            <label><span className="form-label">{t("Site")}</span><select className="form-select w-full" value={siteId} disabled>{sites.slice(0, 6).map((site) => <option key={site.site_id} value={site.site_id}>{site.alias}</option>)}<option value={siteId}>{siteId}</option></select></label>
            <label><span className="form-label">{t("Language")}</span><select className="form-select w-full" value={language} onChange={(event) => setLanguage(event.target.value)}>{languageCompletion.map((lang) => <option key={lang.code}>{lang.code}</option>)}</select></label>
            <label><span className="form-label">{t("SEO title")}</span><input className="form-input" data-testid="seo-title-input" value={title} onChange={(event) => setTitle(event.target.value)} /></label>
            <label><span className="form-label">{t("SEO description")}</span><textarea className="form-input min-h-24" data-testid="seo-description-input" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
            <label><span className="form-label">{t("Slug")}</span><input className="form-input" data-testid="seo-slug-input" value={slug} onChange={(event) => setSlug(event.target.value)} /></label>
            <NeonButton data-testid="seo-save-button" onClick={saveSeo} disabled={busy === "save"}><SearchCode size={15} />{busy === "save" ? t("common.loading") : t("Validate SEO")}</NeonButton>
          </div>
        </GlassCard>
        <GlassCard className="p-4">
          <h2 className="font-bold text-textMain">{t("Generated Assets")}</h2>
          <div className="mt-4 grid gap-3">
            {[
              ["hreflang", seo.data.hreflang?.map((item: any) => `${item.language_code}:${item.slug}`).join(", ") || "en:/"],
              ["sitemap.xml", `${seo.data.sitemap?.length || 0} URLs queued`],
              ["robots.txt", "Allow production index"],
              ["canonical", "Domain-normalized"],
              ["Open Graph", "Localized preview cards"]
            ].map(([title, desc]) => (
              <div key={title} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center gap-3"><Globe className="text-neon" /><div><p className="font-bold text-textMain">{t(title)}</p><p className="text-sm text-textWeak">{t(desc)}</p></div></div>
                <FileSearch className="text-plasma" />
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
