// ── API client ────────────────────────────────────────────────────────────────
const api = {
  _base: '/api',

  _headers() {
    const h = { 'Content-Type': 'application/json' };
    const t = localStorage.getItem('token');
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  },

  async _handle(resp) {
    let data;
    try { data = await resp.json(); } catch { data = {}; }
    if (!resp.ok) {
      const msg = data.message || data.detail || ('HTTP ' + resp.status);
      throw new Error(msg);
    }
    return data;
  },

  async get(path, skipAuth = false) {
    const headers = skipAuth ? {} : this._headers();
    const resp = await fetch(this._base + path, { headers });
    return this._handle(resp);
  },

  async post(path, body) {
    const resp = await fetch(this._base + path, {
      method:  'POST',
      headers: this._headers(),
      body:    JSON.stringify(body),
    });
    return this._handle(resp);
  },

  async put(path, body) {
    const resp = await fetch(this._base + path, {
      method:  'PUT',
      headers: this._headers(),
      body:    JSON.stringify(body),
    });
    return this._handle(resp);
  },

  async patch(path, body) {
    const resp = await fetch(this._base + path, {
      method:  'PATCH',
      headers: this._headers(),
      body:    JSON.stringify(body),
    });
    return this._handle(resp);
  },

  async del(path) {
    const resp = await fetch(this._base + path, {
      method:  'DELETE',
      headers: this._headers(),
    });
    return this._handle(resp);
  },

  // Multipart upload with progress
  async upload(path, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', this._base + path);
      const t = localStorage.getItem('token');
      if (t) xhr.setRequestHeader('Authorization', 'Bearer ' + t);

      if (onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        });
      }

      xhr.onload = () => {
        let data;
        try { data = JSON.parse(xhr.responseText); } catch { data = {}; }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data);
        } else {
          reject(new Error(data.message || ('HTTP ' + xhr.status)));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },
};
