import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../src", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const allowed = new Set(["LoginPortalAnimation.tsx"]);
const issues = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const stat = statSync(path);
    if (stat.isDirectory()) walk(path);
    if (!stat.isFile() || !path.endsWith(".tsx") || allowed.has(name)) continue;
    const lines = readFileSync(path, "utf8").split(/\r?\n/);
    lines.forEach((line, index) => {
      const stripped = line.trim();
      if (!stripped.includes("<") || stripped.includes("=>")) return;
      const rawText = />\s*[A-Za-z\u4e00-\u9fa5][^<{}`]{2,}\s*</.test(stripped);
      const placeholder = /placeholder="[^"]*[A-Za-z\u4e00-\u9fa5][^"]*"/.test(stripped);
      if ((rawText || placeholder) && !stripped.includes("t(") && !stripped.includes("text(")) {
        issues.push({ file: path, line: index + 1, text: stripped.slice(0, 180) });
      }
    });
  }
}

walk(root);
if (issues.length) {
  console.error(JSON.stringify({ status: "FAIL", count: issues.length, samples: issues.slice(0, 50) }, null, 2));
  process.exit(1);
}
console.log(JSON.stringify({ status: "PASS", count: 0 }));
