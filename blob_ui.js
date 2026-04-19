// ===================== CONFIG =====================
const WEBHOOK_URL = `${window.location.origin}/chat`;

const SESSION_ICONS = {
  standard:     `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`,
  coding:       `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
  architecture: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`,
  study:        `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`,
};

const SESSIONS = [
  { id: 'standard',     label: 'Standard',     },
  { id: 'coding',       label: 'Coding',        },
  { id: 'architecture', label: 'Architecture',  },
  { id: 'study',        label: 'Study',         },
];

// ===================== STATE =====================
const state = {
  chatHistory: [],
  isLoading: false,
  currentSession: localStorage.getItem('accel_active_session') || 'standard',
};

let pendingImages = []; // Array of { base64, name, size, file }
let pendingFiles = [];  // Array of { content, name, size, language }

// ===================== INIT =====================
const UI_VERSION = '202604191200';

document.addEventListener('DOMContentLoaded', () => {
  debugLog(`UI version: ${UI_VERSION}`, 'info');
  loadSettings();
  setupTextarea();
  setupImageInput();   
  setupDragDrop();     
  setupPasteImage();   
  createImageViewer(); 
  setupFileDrop();
});

function loadSettings() {
  updateWebhookDisplay();
  updateStatus('configured');
  renderSessionSidebar();
  loadSessionHistory();

  loadToolSettings();
}

const TOOL_LABELS = {
  bash:                 { label: 'bash',                 desc: 'Shell command execution',           irreversible: true },
  write_file:           { label: 'write_file',           desc: 'Create or overwrite files',         irreversible: true },
  edit_file:            { label: 'edit_file',            desc: 'Edit existing files',               irreversible: true },
  delete_file:          { label: 'delete_file',          desc: 'Delete a file',                     irreversible: true },
  move_file:            { label: 'move_file',            desc: 'Move or rename a file',             irreversible: true },
  read_file:            { label: 'read_file',            desc: 'Read file contents',                irreversible: false },
  get_file_info:        { label: 'get_file_info',        desc: 'File metadata and permissions',     irreversible: false },
  search_files:         { label: 'search_files',         desc: 'Search by name or content',         irreversible: false },
  list_dir:             { label: 'list_dir',             desc: 'List directory contents',           irreversible: false },
  search_web:           { label: 'search_web',           desc: 'Web search via SearXNG',            irreversible: false },
  fetch_url:            { label: 'fetch_url',            desc: 'Fetch and read a URL',              irreversible: false },
  screenshot_url:       { label: 'screenshot_url',       desc: 'Screenshot a web page',             irreversible: false },
  calculate:            { label: 'calculate',            desc: 'Evaluate a math expression',        irreversible: false },
  calendar_today:       { label: 'calendar_today',       desc: 'Get today\'s calendar info',        irreversible: false },
  calendar_get_events:  { label: 'calendar_get_events',  desc: 'Get events and holidays',           irreversible: false },
  calendar_add_event:   { label: 'calendar_add_event',   desc: 'Add a calendar event',              irreversible: true },
  calendar_delete_event:{ label: 'calendar_delete_event',desc: 'Delete a calendar event',           irreversible: true },
  convert_units:        { label: 'convert_units',        desc: 'Convert physical units',            irreversible: false },
  convert_currency:     { label: 'convert_currency',     desc: 'Convert currencies (live rates)',   irreversible: false },
};

let _toolSettings = {};

async function loadToolSettings() {
  try {
    const resp = await fetch('/settings/tools', { signal: AbortSignal.timeout(5000) });
    if (resp.ok) {
      const data = await resp.json();
      _toolSettings = data.tool_settings || {};
      renderToolSettings();
    }
  } catch (_) {}
}

function renderToolSettings() {
  const container = document.getElementById('toolSettingsList');
  if (!container) return;
  container.innerHTML = Object.entries(TOOL_LABELS).map(([key, info]) => {
    const { label, desc } = info;
    const policy = _toolSettings[key] || (info.irreversible ? 'require' : 'auto');
    return `
      <div class="tool-setting-row">
        <div class="tool-setting-info">
          <span class="tool-setting-name">${label}</span>
          <span class="tool-setting-desc">${desc}</span>
        </div>
        <select class="tool-policy-select" onchange="updateToolSetting('${key}', this.value)">
          <option value="require" ${policy === 'require' ? 'selected' : ''}>Require approval</option>
          <option value="auto" ${policy === 'auto' ? 'selected' : ''}>Auto-approve</option>
        </select>
      </div>`;
  }).join('');
}

async function updateToolSetting(toolName, policy) {
  _toolSettings[toolName] = policy;
  try {
    await fetch('/settings/tools', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_settings: _toolSettings }),
    });
    showToast(`${toolName}: ${policy === 'auto' ? 'auto-approve' : 'approval required'}`, 'success', 2000);
  } catch (_) {}
}

async function loadSessionHistory() {
  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;
  const sid = state.currentSession;
  try {
    const resp = await fetch(`${getSplitterBase()}/session?session_id=${sid}&t=${Date.now()}`, { signal: AbortSignal.timeout(8000) });
    if (resp.ok) {
      const data = await resp.json();
      const messages = data.messages || [];
      if (messages.length > 0) {
        state.chatHistory = messages;
        localStorage.setItem(`accel_chat_${sid}`, JSON.stringify(messages));
        document.getElementById('welcomeMessage').style.display = 'none';
        messages.forEach((msg) =>
          renderMessage(msg.role, msg.content, msg.timestamp, false, msg.images || [], msg.files || [], msg.thoughts || '')
        );
        scrollToBottom();
        startSessionPolling();
        sendBtn.disabled = false;
        return;
      }
    }
  } catch (_) {
    // Server unreachable — fall through to localStorage
  }
  const chatSaved = localStorage.getItem(`accel_chat_${sid}`);
  if (chatSaved) {
    try {
      state.chatHistory = JSON.parse(chatSaved);
      if (state.chatHistory.length > 0) {
        document.getElementById('welcomeMessage').style.display = 'none';
        state.chatHistory.forEach((msg) =>
          renderMessage(msg.role, msg.content, msg.timestamp, false, msg.images || [], msg.files || [], msg.thoughts || '')
        );
        scrollToBottom();
      }
    } catch (_) {}
  }
  startSessionPolling();
  sendBtn.disabled = false;
}

let _pollTimer = null;

function startSessionPolling() {
  if (_pollTimer) return;
  _pollTimer = setInterval(pollSession, 10000);
}

async function pollSession() {
  if (state.isLoading) return;
  const sid = state.currentSession;
  try {
    const resp = await fetch(`${getSplitterBase()}/session?session_id=${sid}&t=${Date.now()}`, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) return;
    const { messages = [] } = await resp.json();
    if (!messages.length) return;

    const localLen = state.chatHistory.length;
    const serverLen = messages.length;
    const localLast = state.chatHistory[localLen - 1];
    const serverLast = messages[serverLen - 1];

    // Already in sync
    if (localLen === serverLen &&
        localLast?.role === serverLast?.role &&
        localLast?.content === serverLast?.content) return;

    // Server has more and local is a prefix — append only (common case: other device sent)
    if (serverLen > localLen &&
        localLen > 0 &&
        localLast?.content === messages[localLen - 1]?.content &&
        localLast?.role === messages[localLen - 1]?.role) {
      const newMsgs = messages.slice(localLen);
      state.chatHistory = messages;
      localStorage.setItem(`accel_chat_${sid}`, JSON.stringify(messages));
      document.getElementById('welcomeMessage').style.display = 'none';
      newMsgs.forEach((msg) =>
        renderMessage(msg.role, msg.content, msg.timestamp, false, msg.images || [], msg.files || [], msg.thoughts || '')
      );
      scrollToBottom();
      return;
    }

    // Histories diverged (stale local from old session, or device switch) — full replace
    state.chatHistory = messages;
    localStorage.setItem(`accel_chat_${sid}`, JSON.stringify(messages));
    const container = document.getElementById('chatContainer');
    container.innerHTML = '';
    messages.forEach((msg) =>
      renderMessage(msg.role, msg.content, msg.timestamp, false, msg.images || [], msg.files || [], msg.thoughts || '')
    );
    scrollToBottom();
  } catch (_) {}
}


// ===================== UI HELPERS =====================
function toggleSettings() {
  const open = document.getElementById('settingsPanel').classList.toggle('open');
  if (!open) document.getElementById('knowledgePanel').classList.remove('open');
}

function toggleDebug() {
  document.getElementById('debugPanel').classList.toggle('open');
}

function toggleKnowledge() {
  document.getElementById('knowledgePanel').classList.toggle('open');
}


async function indexVault() {
  const btn = document.getElementById('vaultBtn');
  const status = document.getElementById('vaultBtnStatus');
  btn.disabled = true;
  status.innerHTML = '<span class="kb-spinner"></span>';

  try {
    const resp = await fetch(`${getSplitterBase()}/ingest/vault`, { method: 'POST' });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      status.textContent = 'Failed';
      setTimeout(() => { status.textContent = ''; }, 4000);
    } else {
      const result = await resp.json();
      const errCount = result.errors?.length || 0;
      const pct = result.total_files ? Math.round(result.ingested / result.total_files * 100) : 100;
      status.textContent = errCount
        ? `${pct}% — ${result.ingested}/${result.total_files} (${errCount} err)`
        : `${pct}% — ${result.ingested} notes indexed`;
      setTimeout(() => { status.textContent = ''; }, 5000);
    }
  } catch (e) {
    status.textContent = 'Failed';
    setTimeout(() => { status.textContent = ''; }, 4000);
  } finally {
    btn.disabled = false;
  }
}

async function ingestFiles(fileList) {
  const files = Array.from(fileList);
  if (!files.length) return;

  const sourceType = document.getElementById('kbSourceType').value;
  const title = document.getElementById('kbTitle').value.trim();
  const author = document.getElementById('kbAuthor').value.trim();

  const progressArea = document.getElementById('kbProgressArea');
  const progressList = document.getElementById('kbProgressList');
  const progressHeader = document.getElementById('kbProgressHeader');
  progressArea.style.display = 'block';
  progressList.innerHTML = '';
  if (progressHeader) progressHeader.textContent = `0 / ${files.length} (0%)`;

  const splitterBase = getSplitterBase();
  let done = 0, succeeded = 0, totalChunks = 0;
  const validFiles = files.filter(f => ['pdf','epub','txt','md','rst'].includes(f.name.split('.').pop().toLowerCase()));

  for (const file of validFiles) {
    const row = document.createElement('div');
    row.className = 'kb-file-row';
    row.innerHTML = `<span class="kb-file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span><span class="kb-status">Reading…</span>`;
    progressList.appendChild(row);
    const statusEl = row.querySelector('.kb-status');

    try {
      const arrayBuf = await file.arrayBuffer();
      const bytes = new Uint8Array(arrayBuf);
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      const b64 = btoa(binary);

      statusEl.textContent = 'Ingesting…';

      const resp = await fetch(`${splitterBase}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base64: b64, filename: file.name, source_type: sourceType, title: title || undefined, author: author || undefined }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        statusEl.textContent = `Failed: ${err.detail || resp.statusText}`;
        statusEl.style.color = 'var(--error)';
      } else {
        const result = await resp.json();
        totalChunks += result.chunks_stored || 0;
        succeeded++;
        statusEl.textContent = `${result.chunks_stored} chunks`;
        statusEl.style.color = 'var(--success)';
      }
    } catch (e) {
      statusEl.textContent = `Error: ${e.message}`;
      statusEl.style.color = 'var(--error)';
    }

    done++;
    const pct = Math.round(done / validFiles.length * 100);
    if (progressHeader) progressHeader.textContent = `${done} / ${validFiles.length} (${pct}%)`;
  }

  // summary row
  if (validFiles.length > 0) {
    const summary = document.createElement('div');
    summary.className = 'kb-summary';
    summary.textContent = `Done — ${succeeded}/${validFiles.length} files, ${totalChunks} total chunks`;
    progressList.appendChild(summary);
  }

  document.getElementById('kbTitle').value = '';
  document.getElementById('kbAuthor').value = '';
}

function updateWebhookDisplay() {
  document.getElementById('webhookDisplay').textContent = `${window.location.hostname}:8100/chat`;
}

function updateStatus(status) {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  dot.className = 'status-orb';

  switch (status) {
    case 'connected':
      dot.classList.add('connected');
      text.textContent = 'Connected';
      break;
    case 'error':
      dot.classList.add('error');
      text.textContent = 'Error';
      break;
    case 'waiting':
      dot.classList.add('waiting');
      text.textContent = 'Waiting...';
      break;
    case 'configured':
      text.textContent = 'Configured';
      break;
    default:
      text.textContent = 'Not configured';
  }
}

let _toastTimer = null;
function showToast(message, type = '', duration = 3500) {
  const toast = document.getElementById('toast');
  clearTimeout(_toastTimer);
  toast.textContent = message;
  toast.className = 'toast show ' + type;
  if (duration > 0) _toastTimer = setTimeout(() => (toast.className = 'toast'), duration);
}
function hideToast() {
  clearTimeout(_toastTimer);
  document.getElementById('toast').className = 'toast';
}

function scrollToBottom() {
  const container = document.getElementById('chatContainer');
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });
}

function debugLog(message, type = 'info') {
  const log = document.getElementById('debugLog');
  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = `log-entry log-${type}`;
  div.textContent = `[${time}] ${message}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function setupTextarea() {
  const textarea = document.getElementById('messageInput');
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    document.getElementById('charCount').textContent =
      textarea.value.length + ' chars';
  });
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

function getTimestamp() {
  return new Date().toISOString();
}

function formatTimestamp(ts) {
  if (!ts) return '';
  // Legacy HH:MM strings — display as-is
  if (/^\d{2}:\d{2}$/.test(ts)) return ts;
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (sameDay) return time;
  const sameYear = d.getFullYear() === now.getFullYear();
  const dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric', ...(!sameYear && { year: 'numeric' }) });
  return `${dateStr}, ${time}`;
}

function toggleFileContent(id) {
  const body = document.getElementById(id);
  const toggle = document.getElementById(id + '_toggle');
  if (body.classList.contains('expanded')) {
    body.classList.remove('expanded');
    toggle.textContent = '▶ Show';
  } else {
    body.classList.add('expanded');
    toggle.textContent = '▼ Hide';
  }
}

// ===================== MESSAGE RENDERING =====================
function toggleThinking(id) {
  const content = document.getElementById(id);
  const toggle = document.getElementById(id + '_toggle');
  const isOpen = content.classList.toggle('open');
  toggle.textContent = isOpen ? '▲ Hide' : '▼ Show';
}

function createStreamingMessage() {
  const container = document.getElementById('chatContainer');
  const welcome = document.getElementById('welcomeMessage');
  if (welcome) welcome.style.display = 'none';
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message bot streaming';
  msgDiv.innerHTML = `
    <div class="message-avatar"></div>
    <div class="message-body">
      <div class="thinking-stream" style="display:none"></div>
      <div class="tool-activity"></div>
      <div class="message-content"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    </div>`;
  container.appendChild(msgDiv);
  scrollToBottom();
  return msgDiv;
}

function appendToolCall(msgEl, toolName, args) {
  const area = msgEl.querySelector('.tool-activity');
  if (!area) return;
  const argsStr = typeof args === 'object' ? JSON.stringify(args, null, 2) : String(args);
  const block = document.createElement('div');
  block.className = 'tool-call-block';
  block.innerHTML = `
    <div class="tool-block-header">🔧 <strong>${escapeHtml(toolName)}</strong></div>
    <pre class="tool-block-args">${escapeHtml(argsStr)}</pre>`;
  area.appendChild(block);
  scrollToBottom();
}

function appendToolResult(msgEl, toolName, output, imageB64 = null, imageMime = 'image/png') {
  const area = msgEl.querySelector('.tool-activity');
  if (!area) return;
  if (imageB64) {
    const block = document.createElement('div');
    block.className = 'tool-result-block screenshot-result';
    const img = document.createElement('img');
    img.src = `data:${imageMime};base64,${imageB64}`;
    img.alt = 'Screenshot';
    img.className = 'screenshot-preview';
    img.onclick = () => viewImage(img.src);
    block.innerHTML = `<div class="tool-block-header">📸 <strong>${escapeHtml(toolName)}</strong> — screenshot</div>`;
    block.appendChild(img);
    area.appendChild(block);
  } else {
    const area = msgEl.querySelector('.tool-activity');
    if (!area) return;
    const truncated = output.length > 2000 ? output.slice(0, 2000) + '\n… (truncated)' : output;
    const block = document.createElement('div');
    block.className = 'tool-result-block';
    block.innerHTML = `
      <div class="tool-block-header">📤 <strong>${escapeHtml(toolName)}</strong> result</div>
      <pre class="tool-block-output">${escapeHtml(truncated)}</pre>`;
    area.appendChild(block);
  }
  scrollToBottom();
}

function appendApprovalRequest(msgEl, requestId, toolName, args) {
  const area = msgEl.querySelector('.tool-activity');
  if (!area) return;
  const argsStr = typeof args === 'object' ? JSON.stringify(args, null, 2) : String(args);
  const block = document.createElement('div');
  block.className = 'approval-block';
  block.id = `approval_${requestId}`;
  block.innerHTML = `
    <div class="tool-block-header">⚠️ <strong>${escapeHtml(toolName)}</strong> — requires approval</div>
    <pre class="tool-block-args">${escapeHtml(argsStr)}</pre>
    <div class="approval-buttons">
      <button class="approve-btn" onclick="resolveApproval('${requestId}', true)">✅ Approve</button>
      <button class="deny-btn" onclick="resolveApproval('${requestId}', false)">❌ Deny</button>
    </div>`;
  area.appendChild(block);
  scrollToBottom();
}

async function resolveApproval(requestId, approved) {
  const card = document.getElementById(`approval_${requestId}`);
  if (card) {
    card.innerHTML = `<div class="approval-resolved">${approved ? '✅ Approved' : '❌ Denied'}</div>`;
    card.className = `approval-block ${approved ? 'approved' : 'denied'}`;
  }
  try {
    await fetch(`/approve/${requestId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved }),
    });
  } catch (e) {
    debugLog(`Approval POST failed: ${e.message}`, 'error');
  }
}

function updateStreamingMessage(msgEl, text, thinking) {
  const contentEl = msgEl.querySelector('.message-content');
  const thinkEl = msgEl.querySelector('.thinking-stream');
  if (contentEl) {
    if (text) {
      contentEl.innerHTML = formatContent(text);
    }
    // else keep the three-dots placeholder
  }
  if (thinkEl) {
    if (thinking) {
      thinkEl.style.display = 'block';
      thinkEl.textContent = '🧠 Thinking…';
    } else {
      thinkEl.style.display = 'none';
    }
  }
}

function finalizeStreamingMessage(msgEl, text, thinking, save = true) {
  msgEl.classList.remove('streaming');
  const body = msgEl.querySelector('.message-body');

  // remove only the live thinking stream; keep tool-activity and screenshot-gallery
  body.querySelector('.thinking-stream')?.remove();

  // insert thinking block at the top if present
  if (thinking) {
    const thinkId = `think_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const block = document.createElement('div');
    block.className = 'thinking-block';
    block.innerHTML = `
      <div class="thinking-header" onclick="toggleThinking('${thinkId}')">
        <span class="thinking-icon">💭</span>
        <span>Thoughts</span>
        <span class="thinking-toggle" id="${thinkId}_toggle">▼ Show</span>
      </div>
      <div class="thinking-content" id="${thinkId}">${escapeHtml(thinking)}</div>`;
    body.insertBefore(block, body.firstChild);
  }

  // update message-content in place (already exists from streaming)
  const contentEl = body.querySelector('.message-content');
  if (contentEl) {
    contentEl.innerHTML = formatContent(text);
  } else {
    const div = document.createElement('div');
    div.className = 'message-content';
    div.innerHTML = formatContent(text);
    body.appendChild(div);
  }

  // append meta row
  const meta = document.createElement('div');
  meta.className = 'message-meta';
  meta.innerHTML = `<span>${formatTimestamp(getTimestamp())}</span><button class="copy-btn" onclick="copyMessage(this)">📋 Copy</button>`;
  body.appendChild(meta);

  if (save) {
    state.chatHistory.push({ role: 'bot', content: text, timestamp: getTimestamp(), thoughts: thinking || undefined });
    localStorage.setItem(`accel_chat_${state.currentSession}`, JSON.stringify(state.chatHistory));
  }
}

function renderMessage(role, content, timestamp, save = true, images = [], files = [], thoughts = '') {
  const container = document.getElementById('chatContainer');
  const welcome = document.getElementById('welcomeMessage');
  if (welcome) welcome.style.display = 'none';

  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${role}`;
  const avatar = '';

  // Images HTML
  let imagesHtml = '';
  if (images && images.length > 0) {
    const imgTags = images
      .map(
        (img) =>
          `<img src="${img.dataUrl || 'data:image/png;base64,' + img.base64}" alt="attached" onclick="viewImage(this.src)" />`
      )
      .join('');
    imagesHtml = `<div class="message-images">${imgTags}</div>`;
  }

  // Files HTML
  let filesHtml = '';
  if (files && files.length > 0) {
    const fileBlocks = files
      .map((f, i) => {
        const id = `file_${Date.now()}_${i}`;
        const icon = getFileIcon(f.language || 'text');
        return `
          <div class="file-attachment">
            <div class="file-attachment-header" onclick="toggleFileContent('${id}')">
              <span>${icon} ${escapeHtml(f.name)} (${formatFileSize(f.size || f.content.length)})</span>
              <span class="file-toggle" id="${id}_toggle">▶ Show</span>
            </div>
            <div class="file-attachment-body" id="${id}">
              <pre><code>${escapeHtml(f.content)}</code></pre>
            </div>
          </div>
        `;
      })
      .join('');
    filesHtml = `<div class="message-files">${fileBlocks}</div>`;
  }

  const thinkId = `think_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const thinkingHtml = (role === 'bot' && thoughts) ? `
    <div class="thinking-block">
      <div class="thinking-header" onclick="toggleThinking('${thinkId}')">
        <span class="thinking-icon">💭</span>
        <span>Thoughts</span>
        <span class="thinking-toggle" id="${thinkId}_toggle">▼ Show</span>
      </div>
      <div class="thinking-content" id="${thinkId}">${escapeHtml(thoughts)}</div>
    </div>` : '';

  msgDiv.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      ${imagesHtml}
      ${filesHtml}
      ${thinkingHtml}
      <div class="message-content">${formatContent(content)}</div>
      <div class="message-meta">
        <span>${formatTimestamp(timestamp || getTimestamp())}</span>
        <button class="copy-btn" onclick="copyMessage(this)">📋 Copy</button>
      </div>
    </div>
  `;
  container.appendChild(msgDiv);

  if (save) {
    const savedImages = images.map((img) => ({
      base64: img.base64,
      name: img.name,
      type: img.type || 'image/png',
    }));

    const savedFiles = files.map((f) => ({
      content: f.content,
      name: f.name,
      language: f.language,
      size: f.size,
    }));

    state.chatHistory.push({
      role,
      content,
      timestamp: timestamp || getTimestamp(),
      images: savedImages.length > 0 ? savedImages : undefined,
      files: savedFiles.length > 0 ? savedFiles : undefined,
      thoughts: thoughts || undefined,
    });
    localStorage.setItem(`accel_chat_${state.currentSession}`, JSON.stringify(state.chatHistory));
  }
}

function renderError(message) {
  const container = document.getElementById('chatContainer');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message error bot';
  msgDiv.innerHTML = `
    <div class="message-avatar"></div>
    <div class="message-body">
      <div class="message-content"><strong>Error:</strong> ${escapeHtml(message)}</div>
      <div class="message-meta"><span>${formatTimestamp(getTimestamp())}</span></div>
    </div>
  `;
  container.appendChild(msgDiv);
}

function showTypingIndicator() {
  const container = document.getElementById('chatContainer');
  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  typing.id = 'typingIndicator';
  typing.innerHTML = `
    <div class="message-avatar" style="background:linear-gradient(135deg,#f97316,#ea580c);animation:miniBlobMorph 3s ease-in-out infinite;"></div>
    <div class="typing-dots"><span></span><span></span><span></span></div>
  `;
  container.appendChild(typing);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function formatContent(text) {
  let html = escapeHtml(text);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  html = html.replace(
    /`([^`]+)`/g,
    '<code>$1</code>'
  );
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyMessage(btn) {
  const content = btn.closest('.message').querySelector('.message-content').textContent;
  navigator.clipboard.writeText(content).then(() => {
    btn.textContent = '✅ Copied';
    setTimeout(() => (btn.textContent = '📋 Copy'), 2000);
  });
}

// ===================== IMAGE HANDLING =====================
function setupImageInput() {
  const fileInput = document.getElementById('imageInput');
  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = '';
  });
}

function setupFileDrop() {
  // Extend existing drag/drop to handle all file types
  const wrapper = document.getElementById('inputWrapper');

  // Override the existing drop handler to use handleFiles
  wrapper.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    wrapper.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  }, true); // Use capture to override existing handler
}

function setupDragDrop() {
  const wrapper = document.getElementById('inputWrapper');

  wrapper.addEventListener('dragover', (e) => {
    e.preventDefault();
    wrapper.classList.add('drag-over');
  });

  wrapper.addEventListener('dragleave', (e) => {
    e.preventDefault();
    wrapper.classList.remove('drag-over');
  });
}

function setupPasteImage() {
  const textarea = document.getElementById('messageInput');
  textarea.addEventListener('paste', (e) => {
    const items = [...(e.clipboardData?.items || [])];
    const imageItems = items.filter((item) => item.type.startsWith('image/'));
    if (imageItems.length > 0) {
      e.preventDefault();
      const files = imageItems.map((item) => item.getAsFile()).filter(Boolean);
      handleFiles(files); // ← routes through the unified handler
    }
  });
}

function handleFiles(fileList) {
  const files = [...fileList];
  const maxSize = 20 * 1024 * 1024;

  files.forEach((file) => {
    if (file.size > maxSize) {
      showToast(`⚠️ ${file.name} is too large (max 20MB)`, 'error');
      return;
    }

    if (file.type.startsWith('image/')) {
      handleImageFile(file);
    } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
      handlePdfFile(file);
    } else {
      handleTextFile(file);
    }
  });
}

function handleImageFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const base64Full = e.target.result;
    const base64Data = base64Full.split(',')[1];
    pendingImages.push({
      base64: base64Data,
      dataUrl: base64Full,
      name: file.name || 'image.png',
      size: file.size,
      type: file.type,
    });
    renderPreviews();
    debugLog(`Image attached: ${file.name} (${formatFileSize(file.size)})`, 'info');
  };
  reader.readAsDataURL(file);
}

async function handlePdfFile(file) {
  // Show processing indicator
  const strip = document.getElementById('imagePreviewStrip');
  strip.classList.add('has-images');
  const loader = document.createElement('div');
  loader.className = 'preview-processing';
  loader.id = 'pdfLoader';
  loader.innerHTML = `<div class="spinner"></div><span>Processing ${file.name}...</span>`;
  strip.appendChild(loader);

  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const totalPages = pdf.numPages;

    debugLog(`PDF loaded: ${file.name} — ${totalPages} page(s)`, 'info');

    for (let i = 1; i <= totalPages; i++) {
      const page = await pdf.getPage(i);
      const scale = 2; // 2x resolution for readability
      const viewport = page.getViewport({ scale });

      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d');

      await page.render({ canvasContext: ctx, viewport }).promise;

      const dataUrl = canvas.toDataURL('image/png');
      const base64 = dataUrl.split(',')[1];

      pendingImages.push({
        base64,
        dataUrl,
        name: `${file.name} — p.${i}/${totalPages}`,
        size: Math.round(base64.length * 0.75),
        type: 'image/png',
        isPdfPage: true,
      });
    }

    debugLog(`PDF converted: ${totalPages} page(s) → images`, 'success');
  } catch (err) {
    showToast(`⚠️ Failed to process PDF: ${err.message}`, 'error');
    debugLog(`PDF error: ${err.message}`, 'error');
  }

  // Remove loader and re-render
  const loaderEl = document.getElementById('pdfLoader');
  if (loaderEl) loaderEl.remove();
  renderPreviews();
}

function handleTextFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const lang = getLanguage(file.name);

    pendingFiles.push({
      content,
      name: file.name,
      size: file.size,
      language: lang,
    });

    renderPreviews();
    debugLog(`File attached: ${file.name} (${lang}, ${formatFileSize(file.size)})`, 'info');
  };
  reader.onerror = () => {
    showToast(`⚠️ Failed to read ${file.name}`, 'error');
  };
  reader.readAsText(file);
}

function getLanguage(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const map = {
    js: 'javascript', ts: 'typescript', jsx: 'jsx', tsx: 'tsx',
    py: 'python', rb: 'ruby', go: 'go', rs: 'rust', zig: 'zig',
    java: 'java', c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp',
    cs: 'csharp', php: 'php', swift: 'swift', kt: 'kotlin',
    r: 'r', lua: 'lua', sh: 'bash', bash: 'bash', zsh: 'zsh',
    sql: 'sql', ex: 'elixir', exs: 'elixir', hs: 'haskell',
    ml: 'ocaml', clj: 'clojure', scala: 'scala', pl: 'perl',
    html: 'html', htm: 'html', css: 'css', xml: 'xml', svg: 'svg',
    json: 'json', yaml: 'yaml', yml: 'yaml', toml: 'toml',
    md: 'markdown', txt: 'text', csv: 'csv',
    ini: 'ini', conf: 'config', cfg: 'config', env: 'dotenv',
    dockerfile: 'dockerfile', gitignore: 'gitignore',
    log: 'log', diff: 'diff', patch: 'diff',
  };
  return map[ext] || 'text';
}

function getFileIcon(language) {
  const icons = {
    javascript: '🟨', typescript: '🔷', python: '🐍', ruby: '💎',
    go: '🔵', rust: '🦀', java: '☕', c: '⚙️', cpp: '⚙️',
    csharp: '🟪', php: '🐘', swift: '🍊', kotlin: '🟣',
    html: '🌐', css: '🎨', json: '📋', yaml: '📋',
    markdown: '📝', text: '📄', csv: '📊', sql: '🗃️',
    bash: '🖥️', zsh: '🖥️', dockerfile: '🐳',
    log: '📃', diff: '📑', config: '⚙️', dotenv: '🔒',
  };
  return icons[language] || '📄';
}

function renderPreviews() {
  const strip = document.getElementById('imagePreviewStrip');
  strip.innerHTML = '';

  const hasAnything = pendingImages.length > 0 || pendingFiles.length > 0;

  if (!hasAnything) {
    strip.classList.remove('has-images');
    return;
  }

  strip.classList.add('has-images');

  // Image/PDF thumbnails
  pendingImages.forEach((img, index) => {
    const thumb = document.createElement('div');
    thumb.className = 'preview-thumb';

    let badge = '';
    if (img.isPdfPage) {
      badge = '<div class="pdf-badge">PDF</div>';
    }

    thumb.innerHTML = `
      ${badge}
      <img src="${img.dataUrl}" alt="${img.name}" />
      <button class="remove-thumb" onclick="removeImage(${index})" title="Remove">✕</button>
      <div class="thumb-size">${formatFileSize(img.size)}</div>
    `;
    strip.appendChild(thumb);
  });

  // Text/code file cards
  pendingFiles.forEach((file, index) => {
    const card = document.createElement('div');
    card.className = 'preview-file';

    const icon = getFileIcon(file.language);

    card.innerHTML = `
      <div class="file-icon">${icon}</div>
      <div class="file-info">
        <span class="file-name">${escapeHtml(file.name)}</span>
        <span class="file-meta">${file.language} · ${formatFileSize(file.size)}</span>
      </div>
      <button class="remove-file" onclick="removeFile(${index})" title="Remove">✕</button>
    `;
    strip.appendChild(card);
  });
}

function removeImage(index) {
  const removed = pendingImages.splice(index, 1)[0];
  renderPreviews();
  debugLog(`Image removed: ${removed.name}`, 'info');
}

function removeFile(index) {
  const removed = pendingFiles.splice(index, 1)[0];
  renderPreviews();
  debugLog(`File removed: ${removed.name}`, 'info');
}

function clearPendingImages() {
  pendingImages = [];
  pendingFiles = [];
  renderPreviews();
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ===================== IMAGE VIEWER (fullscreen) =====================
function createImageViewer() {
  const overlay = document.createElement('div');
  overlay.className = 'image-viewer-overlay';
  overlay.id = 'imageViewer';
  overlay.innerHTML = '<img src="" alt="Full size" />';
  overlay.addEventListener('click', () => overlay.classList.remove('active'));
  document.body.appendChild(overlay);
}

function viewImage(src) {
  const viewer = document.getElementById('imageViewer');
  viewer.querySelector('img').src = src;
  viewer.classList.add('active');
}

// ===================== SEND MESSAGE =====================
async function sendMessage() {
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  const hasImages = pendingImages.length > 0;
  const hasFiles = pendingFiles.length > 0;

  if ((!text && !hasImages && !hasFiles) || state.isLoading) return;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('charCount').textContent = '0 chars';

  const sentImages = [...pendingImages];
  const sentFiles = [...pendingFiles];
  clearPendingImages();

  const messageText = text || (hasImages ? '(image attached)' : '(file attached)');
  renderMessage('user', messageText, null, true, sentImages, sentFiles);
  scrollToBottom();

  state.isLoading = true;
  document.getElementById('sendBtn').disabled = true;
  updateStatus('waiting');
  showTypingIndicator();

  const payload = {
    chatInput: messageText,
    chatHistory: state.chatHistory.slice(-60),
    sessionId: getSessionId(),
  };

  if (sentImages.length > 0) {
    payload.images = sentImages.map((img) => ({
      base64: img.base64,
      name: img.name,
      type: img.type,
    }));
    debugLog(`Sending ${sentImages.length} image(s)`, 'info');
  }

  if (sentFiles.length > 0) {
    payload.files = sentFiles.map((f) => ({
      content: f.content,
      name: f.name,
      language: f.language,
    }));
    debugLog(`Sending ${sentFiles.length} file(s): ${sentFiles.map(f => f.name).join(', ')}`, 'info');
  }

  debugLog(`Sending to: ${WEBHOOK_URL}`, 'info');

  try {
    const headers = { 'Content-Type': 'application/json' };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const response = await fetch(WEBHOOK_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    debugLog(`Response: ${response.status} ${response.statusText}`, response.ok ? 'success' : 'error');
    removeTypingIndicator();

    if (!response.ok) {
      let errorDetail = '';
      try { errorDetail = (await response.text()).substring(0, 300); } catch {}
      renderError(`HTTP ${response.status}: ${response.statusText}${errorDetail ? '\n\n' + errorDetail : ''}`);
      updateStatus('error');
      return;
    }

    // --- SSE streaming ---
    let accText = '';
    let accThinking = '';
    const msgEl = createStreamingMessage();

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop(); // keep incomplete last line
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') break;
          try {
            const chunk = JSON.parse(raw);
            if (chunk.type === 'text') {
              accText += chunk.text;
              updateStreamingMessage(msgEl, accText, accThinking);
            } else if (chunk.type === 'thinking') {
              accThinking += chunk.text;
              updateStreamingMessage(msgEl, accText, accThinking);
            } else if (chunk.type === 'tool_call') {
              appendToolCall(msgEl, chunk.tool, chunk.args);
            } else if (chunk.type === 'tool_result') {
              appendToolResult(msgEl, chunk.tool, chunk.output, chunk.image || null, chunk.mime_type);
            } else if (chunk.type === 'approval_request') {
              appendApprovalRequest(msgEl, chunk.request_id, chunk.tool, chunk.args);
            } else if (chunk.type === 'tool_denied') {
              const area = msgEl.querySelector('.tool-activity');
              if (area) {
                const b = document.createElement('div');
                b.className = 'tool-result-block denied';
                b.textContent = `❌ ${chunk.tool} denied`;
                area.appendChild(b);
              }
            } else if (chunk.type === 'error') {
              finalizeStreamingMessage(msgEl, accText || chunk.text, accThinking, false);
              renderError(chunk.text);
              updateStatus('error');
              return;
            }
          } catch {}
        }
        scrollToBottom();
      }
    } finally {
      reader.releaseLock();
    }

    const saveToHistory = accText.trim().length > 0;
    finalizeStreamingMessage(msgEl, accText || '(empty response)', accThinking, saveToHistory);
    updateStatus('connected');
  } catch (error) {
    removeTypingIndicator();
    if (error.name === 'AbortError') {
      renderError('Request timed out (2 min).');
    } else if (error.message.includes('Failed to fetch')) {
      renderError('Cannot connect to n8n.\n\n• Is n8n running?\n• CORS: N8N_CORS_ORIGIN=* n8n start');
    } else {
      renderError(error.message);
    }
    updateStatus('error');
  } finally {
    state.isLoading = false;
    document.getElementById('sendBtn').disabled = false;
    scrollToBottom();
  }
}

function extractResponse(data, field) {
  if (Array.isArray(data)) data = data[0];
  if (!data) return null;

  // Direct field
  if (data[field] !== undefined) return String(data[field]);

  // Nested path
  const parts = field.split('.');
  let current = data;
  for (const part of parts) {
    if (current && current[part] !== undefined) current = current[part];
    else { current = undefined; break; }
  }
  if (current !== undefined) return String(current);

  // Fallbacks
  const fallbacks = [
    'output', 'response', 'text', 'message', 'content',
    'result', 'answer', 'reply', 'generated_text', 'completion',
  ];
  for (const fb of fallbacks) {
    if (data[fb] !== undefined) return String(data[fb]);
  }

  if (typeof data === 'string') return data;
  return null;  // null = genuinely not found
}

// ===================== UTILITIES =====================
function getSplitterBase() {
  return `http://${window.location.hostname}:9200`;
}

function getSessionId() {
  return state.currentSession;
}

function renderSessionSidebar() {
  const sidebar = document.getElementById('sessionSidebar');
  if (!sidebar) return;
  sidebar.innerHTML = SESSIONS.map(s => `
    <button class="session-btn${s.id === state.currentSession ? ' active' : ''}"
            onclick="switchSession('${s.id}')"
            title="${s.label}">
      <span class="session-icon">${SESSION_ICONS[s.id] || ''}</span>
      <span class="session-label">${s.label}</span>
    </button>
  `).join('');
}

async function switchSession(id) {
  if (id === state.currentSession || state.isLoading) return;

  // Stop polling for old session
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }

  state.currentSession = id;
  localStorage.setItem('accel_active_session', id);

  // Clear display
  state.chatHistory = [];
  const container = document.getElementById('chatContainer');
  container.innerHTML = `
    <div class="welcome-state" id="welcomeMessage">
      <div class="welcome-blob-icon"><div class="mini-blob"></div></div>
      <h2>${SESSIONS.find(s => s.id === id)?.label} session</h2>
      <p>Loading history...</p>
    </div>`;

  renderSessionSidebar();
  await loadSessionHistory();
}

async function clearChat() {
  const sid = state.currentSession;
  state.chatHistory = [];
  localStorage.removeItem(`accel_chat_${sid}`);
  try {
    await fetch(`${getSplitterBase()}/session?session_id=${sid}`, { method: 'DELETE', signal: AbortSignal.timeout(5000) });
  } catch (_) {}
  document.getElementById('chatContainer').innerHTML = `
    <div class="welcome-state" id="welcomeMessage">
      <div class="welcome-blob-icon"><div class="mini-blob"></div></div>
      <h2>Chat Cleared</h2>
      <p>Start a new conversation with your local LLM.</p>
      <div class="quick-actions">
        <button class="quick-action glass-panel" onclick="sendQuickAction('Hello!')">👋 Say Hello</button>
        <button class="quick-action glass-panel" onclick="sendQuickAction('Write a haiku about coding.')">📝 Write a Haiku</button>
      </div>
    </div>
  `;
  showToast('🗑️ Chat cleared!', 'success');
}

function sendQuickAction(text) {
  document.getElementById('messageInput').value = text;
  sendMessage();
}

