document.addEventListener('DOMContentLoaded', () => {
  // Tab Switching
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add('active');

      if (btn.dataset.tab === 'tab-queue') loadQueue();
      if (btn.dataset.tab === 'tab-history') loadHistory();
      if (btn.dataset.tab === 'tab-logs') loadLogs();
    });
  });

  // Load Initial Data
  loadStatus();
  loadSettings();
  loadQueue();

  // Topbar Actions
  document.getElementById('btn-sync-drive').addEventListener('click', async () => {
    const btn = document.getElementById('btn-sync-drive');
    btn.disabled = true;
    btn.innerText = '⏳ Đang quét...';
    try {
      const res = await fetch('/api/actions/sync-drive', { method: 'POST' });
      const data = await res.json();
      alert(data.message || 'Đã kích hoạt quét Drive!');
      setTimeout(() => {
        loadStatus();
        loadQueue();
      }, 1500);
    } catch (err) {
      alert('Lỗi: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerText = '🔄 Đồng bộ Drive';
    }
  });

  document.getElementById('btn-publish-next').addEventListener('click', async () => {
    if (!confirm('Bạn có chắc muốn đăng ngay bài viết kế tiếp trong hàng đợi?')) return;
    try {
      const res = await fetch('/api/actions/publish-now', { method: 'POST' });
      const data = await res.json();
      alert(data.message || 'Đã kích hoạt đăng bài!');
      setTimeout(() => {
        loadStatus();
        loadQueue();
        loadHistory();
      }, 1500);
    } catch (err) {
      alert('Lỗi: ' + err.message);
    }
  });

  document.getElementById('btn-refresh-logs')?.addEventListener('click', loadLogs);

  // Forms
  document.getElementById('schedule-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const settings = {
      schedule_cron: document.getElementById('cfg-schedule-cron').value.trim(),
      sync_interval_minutes: document.getElementById('cfg-sync-interval').value.trim(),
      default_caption: document.getElementById('cfg-default-caption').value.trim(),
      enable_facebook: document.getElementById('cfg-enable-fb').checked ? 'true' : 'false',
      enable_instagram: document.getElementById('cfg-enable-ig').checked ? 'true' : 'false',
      enable_tiktok: document.getElementById('cfg-enable-tiktok').checked ? 'true' : 'false',
    };
    await saveSettingsPayload(settings);
  });

  document.getElementById('accounts-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const settings = {
      drive_folder_id: document.getElementById('cfg-drive-folder-id').value.trim(),
      fb_page_id: document.getElementById('cfg-fb-page-id').value.trim(),
      ig_account_id: document.getElementById('cfg-ig-account-id').value.trim(),
      fb_access_token: document.getElementById('cfg-fb-token').value.trim(),
      tiktok_access_token: document.getElementById('cfg-tiktok-token').value.trim()
    };
    await saveSettingsPayload(settings);
  });
});

// Load System Status & Connection Pills
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    document.getElementById('stat-total').innerText = data.stats.total;
    document.getElementById('stat-pending').innerText = data.stats.pending;
    document.getElementById('stat-published').innerText = data.stats.published;
    document.getElementById('stat-failed').innerText = data.stats.failed;

    // Badges
    setPill('pill-drive', data.channels.google_drive);
    setPill('pill-fb', data.channels.facebook);
    setPill('pill-ig', data.channels.instagram);
    setPill('pill-tiktok', data.channels.tiktok);
  } catch (err) {
    console.error('Lỗi khi tải status:', err);
  }
}

function setPill(id, isConnected) {
  const el = document.getElementById(id);
  if (!el) return;
  if (isConnected) {
    el.classList.add('connected');
  } else {
    el.classList.remove('connected');
  }
}

// Load Settings
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const data = await res.json();
    const s = data.settings || {};

    if (document.getElementById('cfg-schedule-cron')) document.getElementById('cfg-schedule-cron').value = s.schedule_cron || '0 9,15,20 * * *';
    if (document.getElementById('cfg-sync-interval')) document.getElementById('cfg-sync-interval').value = s.sync_interval_minutes || '30';
    if (document.getElementById('cfg-default-caption')) document.getElementById('cfg-default-caption').value = s.default_caption || '';
    
    if (document.getElementById('cfg-enable-fb')) document.getElementById('cfg-enable-fb').checked = s.enable_facebook === 'true';
    if (document.getElementById('cfg-enable-ig')) document.getElementById('cfg-enable-ig').checked = s.enable_instagram === 'true';
    if (document.getElementById('cfg-enable-tiktok')) document.getElementById('cfg-enable-tiktok').checked = s.enable_tiktok === 'true';

    if (document.getElementById('cfg-drive-folder-id')) document.getElementById('cfg-drive-folder-id').value = s.drive_folder_id || '';
    if (document.getElementById('cfg-fb-page-id')) document.getElementById('cfg-fb-page-id').value = s.fb_page_id || '';
    if (document.getElementById('cfg-ig-account-id')) document.getElementById('cfg-ig-account-id').value = s.ig_account_id || '';
    if (document.getElementById('cfg-fb-token')) document.getElementById('cfg-fb-token').value = s.fb_access_token || '';
    if (document.getElementById('cfg-tiktok-token')) document.getElementById('cfg-tiktok-token').value = s.tiktok_access_token || '';
  } catch (err) {
    console.error('Lỗi load settings:', err);
  }
}

async function saveSettingsPayload(settings) {
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings })
    });
    const data = await res.json();
    alert(data.message || 'Đã lưu cấu hình!');
    loadStatus();
  } catch (err) {
    alert('Lỗi lưu cài đặt: ' + err.message);
  }
}

// Load Queue
async function loadQueue() {
  const container = document.getElementById('queue-container');
  if (!container) return;
  container.innerHTML = '<div style="color:#8b949e">Đang tải danh sách chờ...</div>';

  try {
    const res = await fetch('/api/posts?status=pending');
    const data = await res.json();
    const posts = data.posts || [];

    if (posts.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding: 40px; color:#8b949e; background:#161b22; border-radius:10px; border:1px dashed #30363d">
          <div style="font-size: 2.4rem; margin-bottom: 10px;">📭</div>
          <p style="font-weight:600">Hàng đợi đang trống!</p>
          <p style="font-size:0.85rem; margin-top:6px;">Bấm nút <b>"🔄 Đồng bộ Drive"</b> phía trên để kéo ảnh mới từ Google Drive về hàng đợi.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = posts.map(p => `
      <div class="queue-card" id="post-card-${p.id}">
        <div class="queue-img-wrap">
          <img src="${p.thumbnail_url || 'https://via.placeholder.com/400x300?text=No+Preview'}" alt="${p.file_name}" loading="lazy">
        </div>
        <div class="queue-card-body">
          <div class="queue-card-title" title="${p.file_name}">${p.file_name}</div>
          <textarea class="caption-input" id="caption-${p.id}" placeholder="Nhập caption cho bài viết...">${p.caption || ''}</textarea>
          
          <div class="platform-tags">
            ${(p.platforms || []).map(plat => `<span class="tag-badge">${plat.toUpperCase()}</span>`).join('')}
          </div>

          <div class="queue-card-actions">
            <button class="btn btn-sm btn-secondary" onclick="updateCaption(${p.id})">💾 Lưu Caption</button>
            <button class="btn btn-sm btn-danger" onclick="deletePost(${p.id})">🗑 Xóa</button>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:#f85149">Lỗi tải hàng đợi: ${err.message}</div>`;
  }
}

// Update caption
window.updateCaption = async function(id) {
  const caption = document.getElementById(`caption-${id}`).value;
  try {
    await fetch(`/api/posts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caption })
    });
    alert('Đã cập nhật caption bài viết!');
  } catch (err) {
    alert('Lỗi: ' + err.message);
  }
};

// Delete post
window.deletePost = async function(id) {
  if (!confirm('Xóa bài viết này khỏi hàng đợi?')) return;
  try {
    await fetch(`/api/posts/${id}`, { method: 'DELETE' });
    document.getElementById(`post-card-${id}`)?.remove();
    loadStatus();
  } catch (err) {
    alert('Lỗi: ' + err.message);
  }
};

// Load History
async function loadHistory() {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/posts?limit=50');
    const data = await res.json();
    const posts = (data.posts || []).filter(p => p.status !== 'pending');

    if (posts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#8b949e">Chưa có bài viết nào được xuất bản.</td></tr>';
      return;
    }

    tbody.innerHTML = posts.map(p => `
      <tr>
        <td>#${p.id}</td>
        <td><img src="${p.thumbnail_url || ''}" class="table-thumb" alt=""></td>
        <td style="font-weight:600">${p.file_name}</td>
        <td style="max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">${p.caption || ''}</td>
        <td>${(p.platforms || []).join(', ')}</td>
        <td><span class="status-pill status-${p.status}">${p.status}</span></td>
        <td style="font-size:0.8rem; color:#8b949e">${p.published_at || p.created_at}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:#f85149">Lỗi: ${err.message}</td></tr>`;
  }
}

// Load Logs
async function loadLogs() {
  const container = document.getElementById('log-container');
  if (!container) return;

  try {
    const res = await fetch('/api/logs?limit=40');
    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length === 0) {
      container.innerHTML = '<div style="color:#6e7681">Chưa có bản ghi log nào.</div>';
      return;
    }

    container.innerHTML = logs.map(l => `
      <div class="log-line">
        <span class="log-time">[${l.created_at}]</span>
        <span class="log-level-${l.level}">[${l.level}]</span>
        <span class="log-msg">${l.message}</span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:#f85149">Lỗi: ${err.message}</div>`;
  }
}
