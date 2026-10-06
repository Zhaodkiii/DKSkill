/*
 * 在已打开的小红书图文笔记详情页中执行本文件。
 * 返回可直接保存为 JSON 的笔记正文、作者、详情页 URL 和正文原图候选链接。
 */
(() => {
  const root = document.querySelector('.note-container');
  if (!root) throw new Error('未找到 .note-container：请先打开图文笔记详情页并等待加载完成');

  const text = (selectors) => {
    for (const selector of selectors) {
      const value = root.querySelector(selector)?.textContent?.trim();
      if (value) return value;
    }
    return '';
  };

  const candidates = (img) => {
    const values = [
      img.currentSrc,
      img.src,
      img.getAttribute('data-src'),
      img.getAttribute('data-original'),
      ...(img.srcset || '').split(',').map((item) => item.trim().split(/\s+/)[0]),
    ];
    return values.filter(Boolean).map((url) => new URL(url, location.href).href);
  };

  const seen = new Set();
  const images = [];
  for (const img of root.querySelectorAll('img')) {
    if (img.closest('[class*="comment"], [class*="avatar"], [class*="author"]')) continue;
    if (img.naturalWidth && img.naturalWidth < 300) continue;
    if (img.naturalHeight && img.naturalHeight < 300) continue;

    const url = candidates(img).find((value) =>
      /(^|\.)xhscdn\.com\//.test(new URL(value).hostname + '/') &&
      !/avatar|comment|emoji/i.test(value)
    );
    if (!url || seen.has(url)) continue;
    seen.add(url);
    images.push({
      index: images.length + 1,
      url,
      width: img.naturalWidth || null,
      height: img.naturalHeight || null,
      alt: img.alt?.trim() || '',
    });
  }

  const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;
  const noteId = canonical.match(/\/explore\/([a-zA-Z0-9]+)/)?.[1] || '';
  return {
    schemaVersion: 1,
    extractedAt: new Date().toISOString(),
    noteId,
    url: canonical,
    title: text(['#detail-title', '.title', '[class*="title"]']),
    author: text(['.author-wrapper .name', '.author .name', '[class*="author"] [class*="name"]']),
    content: text(['#detail-desc', '.desc', '[class*="desc"]']),
    images,
  };
})();
