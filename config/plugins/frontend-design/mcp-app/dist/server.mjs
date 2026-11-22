// src/server.ts
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { RESOURCE_MIME_TYPE } from "@modelcontextprotocol/ext-apps/server";
import { z } from "zod/v4";
var __dirname = dirname(fileURLToPath(import.meta.url));
var PLUGIN_ROOT = resolve(__dirname, "..", "..");
var APP_HTML_PATH = process.env.FRONTEND_DESIGN_APP_HTML || resolve(__dirname, "app.html");
var APP_URI = "ui://frontend-design/preview.html";
var PRESET_NAMES = [
  "academic-paper",
  "editorial-minimal",
  "presentation-deck",
  "saas-enterprise"
];
function parseHexToRgb(color) {
  const m = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!m) return null;
  let hex = m[1];
  if (hex.length === 3) {
    hex = hex.split("").map((c) => c + c).join("");
  }
  const n = parseInt(hex, 16);
  return [n >> 16 & 255, n >> 8 & 255, n & 255];
}
function relativeLuminance([r, g, b]) {
  const toLinear = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}
function contrastRatio(fg, bg) {
  const fgRgb = parseHexToRgb(fg);
  const bgRgb = parseHexToRgb(bg);
  if (!fgRgb || !bgRgb) return null;
  const l1 = relativeLuminance(fgRgb);
  const l2 = relativeLuminance(bgRgb);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2));
}
function parseCssPx(raw, remBase = 16) {
  const val = raw.trim().toLowerCase();
  const pxMatch = val.match(/^([\d.]+)\s*px$/);
  if (pxMatch) return parseFloat(pxMatch[1]);
  const remMatch = val.match(/^([\d.]+)\s*rem$/);
  if (remMatch) return parseFloat(remMatch[1]) * remBase;
  return null;
}
function loadTokens(tokensJson, preset) {
  if (tokensJson) {
    return JSON.parse(tokensJson);
  }
  if (preset && PRESET_NAMES.includes(preset)) {
    const p = resolve(PLUGIN_ROOT, "skills", "web-theme-curator", "presets", `${preset}.json`);
    return JSON.parse(readFileSync(p, "utf-8"));
  }
  const defaultPath = resolve(
    PLUGIN_ROOT,
    "skills",
    "web-theme-curator",
    "templates",
    "design-tokens.json"
  );
  return JSON.parse(readFileSync(defaultPath, "utf-8"));
}
function auditTokens(tokens) {
  const name = typeof tokens.name === "string" ? tokens.name : "custom-tokens";
  const remBase = typeof tokens.remBase === "number" ? tokens.remBase : 16;
  const palette = tokens.palette ?? {};
  const typography = tokens.typography ?? {};
  const scaleObj = typography.scale ?? {};
  const swatches = [];
  for (const [k, v] of Object.entries(palette)) {
    if (typeof v === "string") {
      swatches.push({ key: k, value: v });
    } else if (v && typeof v === "object" && !Array.isArray(v)) {
      for (const [subK, subV] of Object.entries(v)) {
        if (typeof subV === "string") {
          swatches.push({ key: `${k}.${subK}`, value: subV });
        }
      }
    }
  }
  const bgBase = typeof palette.bgBase === "string" ? palette.bgBase : "#0a1526";
  const textMain = typeof palette.textMain === "string" ? palette.textMain : "";
  const textSecondary = typeof palette.textSecondary === "string" ? palette.textSecondary : "";
  const primary = typeof palette.primary === "string" ? palette.primary : "";
  const contrasts = [];
  for (const [label, fg] of [
    ["textMain / bgBase", textMain],
    ["textSecondary / bgBase", textSecondary],
    ["primary / bgBase", primary]
  ]) {
    if (!fg) continue;
    const ratio = contrastRatio(fg, bgBase);
    contrasts.push({
      label,
      fg,
      bg: bgBase,
      ratio,
      wcagAA: ratio !== null ? ratio >= 4.5 : false,
      wcagAAA: ratio !== null ? ratio >= 7 : false
    });
  }
  const scale = Object.entries(scaleObj).map(([key, rawVal]) => {
    const raw = String(rawVal);
    const px = parseCssPx(raw, remBase);
    return {
      key,
      raw,
      px,
      passed: px !== null ? px >= 12 : true
    };
  });
  const floorViolations = scale.filter((s) => !s.passed);
  return {
    mode: "tokens",
    name,
    remBase,
    swatches,
    contrasts,
    scale,
    floorPassed: floorViolations.length === 0,
    floorViolations
  };
}
function auditSvg(svgContent, sourceLabel) {
  const fontMatches = [...svgContent.matchAll(/font-size\s*[:=]\s*['"]?\s*([\d.]+)\s*(px|pt|rem|em)?/gi)];
  const findings = fontMatches.map((m) => {
    const num = parseFloat(m[1]);
    const unit = (m[2] || "px").toLowerCase();
    const px = unit === "pt" ? num * (96 / 72) : unit === "rem" || unit === "em" ? num * 16 : num;
    return {
      raw: m[0],
      px: Number(px.toFixed(1)),
      passed: px >= 12
    };
  });
  const hexColors = new Set(
    (svgContent.match(/#[0-9a-fA-F]{3,6}\b/g) || []).map((c) => c.toLowerCase())
  );
  const violations = findings.filter((f) => !f.passed);
  return {
    mode: "svg",
    sourceLabel,
    svgContent,
    colorCount: hexColors.size,
    colors: [...hexColors],
    fontChecks: findings,
    floorPassed: violations.length === 0,
    violationCount: violations.length
  };
}
var server = new McpServer({
  name: "frontend-design-ui",
  version: "1.0.0"
});
server.registerResource(
  "frontend-design-preview",
  APP_URI,
  {
    description: "Interactive Design Tokens, Contrast & SVG Typography Quality Gate UI",
    mimeType: RESOURCE_MIME_TYPE,
    _meta: {
      ui: {
        prefersBorder: false
      }
    }
  },
  async () => {
    const html = readFileSync(APP_HTML_PATH, "utf-8");
    return {
      contents: [
        {
          uri: APP_URI,
          mimeType: RESOURCE_MIME_TYPE,
          text: html
        }
      ]
    };
  }
);
server.registerTool(
  "preview_design_tokens",
  {
    title: "Design Tokens & Gate",
    description: "Preview design tokens palette, WCAG contrast ratios, and verify >= 12px typography floor in an interactive UI.",
    inputSchema: {
      tokensJson: z.string().optional().describe("Optional raw design-tokens.json content"),
      preset: z.enum(PRESET_NAMES).optional().describe("Optional built-in preset name when tokensJson is omitted")
    },
    _meta: {
      ui: {
        resourceUri: APP_URI
      },
      "com.google.antigravity/ui": {
        entrypoints: [
          { type: "aux_pane", title: "Design Tokens & Gate" },
          { type: "global", title: "Design Tokens & Gate" }
        ]
      }
    }
  },
  async ({ tokensJson, preset }) => {
    const tokens = loadTokens(tokensJson, preset);
    const audit = auditTokens(tokens);
    const summary = `Design Tokens "${audit.name}": ${audit.swatches.length} swatches, typography floor (>=12px) ${audit.floorPassed ? "PASSED" : "FAILED"}.`;
    return {
      content: [{ type: "text", text: summary }],
      structuredContent: audit
    };
  }
);
server.registerTool(
  "inspect_svg_gate",
  {
    title: "Inspect SVG Quality Gate",
    description: "Render an SVG preview and audit all font-size declarations against the >= 12px readability floor.",
    inputSchema: {
      svgContent: z.string().optional().describe("Optional raw SVG XML string"),
      filePath: z.string().optional().describe("Optional path to an SVG file")
    },
    _meta: {
      ui: {
        resourceUri: APP_URI
      }
    }
  },
  async ({ svgContent, filePath }) => {
    let resolvedSvg = svgContent;
    let label = "inline-svg";
    if (!resolvedSvg && filePath) {
      resolvedSvg = readFileSync(filePath, "utf-8");
      label = filePath;
    }
    if (!resolvedSvg) {
      const defaultSvg = resolve(PLUGIN_ROOT, "skills", "svg-skill-curator", "templates", "arch-card.svg");
      resolvedSvg = readFileSync(defaultSvg, "utf-8");
      label = "templates/arch-card.svg";
    }
    const audit = auditSvg(resolvedSvg, label);
    const summary = `SVG Gate (${audit.sourceLabel}): ${audit.colorCount} colors, ${audit.fontChecks.length} font checks, floor ${audit.floorPassed ? "PASSED" : `FAILED (${audit.violationCount} violations)`}.`;
    return {
      content: [{ type: "text", text: summary }],
      structuredContent: audit
    };
  }
);
var transport = new StdioServerTransport();
await server.connect(transport);
