import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Edit3, FilePlus2, Languages, SearchCode, UploadCloud } from "lucide-react";
import { useState } from "react";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n";

type Props = {
  siteId: string;
  onToast: (message: string) => void;
};

export function CMS({ siteId, onToast }: Props) {
  const { t } = useI18n();
  const [tab, setTab] = useState<"articles" | "products">("articles");
  const [refresh, setRefresh] = useState(0);
  const articles = useApiData(() => api.articles(siteId), { items: [] }, [siteId, refresh]);
  const products = useApiData(() => api.products(siteId), { items: [] }, [siteId, refresh]);
  const [articleTitle, setArticleTitle] = useState("V2 Article");
  const [articleSlug, setArticleSlug] = useState("v2-article");
  const [articleLanguage, setArticleLanguage] = useState("en");
  const [articleSeoTitle, setArticleSeoTitle] = useState("V2 Article SEO");
  const [articleSeoDescription, setArticleSeoDescription] = useState("Article created from the real CMS button.");
  const [productName, setProductName] = useState("V2 Product");
  const [productPrice, setProductPrice] = useState("19.99");
  const [productDescription, setProductDescription] = useState("Created by CMS UI");
  const [productImage, setProductImage] = useState("https://example.com/product.jpg");
  const [productPayment, setProductPayment] = useState("https://pay.example.com/product");
  const [productLanguage, setProductLanguage] = useState("en");
  const [productSeoTitle, setProductSeoTitle] = useState("V2 Product SEO");
  const [productSeoDescription, setProductSeoDescription] = useState("Product created from CMS UI.");
  const [busy, setBusy] = useState("");
  const editor = useEditor({ extensions: [StarterKit], content: `<p>${t("Article created from the real CMS button.")}</p>` });

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    try {
      const result = await fn();
      onToast(`${label} OK`);
      setRefresh((value) => value + 1);
      return result;
    } catch (error) {
      onToast(errorText(error));
      return null;
    } finally {
      setBusy("");
    }
  };

  const createArticle = () => run("ARTICLE_CREATE", () => api.createArticle(siteId, { request_id: `web_article_${Date.now()}`, title: articleTitle, slug: articleSlug, language_code: articleLanguage, content: editor?.getHTML() || "", seo_title: articleSeoTitle, seo_description: articleSeoDescription }));
  const createProduct = async () => run("PRODUCT_CREATE", async () => {
    const created = await api.createProduct(siteId, { request_id: `web_product_${Date.now()}`, name: productName, price: Number(productPrice), description: productDescription, images: [productImage], language_code: productLanguage, seo_title: productSeoTitle, seo_description: productSeoDescription });
    if (productPayment && created?.product?.product_id) {
      const payment = await api.createPayment(siteId, { request_id: `web_payment_${Date.now()}`, provider: "manual", payment_url: productPayment, linked_product_id: created.product.product_id });
      if (payment?.payment?.payment_id) {
        await api.bindPayment(created.product.product_id, { request_id: `web_payment_bind_${Date.now()}`, payment_id: payment.payment.payment_id });
      }
    }
    return created;
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="page-kicker">{t("Content Command")}</p>
          <h1 className="page-title">{t("CMS")}</h1>
        </div>
        <div className="flex rounded-xl border border-white/10 bg-white/5 p-1">
          <button className={`tab-btn ${tab === "articles" ? "tab-active" : ""}`} onClick={() => setTab("articles")}>{t("Articles")}</button>
          <button className={`tab-btn ${tab === "products" ? "tab-active" : ""}`} onClick={() => setTab("products")}>{t("Products")}</button>
        </div>
      </div>

      {tab === "articles" ? (
        <GlassCard className="p-4">
          <div className="mb-4 grid gap-3 lg:grid-cols-3">
            <input className="form-input" data-testid="article-title" value={articleTitle} onChange={(event) => setArticleTitle(event.target.value)} placeholder={t("Title")} />
            <input className="form-input" data-testid="article-slug" value={articleSlug} onChange={(event) => setArticleSlug(event.target.value)} placeholder={t("Slug")} />
            <select className="form-select" value={articleLanguage} onChange={(event) => setArticleLanguage(event.target.value)} aria-label={t("Language")}><option>en</option><option>zh-CN</option><option>es</option></select>
            <input className="form-input" value={articleSeoTitle} onChange={(event) => setArticleSeoTitle(event.target.value)} placeholder={t("SEO title")} />
            <input className="form-input" value={articleSeoDescription} onChange={(event) => setArticleSeoDescription(event.target.value)} placeholder={t("SEO description")} />
            <NeonButton onClick={createArticle} disabled={busy === "ARTICLE_CREATE"} data-testid="new-article-button"><FilePlus2 size={16} />{t("New Article")}</NeonButton>
            <div className="lg:col-span-3 rounded-2xl border border-white/10 bg-black/20 p-3 text-textMain" data-testid="article-content">
              <EditorContent editor={editor} />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="cyber-table">
              <thead><tr><th>article_id</th><th>{t("Status")}</th><th>SEO</th><th>{t("Actions")}</th></tr></thead>
              <tbody>
                {articles.data.items.map((article: any) => (
                  <tr key={article.article_id}>
                    <td className="font-mono text-neon">{article.article_id}</td>
                    <td><StatusBadge status={article.status} /></td>
                    <td><SearchCode size={14} /></td>
                    <td><div className="flex gap-2"><NeonButton tone="ghost" onClick={() => onToast(`${t("Edit")} ${article.article_id}`)}><Edit3 size={14} />{t("Edit")}</NeonButton><NeonButton tone="purple" onClick={() => onToast(`I18N ${article.article_id}`)}><Languages size={14} />I18n</NeonButton><NeonButton tone="success" data-testid={`publish-article-${article.article_id}`} onClick={() => run("ARTICLE_PUBLISH", () => api.publishArticle(article.article_id, { request_id: `web_article_pub_${Date.now()}` }))}>{t("Publish")}</NeonButton></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      ) : (
        <GlassCard className="p-4">
          <div className="mb-4 grid gap-3 lg:grid-cols-3">
            <input className="form-input" data-testid="product-name" value={productName} onChange={(event) => setProductName(event.target.value)} placeholder={t("Name")} />
            <input className="form-input" data-testid="product-price" value={productPrice} onChange={(event) => setProductPrice(event.target.value)} placeholder={t("Price")} />
            <select className="form-select" value={productLanguage} onChange={(event) => setProductLanguage(event.target.value)} aria-label={t("Language")}><option>en</option><option>zh-CN</option><option>es</option></select>
            <input className="form-input" value={productDescription} onChange={(event) => setProductDescription(event.target.value)} placeholder={t("Description")} />
            <input className="form-input" value={productImage} onChange={(event) => setProductImage(event.target.value)} placeholder={t("Image URL")} />
            <input className="form-input" value={productPayment} onChange={(event) => setProductPayment(event.target.value)} placeholder={t("Payment link")} />
            <input className="form-input" value={productSeoTitle} onChange={(event) => setProductSeoTitle(event.target.value)} placeholder={t("SEO title")} />
            <input className="form-input" value={productSeoDescription} onChange={(event) => setProductSeoDescription(event.target.value)} placeholder={t("SEO description")} />
            <NeonButton onClick={createProduct} disabled={busy === "PRODUCT_CREATE"} data-testid="new-product-button"><UploadCloud size={16} />{t("New Product")}</NeonButton>
          </div>
          <div className="overflow-x-auto">
            <table className="cyber-table">
              <thead><tr><th>product_id</th><th>{t("Price")}</th><th>{t("Status")}</th><th>{t("Payment")}</th><th>{t("Actions")}</th></tr></thead>
              <tbody>
                {products.data.items.map((product: any) => (
                  <tr key={product.product_id}>
                    <td className="font-mono text-neon">{product.product_id}</td>
                    <td>${Number(product.price).toFixed(2)}</td>
                    <td><StatusBadge status={product.status} /></td>
                    <td>{product.payment_id || "-"}</td>
                    <td><div className="flex gap-2"><NeonButton tone="ghost" onClick={() => onToast(`${t("Edit")} ${product.product_id}`)}>{t("Edit")}</NeonButton><NeonButton tone="success" data-testid={`publish-product-${product.product_id}`} onClick={() => run("PRODUCT_PUBLISH", () => api.publishProduct(product.product_id, { request_id: `web_product_pub_${Date.now()}` }))}>{t("Publish")}</NeonButton></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
