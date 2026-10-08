const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/xhs_extract.js`, 'utf8');
const img = (url, excluded = false) => ({
  src: url, currentSrc: url, naturalWidth: 1080, naturalHeight: 1440,
  getAttribute: () => null, closest: () => excluded ? {} : null,
});
const root = {
  innerText: '1/2\n测试笔记',
  querySelector: () => ({textContent: '测试笔记'}),
  querySelectorAll: () => [
    img('https://sns-webpic-qc.xhscdn.com/photo-last', true),
    img('https://sns-webpic-qc.xhscdn.com/photo-first'),
    img('http://sns-webpic-qc.xhscdn.com/photo-first'),
    img('https://sns-webpic-qc.xhscdn.com/new-signature/photo-first!different-size'),
    img('https://sns-webpic-qc.xhscdn.com/photo-last'),
    img('https://sns-avatar-qc.xhscdn.com/avatar/test'),
  ],
};
const run = pathname => vm.runInNewContext(source, {
  URL, location: {pathname, href: `https://www.xiaohongshu.com${pathname}?xsec_token=test`},
  document: {querySelector: () => root},
});
for (const path of ['/explore/abc123', '/discovery/item/abc123']) {
  const result = run(path);
  assert.equal(result.noteId, 'abc123');
  assert.equal(result.images.length, 2);
  assert.equal(result.pageImageCount, 2);
  assert.ok(result.images[0].url.endsWith('/photo-first'));
  assert.ok(result.images[1].url.endsWith('/photo-last'));
  assert.ok(result.url.includes('xsec_token=test'));
}
assert.throws(() => run('/search_result_ai'), /单篇/);
console.log('extract self-test passed');
