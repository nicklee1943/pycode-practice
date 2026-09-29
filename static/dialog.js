// 頁面內的確認視窗。取代瀏覽器原生的 confirm()：
// 有些瀏覽器（例如內嵌的瀏覽器面板）會停用原生對話框，confirm() 直接回傳 false，導致操作無法進行。
// 用法：if (!(await askConfirm('訊息', { okText: '切換', danger: true }))) return;
(function () {
  const css = `
    .cf-mask { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.55);
      display: flex; align-items: center; justify-content: center; padding: 16px; }
    .cf-box { width: 420px; max-width: 100%; background: #262626; color: #e8e8e8; border: 1px solid #3a3a3a;
      border-radius: 12px; box-shadow: 0 12px 40px rgba(0,0,0,.5); padding: 20px 20px 16px;
      font-family: -apple-system, "Segoe UI", "Microsoft JhengHei", "PingFang TC", sans-serif; }
    .cf-title { font-size: 16px; font-weight: 700; margin-bottom: 10px; }
    .cf-msg { font-size: 14px; line-height: 1.7; white-space: pre-wrap; color: #cfcfcf; }
    .cf-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
    .cf-actions button { font: inherit; font-size: 14px; cursor: pointer; border: none; border-radius: 6px; padding: 7px 16px; }
    .cf-cancel { background: #3a3a3a; color: #e8e8e8; }
    .cf-cancel:hover { background: #454545; }
    .cf-ok { background: #ffa116; color: #1a1a1a; font-weight: 600; }
    .cf-ok.danger { background: #ef4743; color: #fff; }
    .cf-ok:hover { filter: brightness(1.08); }
    .cf-choices { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; max-height: 50vh; overflow-y: auto; }
    .cf-choice { display: flex; justify-content: space-between; align-items: center; gap: 12px; text-align: left;
      font: inherit; font-size: 14px; cursor: pointer; border: 1px solid #3a3a3a; border-radius: 8px;
      padding: 10px 14px; background: #303030; color: #e8e8e8; }
    .cf-choice:hover, .cf-choice:focus { border-color: #ffa116; outline: none; }
    .cf-choice-hint { font-size: 12px; color: #9a9a9a; white-space: nowrap; }`;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // 多選一：choices = [{ value, label, hint }]；回傳選到的 value，取消回傳 null。
  // 沒有 choices 時就是只有「確定」的訊息視窗。
  window.askChoice = function (message, opts = {}) {
    return new Promise((resolve) => {
      const mask = document.createElement('div');
      mask.className = 'cf-mask';
      mask.innerHTML = `
        <div class="cf-box" role="dialog" aria-modal="true">
          <div class="cf-title"></div>
          <div class="cf-msg"></div>
          <div class="cf-choices"></div>
          <div class="cf-actions"><button class="cf-cancel" type="button"></button></div>
        </div>`;
      mask.querySelector('.cf-title').textContent = opts.title || '請選擇';
      mask.querySelector('.cf-msg').textContent = message || '';
      const list = mask.querySelector('.cf-choices');
      (opts.choices || []).forEach((c) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'cf-choice';
        b.innerHTML = '<span class="cf-choice-label"></span><span class="cf-choice-hint"></span>';
        b.querySelector('.cf-choice-label').textContent = c.label;
        b.querySelector('.cf-choice-hint').textContent = c.hint || '';
        b.onclick = () => done(c.value);
        list.appendChild(b);
      });
      const cancel = mask.querySelector('.cf-cancel');
      cancel.textContent = opts.cancelText || (opts.choices?.length ? '取消' : '確定');
      const done = (answer) => {
        document.removeEventListener('keydown', onKey, true);
        mask.remove();
        resolve(answer);
      };
      const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(null); } };
      cancel.onclick = () => done(null);
      mask.onclick = (e) => { if (e.target === mask) done(null); };
      document.addEventListener('keydown', onKey, true);
      document.body.appendChild(mask);
      (list.querySelector('button') || cancel).focus();
    });
  };

  // 輸入一行文字：回傳輸入的內容，取消回傳 null。opts.type 可設 'password'。
  window.askText = function (message, opts = {}) {
    return new Promise((resolve) => {
      const mask = document.createElement('div');
      mask.className = 'cf-mask';
      mask.innerHTML = `
        <div class="cf-box" role="dialog" aria-modal="true">
          <div class="cf-title"></div>
          <div class="cf-msg"></div>
          <input class="cf-input" style="width:100%;box-sizing:border-box;font-size:16px;padding:10px;margin:4px 0 14px;border-radius:8px;border:1px solid #3a3a3a;background:#303030;color:#e8e8e8">
          <div class="cf-actions">
            <button class="cf-cancel" type="button"></button>
            <button class="cf-ok" type="button"></button>
          </div>
        </div>`;
      mask.querySelector('.cf-title').textContent = opts.title || '請輸入';
      mask.querySelector('.cf-msg').textContent = message || '';
      const input = mask.querySelector('.cf-input');
      input.type = opts.type || 'text';
      input.value = opts.value || '';
      if (opts.type === 'password') input.autocomplete = 'new-password';
      mask.querySelector('.cf-cancel').textContent = opts.cancelText || '取消';
      mask.querySelector('.cf-ok').textContent = opts.okText || '確定';
      const done = (answer) => {
        document.removeEventListener('keydown', onKey, true);
        mask.remove();
        resolve(answer);
      };
      const onKey = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(null); }
        if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); done(input.value); }
      };
      mask.querySelector('.cf-cancel').onclick = () => done(null);
      mask.querySelector('.cf-ok').onclick = () => done(input.value);
      document.addEventListener('keydown', onKey, true);
      document.body.appendChild(mask);
      input.focus();
    });
  };

  window.askConfirm = function (message, opts = {}) {
    return new Promise((resolve) => {
      const mask = document.createElement('div');
      mask.className = 'cf-mask';
      mask.innerHTML = `
        <div class="cf-box" role="dialog" aria-modal="true">
          <div class="cf-title"></div>
          <div class="cf-msg"></div>
          <div class="cf-actions">
            <button class="cf-cancel" type="button"></button>
            <button class="cf-ok ${opts.danger ? 'danger' : ''}" type="button"></button>
          </div>
        </div>`;
      mask.querySelector('.cf-title').textContent = opts.title || '請確認';
      mask.querySelector('.cf-msg').textContent = message;
      mask.querySelector('.cf-cancel').textContent = opts.cancelText || '取消';
      mask.querySelector('.cf-ok').textContent = opts.okText || '確定';

      const done = (answer) => {
        document.removeEventListener('keydown', onKey, true);
        mask.remove();
        resolve(answer);
      };
      const onKey = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(false); }
        if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); done(true); }
      };
      mask.querySelector('.cf-cancel').onclick = () => done(false);
      mask.querySelector('.cf-ok').onclick = () => done(true);
      mask.onclick = (e) => { if (e.target === mask) done(false); };
      document.addEventListener('keydown', onKey, true);
      document.body.appendChild(mask);
      mask.querySelector('.cf-ok').focus();
    });
  };
})();
