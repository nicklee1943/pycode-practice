// 登入狀態（多人模式）：使用者列、登出、管理員連結、每人獨立的瀏覽器暫存。
// 單人模式下 PC.me.mode === 'single'，這裡不會顯示任何東西，暫存的 key 也維持原本的名稱。
window.PC = { me: null, prefix: '' };
PC.key = (k) => PC.prefix + k;  // 瀏覽器暫存（localStorage）的 key：多人模式加上使用者編號，同一支手機換人登入也不會混在一起

// 任何 API 回 401（登入逾時、帳號被停用）→ 回到登入頁
(() => {
  const orig = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const res = await orig(...args);
    const url = String(args[0] && args[0].url || args[0]);
    if (res.status === 401 && url.startsWith('/api/') && !url.startsWith('/api/login')) {
      location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search + location.hash);
    }
    return res;
  };
})();

PC.ready = (async () => {
  try {
    const r = await fetch('/api/me');
    if (!r.ok) return;
    PC.me = await r.json();
    if (PC.me.user) PC.prefix = 'u' + PC.me.user.id + ':';
  } catch { return; }
  const bar = document.getElementById('user-bar');
  if (!bar || !PC.me.user) return;
  const u = PC.me.user;
  const e = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  bar.innerHTML = `<span class="user-name" title="目前登入的帳號">👤 ${e(u.username)}</span>`
    + (u.is_admin ? '<a class="btn" href="/admin" target="pycode-admin" title="帳號管理與每個人的進度">⚙ 管理</a>' : '')
    + '<button class="btn" id="btn-logout" title="登出">登出</button>';
  document.getElementById('btn-logout').onclick = async () => {
    await fetch('/api/logout', { method: 'POST' });
    location.href = '/login';
  };
})();
