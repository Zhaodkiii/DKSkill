#!/usr/bin/env node
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

const manifestPath = process.argv[2];
if (!manifestPath) throw new Error('usage: compose_psd.js /absolute/path/manifest.json');
const m = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
if (m.texts && m.texts.length) throw new Error('Type Layer is disabled; put all text images in layers');
if (fs.existsSync(m.output) && !m.overwrite) throw new Error(`output already exists; use a new versioned path or set overwrite=true: ${m.output}`);

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

fs.mkdirSync(path.dirname(m.output), {recursive: true});
const jsx = [];
jsx.push('app.displayDialogs = DialogModes.NO;');
jsx.push(`var doc = app.documents.add(${m.canvas.width}, ${m.canvas.height}, ${m.canvas.resolution}, "PSD Rebuild", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);`);
jsx.push('var placeholder = doc.activeLayer;');

for (let i = 0; i < m.layers.length; i++) {
  const layer = m.layers[i];
  jsx.push(`var src${i} = app.open(new File(${jsxString(layer.path)}));`);
  jsx.push(`src${i}.activeLayer.duplicate(doc, ElementPlacement.PLACEATBEGINNING);`);
  jsx.push(`src${i}.close(SaveOptions.DONOTSAVECHANGES); app.activeDocument = doc;`);
  jsx.push(`var placed${i} = doc.activeLayer; placed${i}.name = ${jsxString(layer.name)};`);
  jsx.push(`var b${i} = placed${i}.bounds; placed${i}.translate(${layer.x} - b${i}[0].as('px'), ${layer.y} - b${i}[1].as('px'));`);
}
jsx.push('placeholder.remove();');

jsx.push(`var output = new File(${jsxString(m.output)});`);
jsx.push('var saveOptions = new PhotoshopSaveOptions(); saveOptions.layers = true; saveOptions.embedColorProfile = true;');
jsx.push('doc.saveAs(output, saveOptions, true, Extension.LOWERCASE); doc.close(SaveOptions.DONOTSAVECHANGES);');
jsx.push('var check = app.open(output); var textCount = 0;');
jsx.push('for (var i = 0; i < check.artLayers.length; i++) if (check.artLayers[i].kind == LayerKind.TEXT) textCount++;');
jsx.push(`if (check.width.as('px') != ${m.canvas.width} || check.height.as('px') != ${m.canvas.height}) throw new Error('canvas mismatch');`);
jsx.push(`if (check.layers.length != ${m.layers.length}) throw new Error('layer count mismatch: ' + check.layers.length + '/${m.layers.length}');`);
jsx.push("if (textCount != 0) throw new Error('unexpected Type Layer');");
for (let i = 0; i < m.layers.length; i++) {
  jsx.push(`var found${i} = 0; for (var j = 0; j < check.layers.length; j++) if (check.layers[j].name == ${jsxString(m.layers[i].name)}) found${i}++;`);
  jsx.push(`if (found${i} != 1) throw new Error('missing or duplicate layer: ' + ${jsxString(m.layers[i].name)});`);
}
if (m.preview) {
  jsx.push(`var preview = new File(${jsxString(m.preview)}); var png = new PNGSaveOptions(); check.saveAs(preview, png, true, Extension.LOWERCASE);`);
}
jsx.push('check.close(SaveOptions.DONOTSAVECHANGES);');

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'psd-bridge-'));
const jsxPath = path.join(work, 'compose.jsx');
fs.writeFileSync(jsxPath, jsx.join('\n'), 'utf8');
const appleScript = `set jsxFile to POSIX file "${jsxPath}" as alias\nset jsxCode to read jsxFile\ntell application "${m.photoshop_app || 'Adobe Photoshop 2026'}" to do javascript jsxCode`;

try {
  cp.execFileSync('osascript', ['-e', appleScript], {stdio: 'inherit'});
  if (!fs.existsSync(m.output)) throw new Error('Photoshop did not create the PSD');
  console.log(JSON.stringify({output: m.output, width: m.canvas.width, height: m.canvas.height, layers: m.layers.length, textLayers: 0}));
} finally {
  fs.rmSync(work, {recursive: true, force: true});
}
