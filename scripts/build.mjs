// Builds dist/index.html from index.html.
//
// index.html is the source of truth and runs as-is in a browser (Tailwind Play CDN),
// which is handy for editing. This script produces the production file: it compiles
// only the Tailwind classes the page uses, inlines the CSS, and drops the CDN scripts.
//
//   npm run build                  -> dist/
//   SITE_URL=https://example.com npm run build   (absolute URL for the share image)

import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'dist');
const tmp = path.join(dist, '.tmp');
const srcPath = path.join(root, 'index.html');
const html = readFileSync(srcPath, 'utf8');

// 1. Pull the Tailwind config and the @apply component styles out of the source page.
const cdnBlock = /[ \t]*<script src="https:\/\/cdn\.tailwindcss\.com"><\/script>\s*<script>\s*tailwind\.config = (\{[\s\S]*?\n {4}\});\s*<\/script>\n?/;
const styleBlock = /<style type="text\/tailwindcss">([\s\S]*?)<\/style>/;
const cdnMatch = html.match(cdnBlock);
const styleMatch = html.match(styleBlock);
if (!cdnMatch || !styleMatch) throw new Error('Could not find the Tailwind CDN/config or <style type="text/tailwindcss"> block in index.html');

const config = new Function('return ' + cdnMatch[1])();

// 2. Compile with the Tailwind CLI (scans index.html for class names).
rmSync(dist, { recursive: true, force: true });
mkdirSync(tmp, { recursive: true });
const cfgFile = path.join(tmp, 'tailwind.config.cjs');
const inFile = path.join(tmp, 'in.css');
const outFile = path.join(tmp, 'out.css');
writeFileSync(cfgFile, 'module.exports = ' + JSON.stringify({ ...config, content: [srcPath] }) + ';');
writeFileSync(inFile, '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' + styleMatch[1]);
const bin = path.join(root, 'node_modules', '.bin', process.platform === 'win32' ? 'tailwindcss.cmd' : 'tailwindcss');
execFileSync(bin, ['-c', cfgFile, '-i', inFile, '-o', outFile, '--minify'], { stdio: 'inherit' });
const css = readFileSync(outFile, 'utf8');

// 3. Assemble the production page.
let out = html.replace(cdnBlock, '').replace(styleBlock, () => `<style>${css}</style>`);

const siteUrl = (process.env.SITE_URL || '').replace(/\/+$/, '');
if (siteUrl) {
  out = out.replace('content="og.png"', () => `content="${siteUrl}/og.png"`);
  out = out.replace('<meta property="og:type" content="website">', () => `<meta property="og:type" content="website">\n  <meta property="og:url" content="${siteUrl}/">`);
}
writeFileSync(path.join(dist, 'index.html'), out);
if (existsSync(path.join(root, 'og.png'))) copyFileSync(path.join(root, 'og.png'), path.join(dist, 'og.png'));
rmSync(tmp, { recursive: true, force: true });

// 4. Sanity checks so a broken build fails loudly (CI runs this on every PR).
if (out.includes('cdn.tailwindcss.com')) throw new Error('Build still references the Tailwind CDN');
if (out.includes('text/tailwindcss')) throw new Error('Build still contains an uncompiled Tailwind style block');
if (css.length < 10000) throw new Error('Compiled CSS looks too small (' + css.length + ' bytes)');
if (!/\.bg-navy-900\b/.test(css)) throw new Error('Compiled CSS is missing expected utilities');

const kb = (n) => (n / 1024).toFixed(1) + ' KB';
console.log(`Built dist/index.html (${kb(Buffer.byteLength(out))}, CSS ${kb(css.length)})`);
