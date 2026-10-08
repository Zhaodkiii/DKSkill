/*
 * 在已打开的小红书图文笔记详情页中执行本文件。
 * 返回可直接保存为 JSON 的笔记正文、作者、详情页 URL 和网页正文图片链接。
 */
(() => {
  if (!/\/(?:explore|discovery\/item)\/[a-zA-Z0-9]+/.test(location.pathname)) {
    throw new Error('需要单篇笔记详情链接；不能从搜索页下载缩略图');
  }
  const root = document.querySelector('#noteContainer, .note-container');
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
    if (img.closest('.swiper-slide-duplicate, [class*="comment"], [class*="avatar"], [class*="author"]')) continue;
    if (img.naturalWidth && img.naturalWidth < 300) continue;
    if (img.naturalHeight && img.naturalHeight < 300) continue;

    const url = candidates(img).find((value) =>
      /(^|\.)xhscdn\.com\//.test(new URL(value).hostname + '/') &&
      !/avatar|comment|emoji/i.test(value)
    );
    if (!url) continue;
    // CDN 签名目录、协议及尺寸后缀会变化；末段图片 ID 才是同图标识。
    const key = new URL(url).pathname.split('/').pop().split('!')[0];
    if (seen.has(key)) continue;
    seen.add(key);
    images.push({
      index: images.length + 1,
      url,
      width: img.naturalWidth || null,
      height: img.naturalHeight || null,
      alt: img.alt?.trim() || '',
    });
  }

  const canonical = location.href; // 保留详情链接中的访问参数
  const noteId = canonical.match(/\/(?:explore|discovery\/item)\/([a-zA-Z0-9]+)/)?.[1] || '';
  return {
    schemaVersion: 1,
    extractedAt: new Date().toISOString(),
    noteId,
    url: canonical,
    title: text(['#detail-title', '.title', '[class*="title"]']),
    author: text(['.author-wrapper .name', '.author .name', '[class*="author"] [class*="name"]']),
    content: text(['#detail-desc', '.desc', '[class*="desc"]']),
    pageImageCount: Number(root.innerText?.match(/(?:^|\n)\s*\d+\s*\/\s*(\d+)\s*(?:\n|$)/)?.[1]) || null,
    images,
  };
})();
