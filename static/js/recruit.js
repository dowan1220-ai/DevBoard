const LANGS = [
    'Python','JavaScript','TypeScript','Java','C','C++','C#',
    'Go','Rust','Swift','Kotlin','PHP','Ruby','HTML/CSS','SQL','R','Dart','Scala'
];

let pastLangs = new Set();
let currLangs = new Set();
let profileImageBase64 = '';
let currentTab = 'recruit';
let selectedTeamField = '';
let teamMaxMembers = 4;
let editingProfileId = null;

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

const DEV_FIELD_STYLE = {
    '풀스택':    { bg:'rgba(91,94,247,0.12)',  color:'#5b5ef7', emoji:'🔧' },
    '백엔드':    { bg:'rgba(39,174,96,0.13)',  color:'#27ae60', emoji:'⚙️' },
    '프론트엔드': { bg:'rgba(224,85,122,0.13)', color:'#e0557a', emoji:'🎨' },
};

// ─── 탭 전환 ───
const TAB_META = {
    recruit: { title:'구인 게시판', h2:'개발자 찾기', sub:'함께 공부할 개발자를 찾아보세요!' },
    team:    { title:'팀 게시판',   h2:'팀 목록',     sub:'팀을 만들거나 참여해보세요!' },
};

document.querySelectorAll('.board-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.board-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTab = btn.dataset.type;
        const m = TAB_META[currentTab];
        document.getElementById('pageTitle').textContent    = m.title;
        document.getElementById('sectionTitle').textContent = m.h2;
        document.getElementById('sectionSub').textContent   = m.sub;
        loadProfiles();
    });
});

// ─── 언어 프리셋 ───
function initPresets() {
    ['past','curr'].forEach(type => {
        const el = document.getElementById(`${type}-presets`);
        LANGS.forEach(lang => {
            const btn = document.createElement('button');
            btn.type = 'button'; btn.className = 'preset-btn';
            btn.textContent = lang; btn.dataset.lang = lang;
            btn.addEventListener('click', () => toggleLang(type, lang));
            el.appendChild(btn);
        });
    });
}
function toggleLang(type, lang) {
    const s = type==='past' ? pastLangs : currLangs;
    s.has(lang) ? s.delete(lang) : s.add(lang);
    renderTags(type); updatePresetButtons(type);
}
function renderTags(type) {
    const s = type==='past' ? pastLangs : currLangs;
    const el = document.getElementById(`${type}-tags`);
    el.innerHTML = '';
    s.forEach(lang => {
        const tag = document.createElement('span');
        tag.className = `lang-tag tag-${type}`;
        tag.innerHTML = `${escapeHtml(lang)} <button type="button" class="tag-remove">×</button>`;
        tag.querySelector('.tag-remove').addEventListener('click', () => {
            s.delete(lang); renderTags(type); updatePresetButtons(type);
        });
        el.appendChild(tag);
    });
}
function updatePresetButtons(type) {
    const s = type==='past' ? pastLangs : currLangs;
    document.getElementById(`${type}-presets`).querySelectorAll('.preset-btn').forEach(b => {
        b.classList.toggle('active', s.has(b.dataset.lang));
    });
}
function addCustomLang(type, lang) {
    lang = lang.trim(); if (!lang) return;
    const s = type==='past' ? pastLangs : currLangs;
    s.add(lang); renderTags(type); updatePresetButtons(type);
}


// ─── 팀 최대인원 카운터 ───
document.getElementById('countMinus').addEventListener('click', () => {
    if (teamMaxMembers > 2) teamMaxMembers--;
    document.getElementById('countDisplay').textContent = teamMaxMembers;
});
document.getElementById('countPlus').addEventListener('click', () => {
    if (teamMaxMembers < 10) teamMaxMembers++;
    document.getElementById('countDisplay').textContent = teamMaxMembers;
});

// ─── 이미지 ───
document.getElementById('changePhotoBtn').addEventListener('click', () => document.getElementById('imageInput').click());
document.getElementById('imagePreviewCircle').addEventListener('click', () => document.getElementById('imageInput').click());
document.getElementById('imageInput').addEventListener('change', e => {
    const file = e.target.files[0]; if (!file) return;
    compressImage(file, 300, 0.8).then(url => {
        profileImageBase64 = url;
        document.getElementById('imagePreviewCircle').innerHTML = `<img src="${url}" alt="프로필">`;
    });
});
function compressImage(file, maxSize, quality) {
    return new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = e => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                let w = img.width, h = img.height;
                if (w > maxSize || h > maxSize) {
                    if (w > h) { h = Math.round(h*maxSize/w); w = maxSize; }
                    else { w = Math.round(w*maxSize/h); h = maxSize; }
                }
                canvas.width = w; canvas.height = h;
                canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                resolve(canvas.toDataURL('image/jpeg', quality));
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

// ─── 언어 입력 ───
document.getElementById('past-lang-input').addEventListener('keydown', e => {
    if (e.key==='Enter') { e.preventDefault(); addCustomLang('past', e.target.value); e.target.value=''; }
});
document.getElementById('curr-lang-input').addEventListener('keydown', e => {
    if (e.key==='Enter') { e.preventDefault(); addCustomLang('curr', e.target.value); e.target.value=''; }
});

// ─── 구인/구직 모달 ───
function openProfileModal() {
    editingProfileId = null;
    document.getElementById('modalTitle').textContent = '구인 등록';
    document.querySelector('#profileForm .btn-submit').textContent = '등록하기';
    document.getElementById('profileForm').reset();
    document.getElementById('inp-bio').value = '';
    document.getElementById('imagePreviewCircle').innerHTML = '<span class="photo-icon">📷</span>';
    profileImageBase64 = ''; pastLangs.clear(); currLangs.clear();
    renderTags('past'); renderTags('curr');
    updatePresetButtons('past'); updatePresetButtons('curr');
    document.getElementById('formError').textContent = '';
    document.getElementById('modalOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function openEditModal(profile) {
    editingProfileId = profile.id;
    document.getElementById('modalTitle').textContent = '구인 수정';
    document.querySelector('#profileForm .btn-submit').textContent = '수정하기';
    document.getElementById('profileForm').reset();
    document.getElementById('inp-name').value = profile.name || '';
    document.getElementById('inp-class').value = profile.class_number || '';
    document.getElementById('inp-major').value = profile.major || '';
    document.getElementById('inp-bio').value = profile.bio || '';
    // 이미지
    if (profile.profile_image) {
        profileImageBase64 = profile.profile_image;
        document.getElementById('imagePreviewCircle').innerHTML = `<img src="${profile.profile_image}" alt="프로필">`;
    } else {
        profileImageBase64 = '';
        document.getElementById('imagePreviewCircle').innerHTML = '<span class="photo-icon">📷</span>';
    }
    // 언어
    pastLangs.clear(); currLangs.clear();
    (profile.past_languages || []).forEach(l => pastLangs.add(l));
    (profile.current_languages || []).forEach(l => currLangs.add(l));
    renderTags('past'); renderTags('curr');
    updatePresetButtons('past'); updatePresetButtons('curr');
    document.getElementById('formError').textContent = '';
    document.getElementById('modalOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeProfileModal() {
    document.getElementById('modalOverlay').classList.add('hidden');
    document.body.style.overflow = '';
    editingProfileId = null;
}
document.getElementById('modalClose').addEventListener('click', closeProfileModal);
document.getElementById('modalOverlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modalOverlay')) closeProfileModal();
});

// ─── 팀 생성 모달 ───
function openTeamModal() {
    document.getElementById('teamForm').reset();
    selectedTeamField = '';
    teamMaxMembers = 4;
    document.getElementById('countDisplay').textContent = 4;
    document.getElementById('teamFormError').textContent = '';
    document.getElementById('teamModalOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}
function closeTeamModal() {
    document.getElementById('teamModalOverlay').classList.add('hidden');
    document.body.style.overflow = '';
}
document.getElementById('teamModalClose').addEventListener('click', closeTeamModal);
document.getElementById('teamModalOverlay').addEventListener('click', e => {
    if (e.target === document.getElementById('teamModalOverlay')) closeTeamModal();
});

// ─── 팀 관리 모달 ───
function openManageModal(team) {
    document.getElementById('manageModalTitle').textContent = `${team.name} 관리`;
    const body = document.getElementById('manageModalBody');
    if (team.pending_list.length === 0) {
        body.innerHTML = '<p style="text-align:center; color:#aaa; padding:32px 0;">참여 신청이 없습니다.</p>';
    } else {
        body.innerHTML = `
            <p style="font-size:13px; color:#888; margin-bottom:16px;">참여 신청 ${team.pending_list.length}건</p>
            <div id="pendingList"></div>
        `;
        const list = document.getElementById('pendingList');
        team.pending_list.forEach(m => {
            const row = document.createElement('div');
            row.className = 'pending-row';
            row.dataset.memberId = m.id;
            row.innerHTML = `
                <span class="pending-name">${escapeHtml(m.display_name)}</span>
                <div class="pending-actions">
                    <button class="pending-accept" data-id="${m.id}" data-team="${team.id}">수락</button>
                    <button class="pending-reject" data-id="${m.id}" data-team="${team.id}">거절</button>
                </div>
            `;
            list.appendChild(row);
        });
        list.querySelectorAll('.pending-accept').forEach(btn => {
            btn.addEventListener('click', () => respondTeam(btn.dataset.team, btn.dataset.id, 'accept', btn));
        });
        list.querySelectorAll('.pending-reject').forEach(btn => {
            btn.addEventListener('click', () => respondTeam(btn.dataset.team, btn.dataset.id, 'reject', btn));
        });
    }
    document.getElementById('manageModalOverlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}
function closeManageModal() {
    document.getElementById('manageModalOverlay').classList.add('hidden');
    document.body.style.overflow = '';
}
document.getElementById('manageModalClose').addEventListener('click', closeManageModal);
document.getElementById('manageModalOverlay').addEventListener('click', e => {
    if (e.target === document.getElementById('manageModalOverlay')) closeManageModal();
});

async function respondTeam(teamId, memberId, action, btn) {
    const fd = new FormData();
    fd.append('member_id', memberId);
    fd.append('action', action);
    const res = await fetch(`/api/teams/${teamId}/respond`, { method:'POST', body:fd });
    const data = await res.json();
    if (data.success) {
        const row = document.querySelector(`.pending-row[data-member-id="${memberId}"]`);
        if (row) {
            row.style.opacity = '0.4';
            row.querySelector('.pending-actions').innerHTML =
                `<span style="font-size:12px; color:${action==='accept'?'#27ae60':'#e05555'}">${action==='accept'?'수락됨':'거절됨'}</span>`;
        }
        loadProfiles();
    } else {
        alert(data.error || '오류 발생');
    }
}

// ─── 구인/구직 폼 제출 ───
document.getElementById('profileForm').addEventListener('submit', async e => {
    e.preventDefault();
    const name = document.getElementById('inp-name').value.trim();
    const classNum = document.getElementById('inp-class').value.trim();
    const major = document.getElementById('inp-major').value.trim();
    const bio = document.getElementById('inp-bio').value.trim();
    const errorEl = document.getElementById('formError');
    if (!name || !classNum || !major) { errorEl.textContent = '이름, 반/번호, 전공은 필수입니다.'; return; }
    errorEl.textContent = '';
    const fd = new FormData();
    fd.append('name', name); fd.append('class_number', classNum); fd.append('major', major);
    fd.append('bio', bio);
    fd.append('past_languages', [...pastLangs].join(','));
    fd.append('current_languages', [...currLangs].join(','));
    fd.append('post_type', 'recruit');
    if (profileImageBase64) fd.append('profile_image', profileImageBase64);
    const btn = document.querySelector('#profileForm .btn-submit');
    const isEditing = editingProfileId !== null;
    btn.disabled = true; btn.textContent = isEditing ? '수정 중...' : '등록 중...';
    try {
        const url = isEditing ? `/api/profiles/${editingProfileId}` : '/api/profiles';
        const method = isEditing ? 'PUT' : 'POST';
        const res = await fetch(url, {method, body:fd});
        const data = await res.json();
        if (data.success) { closeProfileModal(); loadProfiles(); }
        else errorEl.textContent = data.error || '오류가 발생했습니다.';
    } catch { errorEl.textContent = '오류가 발생했습니다.'; }
    finally { btn.disabled=false; btn.textContent = isEditing ? '수정하기' : '등록하기'; }
});

// ─── 팀 생성 폼 제출 ───
document.getElementById('teamForm').addEventListener('submit', async e => {
    e.preventDefault();
    const name = document.getElementById('team-name').value.trim();
    const desc = document.getElementById('team-desc').value.trim();
    const errorEl = document.getElementById('teamFormError');
    if (!name) { errorEl.textContent = '팀 이름을 입력해주세요.'; return; }
    errorEl.textContent = '';
    const fd = new FormData();
    fd.append('name', name); fd.append('description', desc);
    fd.append('dev_field', ''); fd.append('max_members', teamMaxMembers);
    const btn = document.querySelector('#teamForm .btn-submit'); btn.disabled=true; btn.textContent='생성 중...';
    try {
        const res = await fetch('/api/teams', {method:'POST', body:fd});
        const data = await res.json();
        if (data.success) { closeTeamModal(); loadProfiles(); }
        else errorEl.textContent = data.error || '오류가 발생했습니다.';
    } catch { errorEl.textContent = '오류가 발생했습니다.'; }
    finally { btn.disabled=false; btn.textContent='팀 만들기'; }
});

// ─── 카드 생성 ───
const AVATAR_COLORS = ['#667eea','#f093fb','#4facfe','#43e97b','#fa709a','#a18cd1','#fda085','#56ccf2'];
function getAvatarColor(name) {
    let h=0; for (const c of name) h += c.charCodeAt(0);
    return AVATAR_COLORS[h % AVATAR_COLORS.length];
}
function avatarCircle(name, image, size=36) {
    if (image) return `<img class="member-avatar-img" src="${image}" style="width:${size}px;height:${size}px;border-radius:50%;object-fit:cover;" alt="">`;
    const color = getAvatarColor(name);
    return `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:${Math.round(size*0.4)}px;flex-shrink:0;">${escapeHtml(name.charAt(0))}</div>`;
}

function createPlusCard() {
    const card = document.createElement('div');
    card.className = 'card card-plus';
    if (currentTab === 'team') {
        card.innerHTML = `<div class="plus-icon">🤝</div><div class="plus-text">팀 만들기</div><div class="plus-sub">새 팀을 만들어보세요!</div>`;
        card.addEventListener('click', openTeamModal);
    } else {
        card.innerHTML = `<div class="plus-icon">+</div><div class="plus-text">구인 등록하기</div><div class="plus-sub">내 정보를 등록해보세요!</div>`;
        card.addEventListener('click', openProfileModal);
    }
    return card;
}

function createProfileCard(profile) {
    const card = document.createElement('div');
    card.className = `card card-profile${profile.is_mine ? ' card-mine' : ''}`;

    let avatarHtml;
    if (profile.profile_image) {
        avatarHtml = `<img class="avatar-img" src="${profile.profile_image}" alt="">`;
    } else {
        const color = getAvatarColor(profile.name);
        avatarHtml = `<div class="avatar-default" style="background:${color};">${escapeHtml(profile.name.charAt(0))}</div>`;
    }

    const pastHtml = profile.past_languages.length
        ? profile.past_languages.map(l => `<span class="chip chip-past">${escapeHtml(l)}</span>`).join('')
        : '<span class="no-lang">없음</span>';
    const currHtml = profile.current_languages.length
        ? profile.current_languages.map(l => `<span class="chip chip-curr">${escapeHtml(l)}</span>`).join('')
        : '<span class="no-lang">없음</span>';

    const deleteBtnHtml = profile.is_mine ? `<button class="card-delete-btn" title="삭제">✕</button>` : '';
    const editBtnHtml   = profile.is_mine ? `<button class="card-edit-btn" title="수정">✏️</button>` : '';

    const bioHtml = profile.bio
        ? `<div class="profile-bio">${escapeHtml(profile.bio)}</div>`
        : '';

    let recruitBtnHtml = '';
    if (!profile.is_mine) {
        if (profile.interest_sent) {
            recruitBtnHtml = `<button class="recruit-interest-btn sent" disabled>✅ 구인 신청 완료</button>`;
        } else {
            recruitBtnHtml = `<button class="recruit-interest-btn" data-id="${profile.id}">👋 구인하기</button>`;
        }
    }

    card.innerHTML = `
        ${deleteBtnHtml}
        ${editBtnHtml}
        ${profile.is_mine ? `<div class="mine-badge">내 구인</div>` : ''}
        <div class="avatar-wrap">${avatarHtml}</div>
        <div class="profile-name">${escapeHtml(profile.name)}</div>
        <div class="profile-class">${escapeHtml(profile.class_number)}</div>
        <div class="profile-major-badge">${escapeHtml(profile.major)}</div>
        ${bioHtml}
        <div class="card-divider"></div>
        <div class="profile-langs-section"><div class="langs-label">공부했던 언어</div><div class="langs-list">${pastHtml}</div></div>
        <div class="profile-langs-section"><div class="langs-label">공부중인 언어</div><div class="langs-list">${currHtml}</div></div>
        ${recruitBtnHtml}
    `;
    if (profile.is_mine) {
        card.querySelector('.card-delete-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            if (!confirm('이 게시물을 삭제할까요?')) return;
            const res = await fetch(`/api/profiles/${profile.id}`, {method:'DELETE'});
            const data = await res.json();
            if (data.success) loadProfiles(); else alert(data.error || '삭제 실패');
        });
        card.querySelector('.card-edit-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            openEditModal(profile);
        });
    }
    // 다른 사람 프로필 클릭 → DM 열기 + 조회 알림
    if (!profile.is_mine) {
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
            if (e.target.closest('button')) return;
            openDmFromProfile(profile);
        });
    }

    const interestBtn = card.querySelector('.recruit-interest-btn:not(.sent)');
    if (interestBtn) {
        interestBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            interestBtn.disabled = true;
            interestBtn.textContent = '신청 중...';
            const res = await fetch(`/api/profiles/${profile.id}/interest`, {method:'POST'});
            const data = await res.json();
            if (data.success) {
                interestBtn.textContent = '✅ 구인 신청 완료';
                interestBtn.classList.add('sent');
            } else {
                alert(data.error || '오류 발생');
                interestBtn.disabled = false;
                interestBtn.textContent = '👋 구인하기';
            }
        });
    }
    return card;
}

function createTeamCard(team) {
    const card = document.createElement('div');
    card.className = `card card-team${team.is_mine ? ' card-mine' : ''}`;
    const s = DEV_FIELD_STYLE[team.dev_field] || {bg:'rgba(0,0,0,0.08)',color:'#555',emoji:'💻'};
    const memberCount = team.members.length;
    const isFull = memberCount >= team.max_members;

    // 멤버 아바타
    const memberAvatars = team.members.map(m => `
        <div class="member-slot" title="${escapeHtml(m.display_name)}">
            ${avatarCircle(m.display_name, null, 34)}
            <div class="member-name-tip">${escapeHtml(m.display_name)}</div>
        </div>`).join('');

    // 빈 자리
    const emptySlots = Array(Math.max(0, team.max_members - memberCount))
        .fill('<div class="member-slot-empty"></div>').join('');

    // 버튼 영역
    let actionHtml = '';
    if (team.is_mine) {
        actionHtml = `
            <div class="team-actions">
                <button class="team-manage-btn" data-id="${team.id}">
                    ⚙️ 신청 관리 ${team.pending_count > 0 ? `<span class="pending-badge">${team.pending_count}</span>` : ''}
                </button>
                <button class="team-delete-btn" data-id="${team.id}">삭제</button>
            </div>`;
    } else if (team.my_status === 'accepted') {
        actionHtml = `<div class="team-joined-badge">✅ 참여 중</div>`;
    } else if (team.my_status === 'pending') {
        actionHtml = `<div class="team-pending-badge">⏳ 신청 중</div>`;
    } else if (team.my_status === 'rejected') {
        actionHtml = `<div class="team-rejected-badge">거절됨</div>`;
    } else if (!isFull) {
        actionHtml = `<button class="team-join-btn" data-id="${team.id}">참여 신청</button>`;
    } else {
        actionHtml = `<div class="team-full-badge">정원 마감</div>`;
    }

    card.innerHTML = `
        ${team.is_mine ? '<div class="mine-badge">내 팀</div>' : ''}
        <div class="team-field-badge" style="background:${s.bg};color:${s.color};">${s.emoji} ${escapeHtml(team.dev_field)}</div>
        <div class="team-name">${escapeHtml(team.name)}</div>
        <div class="team-leader">👑 ${escapeHtml(team.leader_name)}</div>
        ${team.description ? `<div class="team-desc">${escapeHtml(team.description)}</div>` : ''}
        <div class="card-divider"></div>
        <div class="team-members-label">
            <span>팀원</span>
            <span class="team-member-count">${memberCount}/${team.max_members}명</span>
        </div>
        <div class="team-member-slots">
            ${memberAvatars}
            ${emptySlots}
        </div>
        ${actionHtml}
    `;

    // 이벤트
    const joinBtn = card.querySelector('.team-join-btn');
    if (joinBtn) {
        joinBtn.addEventListener('click', async () => {
            joinBtn.disabled = true; joinBtn.textContent = '신청 중...';
            const res = await fetch(`/api/teams/${team.id}/join`, {method:'POST'});
            const data = await res.json();
            if (data.success) loadProfiles();
            else { alert(data.error || '오류 발생'); joinBtn.disabled=false; joinBtn.textContent='참여 신청'; }
        });
    }
    const manageBtn = card.querySelector('.team-manage-btn');
    if (manageBtn) {
        manageBtn.addEventListener('click', () => openManageModal(team));
    }
    const deleteBtn = card.querySelector('.team-delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            if (!confirm('팀을 삭제할까요?')) return;
            const res = await fetch(`/api/teams/${team.id}`, {method:'DELETE'});
            const data = await res.json();
            if (data.success) loadProfiles(); else alert(data.error || '삭제 실패');
        });
    }
    return card;
}

// ─── 로드 ───
async function loadProfiles() {
    const grid = document.getElementById('cardsGrid');
    grid.innerHTML = '<div class="loading">불러오는 중...</div>';
    try {
        if (currentTab === 'team') {
            const res = await fetch('/api/teams');
            const data = await res.json();
            grid.innerHTML = '';
            grid.appendChild(createPlusCard());
            data.teams.forEach(t => grid.appendChild(createTeamCard(t)));
        } else {
            const res = await fetch(`/api/profiles?type=${currentTab}`);
            const data = await res.json();
            grid.innerHTML = '';
            const alreadyHaveMine = data.profiles.some(p => p.is_mine);
            if (!alreadyHaveMine) grid.appendChild(createPlusCard());
            data.profiles.forEach(p => grid.appendChild(createProfileCard(p)));
        }
    } catch {
        grid.innerHTML = '<div class="loading">로딩 실패. 새로고침해주세요.</div>';
    }
}

// ─── 알림 ───
const bellBtn       = document.getElementById('bellBtn');
const notifBadge    = document.getElementById('notifBadge');
const notifDropdown = document.getElementById('notifDropdown');

function timeAgo(ts) {
    const diff = Math.floor((Date.now() / 1000) - ts);
    if (diff < 60)  return '방금 전';
    if (diff < 3600) return `${Math.floor(diff/60)}분 전`;
    if (diff < 86400) return `${Math.floor(diff/3600)}시간 전`;
    return `${Math.floor(diff/86400)}일 전`;
}

async function loadNotifications() {
    try {
        const res = await fetch('/api/notifications');
        const data = await res.json();
        if (data.unread > 0) {
            notifBadge.textContent = data.unread > 9 ? '9+' : data.unread;
            notifBadge.classList.remove('hidden');
        } else {
            notifBadge.classList.add('hidden');
        }
        renderNotifDropdown(data.notifications);
    } catch {}
}

function renderNotifDropdown(notifs) {
    if (!notifs.length) {
        notifDropdown.innerHTML = '<div class="notif-empty">알림이 없습니다</div>';
        return;
    }
    notifDropdown.innerHTML = '';
    notifs.forEach(n => {
        const row = document.createElement('div');
        row.className = `notif-row${n.is_read ? '' : ' notif-unread'}`;
        const isView = n.notif_type === 'view';
        const icon = isView ? '👀' : '👋';
        const msg = isView
            ? `<b>${escapeHtml(n.sender_nickname)}</b>님이 <b>${escapeHtml(n.profile_name)}</b> 프로필을 조회했습니다`
            : `<b>${escapeHtml(n.sender_nickname)}</b>님이 <b>${escapeHtml(n.profile_name)}</b>에 구인 신청을 보냈습니다`;
        row.innerHTML = `
            <div class="notif-icon">${icon}</div>
            <div class="notif-info">
                <div class="notif-msg">${msg}</div>
                <div class="notif-time">${timeAgo(n.created_at)}</div>
            </div>`;
        notifDropdown.appendChild(row);
    });
}

bellBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    const isOpen = !notifDropdown.classList.contains('hidden');
    if (isOpen) {
        notifDropdown.classList.add('hidden');
        return;
    }
    await loadNotifications();
    notifDropdown.classList.remove('hidden');
    // 읽음 처리
    if (!notifBadge.classList.contains('hidden')) {
        fetch('/api/notifications/read-all', {method:'POST'}).then(() => {
            notifBadge.classList.add('hidden');
        });
    }
});

document.addEventListener('click', e => {
    if (!document.getElementById('notifWrap').contains(e.target)) {
        notifDropdown.classList.add('hidden');
    }
});

loadNotifications();

// ─── DM (공유 모듈 dm.js 에서 처리) ───
const dmViewedSet = new Set();

function openDmFromProfile(profile) {
    // 조회 알림 (한 번만)
    if (!dmViewedSet.has(profile.id)) {
        dmViewedSet.add(profile.id);
        fetch(`/api/profiles/${profile.id}/view`, { method: 'POST' }).catch(() => {});
    }
    window.DM.openChat(profile.owner_id, profile.nickname || profile.name);
}

initPresets();
loadProfiles();
