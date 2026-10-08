#!/usr/bin/env node
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

const reportQuoteJSX = String.raw`function quote(s) { return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\r/g, '\\r').replace(/\n/g, '\\n').replace(/\t/g, '\\t') + '"'; }`;

const manifestPath = process.argv[2];
if (manifestPath === '--self-test') {
  const assert = require('assert');
  for (const value of ['文字图像_地点_衢山岛', '素材/白色海鸥.png', 'quote"\\line', 'emoji🐦']) {
    assert.strictEqual(JSON.parse(jsxString(value)), value);
  }
  const quote = require('vm').runInNewContext(reportQuoteJSX + '; quote');
  for (const value of ['衢山岛', 'quote"\\line', 'line\nnext\rtab\t']) {
    assert.strictEqual(JSON.parse(quote(value)), value);
  }
  console.log('ok');
  process.exit(0);
}
if (!manifestPath) throw new Error('usage: compose_psd.js /absolute/path/manifest.json');
const m = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const verifyOnly = process.argv.includes('--verify-only');
if (m.texts && m.texts.length) throw new Error('Type Layer is disabled; put all text images in layers');
if (!m.layers || !m.layers.length || !path.isAbsolute(m.output)) throw new Error('missing layers or absolute output path');
if (path.extname(m.output).toLowerCase() !== '.psd') throw new Error('output must be a PSD');
for (const value of [m.canvas.width, m.canvas.height, m.canvas.resolution]) {
  if (!Number.isFinite(value) || value <= 0) throw new Error('invalid canvas');
}
if (new Set(m.layers.map(layer => layer.name)).size !== m.layers.length) throw new Error('duplicate layer names');
for (const layer of m.layers) {
  if (!path.isAbsolute(layer.path) || !fs.existsSync(layer.path)) throw new Error('missing layer image');
  if (!layer.name || /[\u0000-\u001f\ufffd□]/.test(layer.name)) throw new Error('invalid layer name');
  if (layer.name.startsWith('文字图像_') && (!layer.semantic_text || layer.editable !== false)) throw new Error('text image layer requires semantic_text and editable:false');
  if (![layer.x, layer.y, layer.width, layer.height].every(Number.isFinite) || layer.width <= 0 || layer.height <= 0 || layer.x < 0 || layer.y < 0 || layer.x + layer.width > m.canvas.width || layer.y + layer.height > m.canvas.height) throw new Error('invalid layer placement');
}
const logos = m.layers.filter(layer => layer.role === 'brand_logo');
if (!logos.length) throw new Error('每份成品必须有独立主题 Logo 层：role=brand_logo');
if (logos.some(layer => !layer.name.startsWith('品牌Logo_') || layer.visible === false || Number(layer.opacity ?? 100) <= 0)) {
  throw new Error('Logo 图层必须以 品牌Logo_ 命名且可见');
}
if (m.layers.slice(m.layers.indexOf(logos[0])).some(layer => layer.role !== 'brand_logo')) {
  throw new Error('Logo 必须置于其他图层上方，请重新执行准备脚本');
}
if (!verifyOnly && fs.existsSync(m.output)) throw new Error('output exists; refuse overwrite, use --verify-only to inspect');
if (verifyOnly && !fs.existsSync(m.output)) throw new Error('PSD does not exist for verification');

function jsxString(value) {
  return '"' + [...String(value)].map(ch => {
    const code = ch.codePointAt(0);
    if (code > 127) {
      if (code <= 0xffff) return '\\u' + code.toString(16).padStart(4, '0');
      const n = code - 0x10000;
      return '\\u' + (0xd800 + (n >> 10)).toString(16) +
        '\\u' + (0xdc00 + (n & 1023)).toString(16);
    }
    return ch === '\\' ? '\\\\' : ch === '"' ? '\\"' : ch === '\n' ? '\\r' : ch;
  }).join('') + '"';
}

const outDir = path.dirname(m.output);
fs.mkdirSync(outDir, {recursive: true});
const verification = path.join(path.dirname(path.resolve(manifestPath)), 'verification');
fs.mkdirSync(verification, {recursive: true});
const previewPath = path.join(verification, 'photoshop-preview.png');
const foregroundPath = path.join(verification, 'photoshop-foreground.png');
const reportPath = path.join(verification, 'photoshop-check.json');

const jsx = [];
jsx.push('var previousDialogs = app.displayDialogs; app.displayDialogs = DialogModes.NO; try {');
jsx.push(`var output = new File(${jsxString(m.output)});`);
if (!verifyOnly) {
  jsx.push(`var doc = app.documents.add(${m.canvas.width}, ${m.canvas.height}, ${m.canvas.resolution}, ${jsxString('分层重建')}, NewDocumentMode.RGB, DocumentFill.TRANSPARENT);`);
  jsx.push('var initialEmptyLayer = doc.activeLayer;');
  for (const layer of m.layers) {
    jsx.push(`var src = app.open(new File(${jsxString(layer.path)}));`);
    jsx.push('try {');
    jsx.push(`if (src.width.as('px') != ${layer.width} || src.height.as('px') != ${layer.height}) src.resizeImage(UnitValue(${layer.width}, 'px'), UnitValue(${layer.height}, 'px'));`);
    jsx.push(`src.activeLayer.name = ${jsxString(layer.name)};`);
    jsx.push("var sourceLeft = src.activeLayer.bounds[0].as('px'); var sourceTop = src.activeLayer.bounds[1].as('px');");
    jsx.push('var placed = src.activeLayer.duplicate(doc, ElementPlacement.PLACEATBEGINNING); app.activeDocument = doc;');
    jsx.push(`placed.translate(UnitValue(${layer.x} + sourceLeft - placed.bounds[0].as('px'), 'px'), UnitValue(${layer.y} + sourceTop - placed.bounds[1].as('px'), 'px'));`);
    if (layer.role === 'brand_logo') jsx.push('placed.visible = true; placed.opacity = 100;');
    jsx.push('} finally { src.close(SaveOptions.DONOTSAVECHANGES); app.activeDocument = doc; }');
  }
  jsx.push('initialEmptyLayer.remove();');
  jsx.push("if (output.exists) throw new Error('output appeared during composition; refuse overwrite');");
  jsx.push('var saveOptions = new PhotoshopSaveOptions(); saveOptions.layers = true; saveOptions.embedColorProfile = true;');
  jsx.push('doc.saveAs(output, saveOptions, true, Extension.LOWERCASE); doc.close(SaveOptions.DONOTSAVECHANGES);');
}
jsx.push('var check = app.open(output); var textCount = 0;');
jsx.push('for (var i=0; i<check.artLayers.length; i++) if (check.artLayers[i].kind == LayerKind.TEXT) textCount++;');
jsx.push(`if (check.width.as('px') != ${m.canvas.width} || check.height.as('px') != ${m.canvas.height}) throw new Error('canvas mismatch');`);
jsx.push("if (textCount != 0) throw new Error('unexpected Type Layer');");
jsx.push(`if (check.resolution != ${m.canvas.resolution} || check.artLayers.length != ${m.layers.length}) throw new Error('resolution or layer count mismatch');`);
jsx.push(`var expectedNames = [${m.layers.slice().reverse().map(layer => jsxString(layer.name)).join(',')}];`);
jsx.push("for (var i=0; i<expectedNames.length; i++) if (check.artLayers[i].name != expectedNames[i]) throw new Error('layer name/order mismatch');");
jsx.push('var actualLogoCount = 0;');
for (const layer of logos) {
  jsx.push(`var logo = check.artLayers.getByName(${jsxString(layer.name)}); if (!logo.visible || logo.opacity != 100) throw new Error('Logo is hidden or faded'); actualLogoCount++;`);
}
jsx.push(`check.saveAs(new File(${jsxString(previewPath)}), new PNGSaveOptions(), true, Extension.LOWERCASE);`);
const backgroundIndices = m.layers.slice().reverse().flatMap((layer, i) => layer.transparent === false || layer.name.startsWith('背景') ? [i] : []);
jsx.push(`var backgroundIndices = ${JSON.stringify(backgroundIndices)}, previousVisibility = [];`);
jsx.push('for (var i=0; i<backgroundIndices.length; i++) { var layer = check.artLayers[backgroundIndices[i]]; previousVisibility.push(layer.visible); layer.visible = false; }');
jsx.push(`try { check.saveAs(new File(${jsxString(foregroundPath)}), new PNGSaveOptions(), true, Extension.LOWERCASE); } finally { for (var i=0; i<backgroundIndices.length; i++) check.artLayers[backgroundIndices[i]].visible = previousVisibility[i]; }`);
jsx.push(reportQuoteJSX);
jsx.push('var names = []; for (var i=0; i<check.artLayers.length; i++) names.push(quote(check.artLayers[i].name));');
jsx.push(`var report = '{"width":'+check.width.as('px')+',"height":'+check.height.as('px')+',"resolution":'+check.resolution+',"layers":'+check.artLayers.length+',"textLayers":'+textCount+',"logoLayers":'+actualLogoCount+',"logosVisible":true,"names":['+names.join(',')+']}';`);
jsx.push(`var reportFile = new File(${jsxString(reportPath)}); reportFile.encoding = 'UTF8'; reportFile.open('w'); reportFile.write(report); reportFile.close();`);
jsx.push('} finally { app.displayDialogs = previousDialogs; }');

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'psd-bridge-'));
const jsxPath = path.join(work, 'compose.jsx');
fs.writeFileSync(jsxPath, jsx.join('\n'), 'utf8');
const appleScript = `set jsxFile to POSIX file "${jsxPath}"
tell application ${JSON.stringify(m.photoshop_app || 'Adobe Photoshop 2026')}
  do javascript (read jsxFile as text)
end tell`;

try {
  cp.execFileSync('osascript', ['-e', appleScript], {stdio: 'inherit'});
  if (!fs.existsSync(m.output)) throw new Error('Photoshop did not create the PSD');
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8').replace(/^\uFEFF/, ''));
  Object.assign(report, {output: m.output, preview: previewPath, foreground: foregroundPath});
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify(report));
} finally {
  fs.rmSync(work, {recursive: true, force: true});
}
