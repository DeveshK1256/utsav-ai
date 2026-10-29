import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const frontendDir = path.resolve(__dirname, '..');
const outDir = path.join(frontendDir, 'out');

function findHtmlFiles(dir) {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  for (const file of fs.readdirSync(dir)) {
    const full = path.join(dir, file);
    if (fs.statSync(full).isDirectory()) {
      results = results.concat(findHtmlFiles(full));
    } else if (file.endsWith('.html')) {
      results.push(full);
    }
  }
  return results;
}

const htmlFiles = findHtmlFiles(outDir);
console.log(`[post-build-csp] Scanning ${htmlFiles.length} HTML files in ${outDir}...`);

const hashes = new Set();
const scriptRegex = /<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/gi;

for (const f of htmlFiles) {
  const content = fs.readFileSync(f, 'utf8');
  let match;
  while ((match = scriptRegex.exec(content)) !== null) {
    const scriptBody = match[2];
    if (scriptBody && scriptBody.trim().length > 0) {
      const hash = crypto.createHash('sha256').update(scriptBody).digest('base64');
      hashes.add(`'sha256-${hash}'`);
    }
  }
}

const hashList = Array.from(hashes).sort();
console.log(`[post-build-csp] Extracted ${hashList.length} unique inline script sha256 hashes.`);

// Construct strict script-src with exact hashes and no unsafe-inline
const scriptSrc = ["'self'", ...hashList].join(' ');
const styleSrc = "'self' https://fonts.googleapis.com 'unsafe-inline'";
const imgSrc = "'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org";
const fontSrc = "'self' https://fonts.gstatic.com data:";
const connectSrc = "'self' https://utsav-ai-ycg2.onrender.com";

const cspValue = [
  "default-src 'self'",
  `script-src ${scriptSrc}`,
  `style-src ${styleSrc}`,
  `img-src ${imgSrc}`,
  `font-src ${fontSrc}`,
  `connect-src ${connectSrc}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'"
].join('; ');

const headersContent = `# Netlify Edge Security Headers (Static Export with Exact Inline Script Hashes)
/*
  Content-Security-Policy: ${cspValue};
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(self), camera=(), microphone=()
`;

// Write to frontend/out/_headers only (never touch tracked source files)
const outHeaders = path.join(outDir, '_headers');
if (fs.existsSync(outDir)) {
  fs.writeFileSync(outHeaders, headersContent, 'utf8');
  console.log(`[post-build-csp] Wrote CSP headers with ${hashList.length} hashes to ${outHeaders}`);
}
