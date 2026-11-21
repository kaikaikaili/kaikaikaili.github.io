// email-guard.js — 防爬虫邮箱收割
// HTML 源码中不含明文邮箱；脚本运行时解码 base64 并填充 mailto 链接与显示文本。
// 用法：
//   仅填充链接：<a href="#" data-email><i class="fas fa-envelope"></i></a>
//   填充链接+文本：<a href="#" data-email="bGlrYWkyMjEyMDAwMzFAcXEuY29t" data-email-text></a>
//   data-email 的值为邮箱的 base64；缺省用默认地址。
(function () {
  var DEFAULT = 'MjIxMjAwMDMxQHNtYWlsLm5qdS5lZHUuY24=';
  document.querySelectorAll('[data-email]').forEach(function (el) {
    var addr = atob(el.getAttribute('data-email') || DEFAULT);
    el.setAttribute('href', 'mailto:' + addr);
    if (el.hasAttribute('data-email-text') && !el.textContent.trim()) {
      el.textContent = addr;
    }
  });
})();
