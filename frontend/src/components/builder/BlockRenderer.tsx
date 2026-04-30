import { blockRegistry } from "./blockRegistry";
import type { PageBlock } from "./schema";

export function BlockRenderer({ block, locale }: { block: PageBlock; locale: string }) {
  const entry = blockRegistry[block.type] || blockRegistry.Text;
  const Renderer = entry.Renderer;
  return <Renderer block={block} locale={locale} />;
}
