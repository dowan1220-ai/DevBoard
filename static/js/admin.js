'use strict';

// ── 탭 전환 ──
document.querySelectorAll('.sidebar-item').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.sidebar-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.getElementById(`tab-${tab}`).classList.add('active');
        if (tab === 'users') loadUsers();
    });
});

// ── 유틸 ──
function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
function timeStr(ts) {
    if (!ts) return '-';
    const d = new Date(ts * 1000);
    return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function showError(id, msg) {
    const el = document.getElementById(id);
    el.textContent = msg;
    el.classList.remove('hidden');
}
function hideError(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

// ════════════════════════════════
//  공지 관리
// ════════════════════════════════
let editingNoticeId = null;
let noticesCache = {};   // id → notice 객체 캐시

async function loadNotices() {
    const list = document.getElementById('noticeList');
    list.innerHTML = '<div class="admin-loading">불러오는 중...</div>';
    try {
        const res  = await fetch('/api/notices');
        const data = await res.json();
        if (!data.notices.length) {
            list.innerHTML = '<div class="notice-empty-admin">📭 아직 공지사항이 없습니다.<br>새 공지를 작성해보세요!</div>';
            return;
        }
        noticesCache = {};
        list.innerHTML = '';
        data.notices.forEach(n => {
            noticesCache[n.id] = n;   // 캐시에 저장
            const item = document.createElement('div');
            item.className = 'notice-item';
            item.innerHTML = `
                <div class="notice-pin-icon ${n.is_pinned ? 'pinned' : ''}">📌</div>
                <div class="notice-item-body">
                    <div class="notice-item-title">
                        ${n.is_pinned ? '<span class="notice-pin-badge">고정</span>' : ''}
                        ${escHtml(n.title)}
                    </div>
                    <div class="notice-item-content">${escHtml(n.content)}</div>
                    <div class="notice-item-meta">${escHtml(n.author_nickname)} · ${timeStr(n.created_at)}${n.updated_at > n.created_at + 1 ? ' · (수정됨)' : ''}</div>
                </div>
                <div class="notice-item-actions">
                    <button class="btn-neutral" data-notice-id="${n.id}">✏️ 수정</button>
                    <button class="btn-danger"  data-delete-id="${n.id}">🗑 삭제</button>
                </div>
            `;
            // 인라인 onclick 대신 addEventListener로 처리 (특수문자 안전)
            item.querySelector('[data-notice-id]').addEventListener('click', () => openEditNotice(n.id));
            item.querySelector('[data-delete-id]').addEventListener('click', () => deleteNotice(n.id));
            list.appendChild(item);
        });
    } catch {
        list.innerHTML = '<div class="admin-loading">로딩 실패</div>';
    }
}

function openNewNotice() {
    editingNoticeId = null;
    document.getElementById('noticeModalTitle').textContent = '새 공지 작성';
    document.getElementById('noticeSubmitBtn').textContent = '등록하기';
    document.getElementById('noticeTitle').value = '';
    document.getElementById('noticeContent').value = '';
    document.getElementById('noticePinned').checked = false;
    hideError('noticeFormError');
    document.getElementById('noticeModalOverlay').classList.remove('hidden');
}

function openEditNotice(id) {
    const n = noticesCache[id];
    if (!n) return;
    editingNoticeId = id;
    document.getElementById('noticeModalTitle').textContent = '공지 수정';
    document.getElementById('noticeSubmitBtn').textContent = '저장하기';
    document.getElementById('noticeTitle').value = n.title;
    document.getElementById('noticeContent').value = n.content;
    document.getElementById('noticePinned').checked = n.is_pinned;
    hideError('noticeFormError');
    document.getElementById('noticeModalOverlay').classList.remove('hidden');
}

function closeNoticeModal() {
    document.getElementById('noticeModalOverlay').classList.add('hidden');
    editingNoticeId = null;
}

document.getElementById('newNoticeBtn').addEventListener('click', openNewNotice);
document.getElementById('noticeModalClose').addEventListener('click', closeNoticeModal);
document.getElementById('noticeModalCancelBtn').addEventListener('click', closeNoticeModal);

document.getElementById('noticeForm').addEventListener('submit', async e => {
    e.preventDefault();
    const title   = document.getElementById('noticeTitle').value.trim();
    const content = document.getElementById('noticeContent').value.trim();
    const pinned  = document.getElementById('noticePinned').checked;
    if (!title || !content) {
        showError('noticeFormError', '제목과 내용을 입력해주세요.');
        return;
    }
    const fd = new FormData();
    fd.append('title', title);
    fd.append('content', content);
    fd.append('is_pinned', pinned ? 'true' : 'false');
    const url    = editingNoticeId ? `/api/notices/${editingNoticeId}` : '/api/notices';
    const method = editingNoticeId ? 'PUT' : 'POST';
    try {
        const res  = await fetch(url, { method, body: fd });
        const data = await res.json();
        if (!res.ok) { showError('noticeFormError', data.error || '오류가 발생했습니다.'); return; }
        closeNoticeModal();
        loadNotices();
    } catch {
        showError('noticeFormError', '서버 오류가 발생했습니다.');
    }
});

async function deleteNotice(id) {
    if (!confirm('이 공지를 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`/api/notices/${id}`, { method: 'DELETE' });
        if (res.ok) loadNotices();
    } catch {}
}

// ════════════════════════════════
//  회원 관리
// ════════════════════════════════
let allUsers = [];

async function loadUsers() {
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '<tr><td colspan="7" class="admin-loading">불러오는 중...</td></tr>';
    try {
        const res  = await fetch('/api/admin/users');
        const data = await res.json();
        allUsers = data.users || [];
        document.getElementById('userCount').textContent = allUsers.length;
        renderUsers(allUsers);
    } catch {
        tbody.innerHTML = '<tr><td colspan="7" class="admin-loading">로딩 실패</td></tr>';
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '';
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="admin-loading">해당 회원이 없습니다</td></tr>';
        return;
    }
    users.forEach(u => {
        const tr = document.createElement('tr');
        const lockLabel = u.is_locked
            ? `<span class="status-badge locked">🔒 잠금</span>`
            : `<span class="status-badge normal">✅ 정상</span>`;
        const adminLabel = u.is_admin
            ? `<span class="admin-badge-cell is-admin">🛡️ 관리자</span>`
            : `<span class="admin-badge-cell not-admin">일반</span>`;

        const isSelf = u.username === CURRENT_ADMIN_ID;
        const actionHtml = isSelf
            ? `<span class="self-label">본인 계정</span>`
            : `<div class="action-btns">
                    ${u.is_locked
                        ? `<button class="btn-success" onclick="unlockUser('${escAttr(u.username)}')">🔓 잠금해제</button>`
                        : `<button class="btn-warn" onclick="openLockModal('${escAttr(u.username)}', '${escAttr(u.nickname)}')">🔒 잠금</button>`
                    }
                    <button class="btn-neutral" onclick="toggleAdmin('${escAttr(u.username)}')">${u.is_admin ? '관리자 해제' : '관리자 지정'}</button>
                    <button class="btn-danger" onclick="deleteUser('${escAttr(u.username)}', '${escAttr(u.nickname)}')">🗑 삭제</button>
               </div>`;

        tr.innerHTML = `
            <td><span class="user-nickname">${escHtml(u.nickname)}${isSelf ? ' <span class="self-tag">나</span>' : ''}</span></td>
            <td><span class="user-id-cell">${escHtml(u.username)}</span></td>
            <td><span class="user-count-badge">${u.profile_count}</span></td>
            <td><span class="user-count-badge">${u.team_count}</span></td>
            <td>${lockLabel}</td>
            <td>${adminLabel}</td>
            <td>${actionHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

// 검색
document.getElementById('userSearchInput').addEventListener('input', e => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) { renderUsers(allUsers); return; }
    renderUsers(allUsers.filter(u =>
        u.nickname.toLowerCase().includes(q) || u.username.toLowerCase().includes(q)
    ));
});

// 잠금 모달
let lockTargetId = null;
function openLockModal(uid, nickname) {
    lockTargetId = uid;
    document.getElementById('lockTargetName').textContent = `"${nickname}" 계정 잠금 기간을 선택하세요`;
    document.getElementById('lockModalOverlay').classList.remove('hidden');
}
document.getElementById('lockModalClose').addEventListener('click', () => {
    document.getElementById('lockModalOverlay').classList.add('hidden');
    lockTargetId = null;
});
document.querySelectorAll('.lock-opt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!lockTargetId) return;
        lockUser(lockTargetId, btn.dataset.min);
        document.getElementById('lockModalOverlay').classList.add('hidden');
        lockTargetId = null;
    });
});

async function lockUser(uid, minutes) {
    const fd = new FormData();
    fd.append('minutes', minutes);
    try {
        const res = await fetch(`/api/admin/users/${encodeURIComponent(uid)}/lock`, { method: 'POST', body: fd });
        if (res.ok) loadUsers();
    } catch {}
}
async function unlockUser(uid) {
    try {
        const res = await fetch(`/api/admin/users/${encodeURIComponent(uid)}/unlock`, { method: 'POST' });
        if (res.ok) loadUsers();
    } catch {}
}
async function toggleAdmin(uid) {
    if (!confirm('관리자 권한을 변경하시겠습니까?')) return;
    try {
        const res = await fetch(`/api/admin/users/${encodeURIComponent(uid)}/toggle-admin`, { method: 'POST' });
        if (res.ok) loadUsers();
    } catch {}
}
async function deleteUser(uid, nickname) {
    if (!confirm(`"${nickname}" 계정을 삭제하시겠습니까?\n게시글, DM, 알림도 모두 삭제됩니다.`)) return;
    try {
        const res = await fetch(`/api/admin/users/${encodeURIComponent(uid)}`, { method: 'DELETE' });
        if (res.ok) loadUsers();
    } catch {}
}

// ── 초기 로드 ──
loadNotices();
