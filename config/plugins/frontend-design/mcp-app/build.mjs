// config/plugins/frontend-design/mcp-app/build.mjs
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import esbuild from 'esbuild';

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = resolve(__dirname, 'dist');
mkdirSync(distDir, { recursive: true });

// 1. Bundle client app into self-contained single-file HTML (CSP compliant)
const appBundle = await esbuild.build({
  entryPoints: [resolve(__dirname, 'src', 'app.ts')],
  bundle: true,
  format: 'iife',
  platform: 'browser',
  target: ['es2022'],
  minify: true,
  write: false,
});

const jsCode = appBundle.outputFiles[0].text;
const templateHtml = readFileSync(resolve(__dirname, 'src', 'index.html'), 'utf-8');
const finalHtml = templateHtml.replace('<!-- APP_BUNDLE -->', () => `<script>${jsCode}</script>`);
writeFileSync(resolve(distDir, 'app.html'), finalHtml, 'utf-8');

// 2. Bundle MCP stdio server (externalizing node_modules for clean ESM resolution)
await esbuild.build({
  entryPoints: [resolve(__dirname, 'src', 'server.ts')],
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: ['node20'],
  packages: 'external',
  outfile: resolve(distDir, 'server.mjs'),
});

console.log('[build] Built dist/app.html and dist/server.mjs');
