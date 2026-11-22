// config/plugins/frontend-design/mcp-app/src/app.ts
import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
} from '@modelcontextprotocol/ext-apps';

interface Swatch {
  key: string;
  value: string;
}

interface ContrastEntry {
  label: string;
  fg: string;
  bg: string;
  ratio: number | null;
  wcagAA: boolean;
  wcagAAA: boolean;
}

interface ScaleEntry {
  key: string;
  raw: string;
  px: number | null;
  passed: boolean;
}

interface TokensPayload {
  mode: 'tokens';
  name: string;
  remBase: number;
  swatches: Swatch[];
  contrasts: ContrastEntry[];
  scale: ScaleEntry[];
  floorPassed: boolean;
}

interface SvgPayload {
  mode: 'svg';
  sourceLabel: string;
  svgContent: string;
  colorCount: number;
  colors: string[];
  fontChecks: Array<{ raw: string; px: number; passed: boolean }>;
  floorPassed: boolean;
  violationCount: number;
}

type RenderPayload = TokensPayload | SvgPayload;

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function renderTokens(data: TokensPayload): string {
  const statusBadge = data.floorPassed
    ? '<span class="badge pass">Typography Floor &ge; 12px: PASS</span>'
    : '<span class="badge fail">Typography Floor &ge; 12px: FAIL</span>';

  const swatchCards = data.swatches
    .map(
      (s) => `
      <div class="card">
        <div class="swatch" style="background:${escapeHtml(s.value)}"></div>
        <div><strong>${escapeHtml(s.key)}</strong></div>
        <div class="mono">${escapeHtml(s.value)}</div>
      </div>`,
    )
    .join('');

  const contrastRows = data.contrasts
    .map((c) => {
      const ratioText = c.ratio !== null ? `${c.ratio}:1` : 'N/A';
      const badgeClass = c.wcagAAA ? 'pass' : c.wcagAA ? 'warn' : 'fail';
      const level = c.wcagAAA ? 'AAA' : c.wcagAA ? 'AA' : 'FAIL';
      return `
      <div class="scale-row">
        <div><strong>${escapeHtml(c.label)}</strong> <span class="mono">(${escapeHtml(c.fg)} on ${escapeHtml(c.bg)})</span></div>
        <div><span class="badge ${badgeClass}">${ratioText} &middot; ${level}</span></div>
      </div>`;
    })
    .join('');

  const scaleRows = data.scale
    .map((s) => {
      const pxLabel = s.px !== null ? `${s.px}px` : 'unparsed';
      const badgeClass = s.passed ? 'pass' : 'fail';
      return `
      <div class="scale-row">
        <div>
          <strong>${escapeHtml(s.key)}</strong>
          <span class="mono">(${escapeHtml(s.raw)} &asymp; ${pxLabel})</span>
        </div>
        <span class="badge ${badgeClass}">${s.passed ? 'PASS' : '&lt; 12px VIOLATION'}</span>
      </div>`;
    })
    .join('');

  return `
    <div class="header">
      <div>
        <h1 class="title">Design Tokens: ${escapeHtml(data.name)}</h1>
        <div class="subtitle">remBase: ${data.remBase}px &middot; ${data.swatches.length} palette tokens</div>
      </div>
      ${statusBadge}
    </div>
    <h2 class="section-title">Palette Swatches</h2>
    <div class="grid">${swatchCards}</div>
    <h2 class="section-title">WCAG Contrast Audit</h2>
    ${contrastRows || '<div class="empty">No hex contrast pairs available</div>'}
    <h2 class="section-title">Typography Scale (&ge; 12px Floor)</h2>
    ${scaleRows}
  `;
}

function renderSvg(data: SvgPayload): string {
  const statusBadge = data.floorPassed
    ? '<span class="badge pass">SVG Gate: PASS</span>'
    : `<span class="badge fail">SVG Gate: ${data.violationCount} VIOLATION(S)</span>`;

  const checksHtml = data.fontChecks
    .map(
      (f) => `
      <div class="scale-row">
        <span class="mono">${escapeHtml(f.raw)} &rarr; ${f.px}px</span>
        <span class="badge ${f.passed ? 'pass' : 'fail'}">${f.passed ? 'PASS' : '&lt; 12px'}</span>
      </div>`,
    )
    .join('');

  return `
    <div class="header">
      <div>
        <h1 class="title">SVG Quality Gate</h1>
        <div class="subtitle">${escapeHtml(data.sourceLabel)} &middot; ${data.colorCount} hex colors</div>
      </div>
      ${statusBadge}
    </div>
    <div class="svg-stage">${data.svgContent}</div>
    <h2 class="section-title">Font-Size Checks (${data.fontChecks.length})</h2>
    ${checksHtml || '<div class="empty">No explicit font-size attributes found</div>'}
  `;
}

const root = document.getElementById('root')!;
const app = new App({ name: 'Frontend Design Studio', version: '1.0.0' }, {});

app.ontoolinput = () => {
  root.innerHTML = '<div class="empty">Running Frontend Design audit...</div>';
};

app.ontoolresult = (result) => {
  const data = result.structuredContent as RenderPayload | undefined;
  if (!data) {
    root.innerHTML = '<div class="empty">No structuredContent returned by tool.</div>';
    return;
  }
  root.innerHTML = data.mode === 'svg' ? renderSvg(data) : renderTokens(data);
};

app.onhostcontextchanged = (ctx) => {
  if (ctx.theme) applyDocumentTheme(ctx.theme);
  if (ctx.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
};

async function init(): Promise<void> {
  await app.connect();
  const ctx = app.getHostContext();
  if (ctx?.theme) applyDocumentTheme(ctx.theme);
  if (ctx?.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
}

void init();
