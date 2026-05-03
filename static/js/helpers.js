// ── Formatting helpers ────────────────────────────────────────────────────────
function formatDate(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric'
  });
}

function formatRelative(isoStr) {
  if (!isoStr) return '—';
  const diff = (Date.now() - new Date(isoStr)) / 1000;
  if (diff < 60)        return 'Just now';
  if (diff < 3600)      return Math.floor(diff / 60)    + ' min ago';
  if (diff < 86400)     return Math.floor(diff / 3600)  + ' hr ago';
  if (diff < 2592000)   return Math.floor(diff / 86400) + ' days ago';
  return formatDate(isoStr);
}

function formatDuration(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${m}:${String(s).padStart(2,'0')}`;
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B','KB','MB','GB'];
  let i = 0;
  while (bytes >= 1024 && i < 3) { bytes /= 1024; i++; }
  return bytes.toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
}

function getInitials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).slice(0,2).join('').toUpperCase();
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  const icons = { success:'✅', error:'❌', info:'ℹ️', warning:'⚠️' };
  toast.className = 'toast toast-' + type;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span>${escHtml(msg)}</span>`;
  container.appendChild(toast);
  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
