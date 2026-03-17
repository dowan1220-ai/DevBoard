from flask import Flask, render_template, request, redirect, url_for, session
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import text, or_, and_
from typing import Optional

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time

app = Flask(__name__)
app.secret_key = 'rlawldhrladmstjrlaehdhks'

def send_verification_email(receiver_email, auth_code, subject="[서비스 이름] 인증번호입니다."):
    sender_email = "jok10com@gmail.com"
    app_password = "mdsv afzd egvx ancu"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    body = f"""
    안녕하세요, 요청하신 인증번호를 안내해 드립니다.

    인증번호: [{auth_code}]

    해당 번호를 인증 창에 입력해 주세요.
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        print(f"성공: {receiver_email}로 인증번호를 보냈습니다.")
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    nickname: Optional[str] = Field(default=None)
    failed_attempts: int = Field(default=0)       # 로그인 실패 횟수
    locked_until: Optional[float] = Field(default=None)  # 잠금 해제 시각 (Unix timestamp)
    is_admin: bool = Field(default=False)


class Notice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default='')
    content: str = Field(default='')
    author_id: str
    author_nickname: str = Field(default='')
    is_pinned: bool = Field(default=False)
    created_at: float = Field(default=0.0)
    updated_at: float = Field(default=0.0)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    leader_id: str
    leader_name: str
    name: str
    description: str = Field(default='')
    dev_field: str = Field(default='')
    max_members: int = Field(default=4)
    created_at: float = Field(default=0.0)


class TeamMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int
    user_id: str
    display_name: str
    status: str = Field(default='pending')   # 'pending' | 'accepted' | 'rejected'
    joined_at: float = Field(default=0.0)


class DirectMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: str
    receiver_id: str
    message: str = Field(default='')
    is_read: bool = Field(default=False)
    created_at: float = Field(default=0.0)


class RecruitInterest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int
    sender_id: str
    created_at: float = Field(default=0.0)


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str          # 받는 사람
    sender_id: str
    sender_nickname: str
    profile_id: int = Field(default=0)
    profile_name: str = Field(default='')
    notif_type: str = Field(default='interest')  # 'interest' | 'view'
    is_read: bool = Field(default=False)
    created_at: float = Field(default=0.0)


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field()
    name: str
    class_number: str
    major: str
    bio: str = Field(default='')
    past_languages: str = Field(default='')
    current_languages: str = Field(default='')
    profile_image: Optional[str] = Field(default=None)
    post_type: str = Field(default='recruit')       # 'recruit' | 'job_seek'
    dev_field: Optional[str] = Field(default=None)  # '풀스택' | '백엔드' | '프론트엔드'
    created_at: float = Field(default=0.0)


sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url)

with app.app_context():
    SQLModel.metadata.create_all(engine)
    # 기존 DB에 nickname 컬럼 없을 경우 추가
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN nickname VARCHAR"))
            conn.commit()
        except Exception:
            pass
        # Profile.user_id unique 제약 제거 (다중 프로필 허용)
        for idx_name in ('ix_profile_user_id', 'uq_profile_user_id', 'profile_user_id'):
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                conn.commit()
            except Exception:
                pass
        # 구직 컬럼 추가
        for col_sql in (
            "ALTER TABLE profile ADD COLUMN post_type VARCHAR DEFAULT 'recruit'",
            "ALTER TABLE profile ADD COLUMN dev_field VARCHAR",
            "ALTER TABLE profile ADD COLUMN bio VARCHAR DEFAULT ''",
            "ALTER TABLE notification ADD COLUMN notif_type VARCHAR DEFAULT 'interest'",
            "ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0",
        ):
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except Exception:
                pass


def check_admin():
    """현재 로그인 유저가 관리자인지 확인"""
    uid = session.get('user_id')
    if not uid:
        return False
    with Session(engine) as db_session:
        u = db_session.exec(select(User).where(User.username == uid)).first()
        return bool(u and u.is_admin)


@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/login_page')
def login_page():
    show_toast = session.pop('show_login_toast', False)
    return render_template('login.html', show_toast=show_toast)


# ───────────── 로그인 ─────────────
@app.route('/login', methods=['POST'])
def login():
    input_id = request.form.get('email')
    input_pw = request.form.get('password')

    if not input_id or not input_pw:
        return "<script>alert('아이디와 비밀번호를 입력해주세요.'); history.back();</script>"

    with Session(engine) as db_session:
        statement = select(User).where(User.username == input_id)
        user = db_session.exec(statement).first()

        if not user:
            return "<script>alert('아이디 또는 비밀번호가 틀렸습니다.'); history.back();</script>"

        # 잠금 여부 확인
        if user.locked_until and time.time() < user.locked_until:
            remaining = int((user.locked_until - time.time()) / 60) + 1
            return f"<script>alert('로그인 5회 실패로 계정이 잠겼습니다.\\n{remaining}분 후 다시 시도하거나 비밀번호 찾기를 이용해주세요.'); history.back();</script>"

        if user.password == input_pw:
            # 로그인 성공 → 실패 횟수 초기화
            user.failed_attempts = 0
            user.locked_until = None
            db_session.add(user)
            db_session.commit()
            session['user_id'] = user.username
            session['nickname'] = user.nickname or user.username
            session['show_login_toast'] = True
            return redirect(url_for('home'))
        else:
            # 로그인 실패 → 실패 횟수 증가
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = time.time() + 30 * 60  # 30분 잠금
                db_session.add(user)
                db_session.commit()
                return "<script>alert('비밀번호를 5회 틀렸습니다.\\n30분간 로그인이 잠깁니다. 비밀번호 찾기를 이용해주세요.'); history.back();</script>"
            else:
                remaining = 5 - user.failed_attempts
                db_session.add(user)
                db_session.commit()
                return f"<script>alert('아이디 또는 비밀번호가 틀렸습니다.\\n(남은 시도 횟수: {remaining}회)'); history.back();</script>"


# ───────────── 홈 / 로그아웃 ─────────────
@app.route('/main')
def home():
    show_toast = session.pop('show_login_toast', False)
    nickname = session.get('nickname', session.get('user_id', '게스트'))
    return render_template('main.html', user_id=nickname, show_toast=show_toast, is_admin=check_admin())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ───────────── 회원가입 ─────────────
@app.route('/signup')
def signup_page():
    return render_template('first-login.html')

@app.route('/check_email', methods=['POST'])
def check_email():
    email_local = request.form.get('email', '').strip()
    if not email_local:
        return {"exists": False}
    with Session(engine) as db_session:
        existing = db_session.exec(select(User).where(User.username == email_local)).first()
    return {"exists": bool(existing)}


@app.route('/send_code', methods=['POST'])
def send_code():
    email_local = request.form.get('email', '').strip()
    if not email_local:
        return {"success": False, "message": "이메일을 입력해주세요."}, 400

    # 이미 가입된 이메일인지 확인
    with Session(engine) as db_session:
        existing = db_session.exec(select(User).where(User.username == email_local)).first()
    if existing:
        return {"success": False, "message": "이미 가입된 이메일입니다."}, 400

    code = str(random.randint(100000, 999999)).zfill(6)
    session['verification_code'] = code
    session['verified_email_local'] = email_local
    session['email_verified'] = False

    full_email = f"{email_local}@gmail.com"
    sent = send_verification_email(full_email, code, "[서비스 이름] 회원가입 인증번호입니다.")
    if sent:
        return {"success": True, "message": "인증번호를 발송했습니다. 이메일을 확인해주세요."}
    return {"success": False, "message": "인증번호 발송에 실패했습니다."}, 500


@app.route('/verify_code', methods=['POST'])
def verify_code():
    email_local = request.form.get('email', '').strip()
    code = request.form.get('code', '').strip()

    if not email_local or not code:
        return {"success": False, "message": "이메일과 인증번호를 모두 입력해주세요."}, 400

    expected_email_local = session.get('verified_email_local')
    expected_code = session.get('verification_code')

    if not expected_code or not expected_email_local:
        return {"success": False, "message": "먼저 인증번호를 요청해주세요."}, 400
    if email_local != expected_email_local:
        return {"success": False, "message": "이메일이 변경되었습니다. 인증번호를 다시 요청해주세요."}, 400
    if code == expected_code:
        session['email_verified'] = True
        return {"success": True, "message": "인증이 완료되었습니다.", "buttonText": "인증완료"}

    return {"success": False, "message": "인증번호가 일치하지 않습니다."}, 400


@app.route('/signup_process', methods=['POST'])
def signup_process():
    u_id = request.form.get('email')
    u_pw = request.form.get('password')
    u_nickname = request.form.get('nickname', '').strip()

    if not u_id or not u_pw or not u_nickname:
        return "<script>alert('정보를 모두 입력해주세요.'); history.back();</script>"
    if not session.get('email_verified') or session.get('verified_email_local') != u_id:
        return "<script>alert('이메일 인증을 완료해주세요.'); history.back();</script>"

    # 최종 중복 확인
    with Session(engine) as db_session:
        existing = db_session.exec(select(User).where(User.username == u_id)).first()
        if existing:
            return "<script>alert('이미 가입된 이메일입니다.'); history.back();</script>"

        new_user = User(username=u_id, password=u_pw, nickname=u_nickname)
        db_session.add(new_user)
        db_session.commit()

    session.pop('email_verified', None)
    session.pop('verification_code', None)
    session.pop('verified_email_local', None)

    return render_template("go-login.html")


# ───────────── 비밀번호 찾기 ─────────────
@app.route('/forgot_password')
def forgot_password_page():
    return render_template('forgot-password.html')


@app.route('/send_reset_code', methods=['POST'])
def send_reset_code():
    email_local = request.form.get('email', '').strip()
    if not email_local:
        return {"success": False, "message": "이메일을 입력해주세요."}, 400

    full_email = f"{email_local}@gmail.com"

    # 가입된 이메일인지 확인
    with Session(engine) as db_session:
        statement = select(User).where(User.username == email_local)
        user = db_session.exec(statement).first()

    if not user:
        return {"success": False, "message": "가입되지 않은 이메일입니다."}, 400

    code = str(random.randint(100000, 999999)).zfill(6)
    session['reset_code'] = code
    session['reset_email'] = email_local

    sent = send_verification_email(full_email, code, "[서비스 이름] 비밀번호 재설정 인증번호입니다.")
    if sent:
        return {"success": True, "message": "인증번호를 발송했습니다. 이메일을 확인해주세요."}
    return {"success": False, "message": "인증번호 발송에 실패했습니다."}, 500


@app.route('/verify_reset_code', methods=['POST'])
def verify_reset_code():
    email_local = request.form.get('email', '').strip()
    code = request.form.get('code', '').strip()

    if not email_local or not code:
        return {"success": False, "message": "이메일과 인증번호를 모두 입력해주세요."}, 400

    if session.get('reset_email') != email_local:
        return {"success": False, "message": "이메일이 변경되었습니다. 다시 요청해주세요."}, 400
    if session.get('reset_code') != code:
        return {"success": False, "message": "인증번호가 일치하지 않습니다."}, 400

    session['reset_verified'] = True
    return {"success": True, "message": "인증이 완료되었습니다."}


@app.route('/reset_password', methods=['POST'])
def reset_password():
    new_pw = request.form.get('password', '').strip()
    email_local = session.get('reset_email')

    if not session.get('reset_verified') or not email_local:
        return "<script>alert('인증을 먼저 완료해주세요.'); history.back();</script>"
    if not new_pw:
        return "<script>alert('새 비밀번호를 입력해주세요.'); history.back();</script>"

    with Session(engine) as db_session:
        statement = select(User).where(User.username == email_local)
        user = db_session.exec(statement).first()
        if not user:
            return "<script>alert('사용자를 찾을 수 없습니다.'); history.back();</script>"

        user.password = new_pw
        user.failed_attempts = 0
        user.locked_until = None
        db_session.add(user)
        db_session.commit()

    session.pop('reset_code', None)
    session.pop('reset_email', None)
    session.pop('reset_verified', None)

    return "<script>alert('비밀번호가 변경되었습니다. 다시 로그인해주세요.'); location.href='/';</script>"


# ───────────── 회원 정보 수정 ─────────────
@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    nickname = session.get('nickname', session['user_id'])
    return render_template('settings.html', user_id=session['user_id'], nickname=nickname)


@app.route('/update_nickname', methods=['POST'])
def update_nickname():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    new_nickname = request.form.get('nickname', '').strip()
    if not new_nickname:
        return {"error": "닉네임을 입력해주세요."}, 400
    if len(new_nickname) > 20:
        return {"error": "닉네임은 20자 이하여야 합니다."}, 400
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == session['user_id'])).first()
        if not user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        user.nickname = new_nickname
        db_session.add(user)
        # 이 유저가 작성한 공지 닉네임도 일괄 업데이트
        notices = db_session.exec(select(Notice).where(Notice.author_id == session['user_id'])).all()
        for n in notices:
            n.author_nickname = new_nickname
            db_session.add(n)
        db_session.commit()
    session['nickname'] = new_nickname
    return {"success": True, "nickname": new_nickname}


# ───────────── 공지사항 ─────────────
@app.route('/notice')
def notice():
    nickname = session.get('nickname', session.get('user_id', '게스트'))
    return render_template('notice.html', user_id=nickname, is_admin=check_admin())


@app.route('/api/notices', methods=['GET'])
def get_notices():
    with Session(engine) as db_session:
        notices = db_session.exec(
            select(Notice).order_by(Notice.is_pinned.desc(), Notice.created_at.desc())
        ).all()
    return {"notices": [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "author_nickname": n.author_nickname,
            "is_pinned": n.is_pinned,
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        } for n in notices
    ]}


@app.route('/api/notices', methods=['POST'])
def create_notice():
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    is_pinned = request.form.get('is_pinned', 'false') == 'true'
    if not title or not content:
        return {"error": "제목과 내용을 입력해주세요."}, 400
    nickname = session.get('nickname', session['user_id'])
    with Session(engine) as db_session:
        notice = Notice(
            title=title, content=content,
            author_id=session['user_id'], author_nickname=nickname,
            is_pinned=is_pinned,
            created_at=time.time(), updated_at=time.time()
        )
        db_session.add(notice)
        db_session.commit()
        db_session.refresh(notice)
    return {"success": True, "id": notice.id}


@app.route('/api/notices/<int:notice_id>', methods=['PUT'])
def update_notice(notice_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    is_pinned = request.form.get('is_pinned', 'false') == 'true'
    if not title or not content:
        return {"error": "제목과 내용을 입력해주세요."}, 400
    with Session(engine) as db_session:
        notice = db_session.get(Notice, notice_id)
        if not notice:
            return {"error": "공지를 찾을 수 없습니다."}, 404
        notice.title = title
        notice.content = content
        notice.is_pinned = is_pinned
        notice.updated_at = time.time()
        db_session.add(notice)
        db_session.commit()
    return {"success": True}


@app.route('/api/notices/<int:notice_id>', methods=['DELETE'])
def delete_notice(notice_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    with Session(engine) as db_session:
        notice = db_session.get(Notice, notice_id)
        if not notice:
            return {"error": "공지를 찾을 수 없습니다."}, 404
        db_session.delete(notice)
        db_session.commit()
    return {"success": True}


# ───────────── 관리자 페이지 ─────────────
@app.route('/admin')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    if not check_admin():
        return redirect(url_for('home'))
    nickname = session.get('nickname', session['user_id'])
    return render_template('admin.html', user_id=nickname, current_user=session['user_id'])


@app.route('/admin/setup')
def admin_setup():
    """첫 관리자 설정 (로그인 상태에서 호출)"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    secret = request.args.get('secret', '')
    if secret != app.config.get('ADMIN_SECRET', 'devboard_admin_2025'):
        return "잘못된 시크릿 키입니다.", 403
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == session['user_id'])).first()
        if user:
            user.is_admin = True
            db_session.add(user)
            db_session.commit()
    return "<script>alert('관리자로 등록되었습니다!'); location.href='/admin';</script>"


@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    with Session(engine) as db_session:
        users = db_session.exec(select(User)).all()
        profiles = db_session.exec(select(Profile)).all()
        teams = db_session.exec(select(Team)).all()
    profile_count = {}
    for p in profiles:
        profile_count[p.user_id] = profile_count.get(p.user_id, 0) + 1
    team_count = {}
    for t in teams:
        team_count[t.leader_id] = team_count.get(t.leader_id, 0) + 1
    return {"users": [
        {
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname or u.username,
            "is_admin": u.is_admin,
            "is_locked": bool(u.locked_until and time.time() < u.locked_until),
            "locked_until": u.locked_until,
            "failed_attempts": u.failed_attempts,
            "profile_count": profile_count.get(u.username, 0),
            "team_count": team_count.get(u.username, 0),
        } for u in users
    ]}


@app.route('/api/admin/users/<target_id>/lock', methods=['POST'])
def admin_lock_user(target_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    minutes = int(request.form.get('minutes', 30))
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == target_id)).first()
        if not user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        user.locked_until = time.time() + minutes * 60
        db_session.add(user)
        db_session.commit()
    return {"success": True}


@app.route('/api/admin/users/<target_id>/unlock', methods=['POST'])
def admin_unlock_user(target_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == target_id)).first()
        if not user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        user.locked_until = None
        user.failed_attempts = 0
        db_session.add(user)
        db_session.commit()
    return {"success": True}


@app.route('/api/admin/users/<target_id>/toggle-admin', methods=['POST'])
def admin_toggle_admin(target_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    if target_id == session['user_id']:
        return {"error": "본인의 관리자 권한은 변경할 수 없습니다."}, 400
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == target_id)).first()
        if not user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        user.is_admin = not user.is_admin
        db_session.add(user)
        db_session.commit()
    return {"success": True, "is_admin": user.is_admin}


@app.route('/api/admin/users/<target_id>', methods=['DELETE'])
def admin_delete_user(target_id):
    if not check_admin():
        return {"error": "권한이 없습니다."}, 403
    if target_id == session['user_id']:
        return {"error": "본인 계정은 삭제할 수 없습니다."}, 400
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == target_id)).first()
        if not user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        # 관련 데이터 삭제
        for profile in db_session.exec(select(Profile).where(Profile.user_id == target_id)).all():
            db_session.delete(profile)
        for notif in db_session.exec(select(Notification).where(
            or_(Notification.user_id == target_id, Notification.sender_id == target_id)
        )).all():
            db_session.delete(notif)
        for dm in db_session.exec(select(DirectMessage).where(
            or_(DirectMessage.sender_id == target_id, DirectMessage.receiver_id == target_id)
        )).all():
            db_session.delete(dm)
        db_session.delete(user)
        db_session.commit()
    return {"success": True}


# ───────────── 닉네임 검색 ─────────────
@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return {"results": []}
    with Session(engine) as db_session:
        users = db_session.exec(select(User)).all()
    results = []
    for u in users:
        nickname = u.nickname or u.username
        if q in nickname.lower() or q in u.username.lower():
            results.append({"nickname": nickname, "username": u.username})
    return {"results": results[:10]}


# ───────────── 활동 통계 ─────────────
@app.route('/api/stats')
def api_stats():
    with Session(engine) as db_session:
        user_count = len(db_session.exec(select(User)).all())
        profile_count = len(db_session.exec(select(Profile)).all())
    return {"users": user_count, "profiles": profile_count}


# ───────────── 새 글 확인용 최신 타임스탬프 ─────────────
@app.route('/api/new-activity')
def new_activity():
    with Session(engine) as db_session:
        profiles = db_session.exec(select(Profile)).all()
        notices  = db_session.exec(select(Notice)).all()
    profile_latest = max((p.created_at for p in profiles), default=0)
    notice_latest  = max((n.created_at for n in notices),  default=0)
    return {"profile_latest": profile_latest, "notice_latest": notice_latest}


# ───────────── 구인 게시판 ─────────────
@app.route('/recruit')
def recruit():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    nickname = session.get('nickname', session['user_id'])
    return render_template('recruit.html', user_id=nickname, is_admin=check_admin())


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    ptype = request.args.get('type', 'recruit')
    with Session(engine) as db_session:
        profiles = db_session.exec(
            select(Profile)
            .where(Profile.post_type == ptype)
            .order_by(Profile.created_at)
        ).all()
        users = db_session.exec(select(User)).all()
        interests = db_session.exec(
            select(RecruitInterest).where(RecruitInterest.sender_id == current_user)
        ).all()
    nickname_map = {u.username: (u.nickname or u.username) for u in users}
    sent_set = {i.profile_id for i in interests}
    mine = []
    others = []
    for p in profiles:
        data = {
            "id": p.id,
            "name": p.name,
            "nickname": nickname_map.get(p.user_id, p.user_id),
            "bio": p.bio or '',
            "class_number": p.class_number,
            "major": p.major,
            "past_languages": [l.strip() for l in p.past_languages.split(',') if l.strip()],
            "current_languages": [l.strip() for l in p.current_languages.split(',') if l.strip()],
            "profile_image": p.profile_image,
            "post_type": p.post_type,
            "dev_field": p.dev_field,
            "is_mine": p.user_id == current_user,
            "interest_sent": p.id in sent_set,
            "owner_id": p.user_id
        }
        if p.user_id == current_user:
            mine.append(data)
        else:
            others.append(data)
    return {"profiles": mine + others}


@app.route('/api/profiles', methods=['POST'])
def create_profile():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        existing = db_session.exec(
            select(Profile).where(Profile.user_id == current_user)
        ).first()
        if existing:
            return {"error": "이미 구인 프로필이 등록되어 있습니다."}, 400
        name = request.form.get('name', '').strip()
        class_number = request.form.get('class_number', '').strip()
        major = request.form.get('major', '').strip()
        bio = request.form.get('bio', '').strip()
        past_languages = request.form.get('past_languages', '').strip()
        current_languages = request.form.get('current_languages', '').strip()
        profile_image = request.form.get('profile_image', '').strip()
        post_type = request.form.get('post_type', 'recruit').strip()
        dev_field = request.form.get('dev_field', '').strip() or None
        if not name or not class_number or not major:
            return {"error": "이름, 반/번호, 전공은 필수입니다."}, 400
        if post_type == 'job_seek' and not dev_field:
            return {"error": "개발 분야를 선택해주세요."}, 400
        profile = Profile(
            user_id=current_user,
            name=name,
            bio=bio,
            class_number=class_number,
            major=major,
            past_languages=past_languages,
            current_languages=current_languages,
            profile_image=profile_image if profile_image else None,
            post_type=post_type,
            dev_field=dev_field,
            created_at=time.time()
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)
        return {
            "success": True,
            "profile": {
                "id": profile.id,
                "name": profile.name,
                "class_number": profile.class_number,
                "major": profile.major,
                "past_languages": [l.strip() for l in profile.past_languages.split(',') if l.strip()],
                "current_languages": [l.strip() for l in profile.current_languages.split(',') if l.strip()],
                "profile_image": profile.profile_image,
                "is_mine": True
            }
        }


# ───────────── 팀 게시판 ─────────────
@app.route('/api/teams', methods=['GET'])
def get_teams():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        teams = db_session.exec(select(Team).order_by(Team.created_at)).all()
        members_all = db_session.exec(select(TeamMember)).all()
    mem_map = {}
    for m in members_all:
        mem_map.setdefault(m.team_id, []).append(m)
    result = []
    for t in teams:
        mems = mem_map.get(t.id, [])
        accepted = [m for m in mems if m.status == 'accepted']
        pending  = [m for m in mems if m.status == 'pending']
        my_status = next((m.status for m in mems if m.user_id == current_user), None)
        result.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "dev_field": t.dev_field,
            "max_members": t.max_members,
            "leader_id": t.leader_id,
            "leader_name": t.leader_name,
            "is_mine": t.leader_id == current_user,
            "my_status": my_status,
            "members": [{"id": m.id, "user_id": m.user_id, "display_name": m.display_name, "status": m.status} for m in accepted],
            "pending_count": len(pending),
            "pending_list": [{"id": m.id, "user_id": m.user_id, "display_name": m.display_name} for m in pending] if t.leader_id == current_user else [],
        })
    return {"teams": result}


@app.route('/api/teams', methods=['POST'])
def create_team():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    nickname = session.get('nickname', current_user)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    dev_field = request.form.get('dev_field', '').strip()
    max_members = int(request.form.get('max_members', 4))
    if not name:
        return {"error": "팀 이름은 필수입니다."}, 400
    with Session(engine) as db_session:
        team = Team(leader_id=current_user, leader_name=nickname,
                    name=name, description=description,
                    dev_field=dev_field, max_members=max_members,
                    created_at=time.time())
        db_session.add(team)
        db_session.commit()
    return {"success": True}


@app.route('/api/teams/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    with Session(engine) as db_session:
        team = db_session.get(Team, team_id)
        if not team:
            return {"error": "팀을 찾을 수 없습니다."}, 404
        if team.leader_id != session['user_id']:
            return {"error": "권한이 없습니다."}, 403
        db_session.exec(select(TeamMember).where(TeamMember.team_id == team_id))
        for m in db_session.exec(select(TeamMember).where(TeamMember.team_id == team_id)).all():
            db_session.delete(m)
        db_session.delete(team)
        db_session.commit()
    return {"success": True}


@app.route('/api/teams/<int:team_id>/join', methods=['POST'])
def join_team(team_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    nickname = session.get('nickname', current_user)
    with Session(engine) as db_session:
        team = db_session.get(Team, team_id)
        if not team:
            return {"error": "팀을 찾을 수 없습니다."}, 404
        if team.leader_id == current_user:
            return {"error": "본인 팀에는 신청할 수 없습니다."}, 400
        existing = db_session.exec(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == current_user)
        ).first()
        if existing:
            return {"error": "이미 신청했습니다."}, 400
        accepted_count = len(db_session.exec(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.status == 'accepted')
        ).all())
        if accepted_count >= team.max_members:
            return {"error": "팀 정원이 꽉 찼습니다."}, 400
        member = TeamMember(team_id=team_id, user_id=current_user,
                            display_name=nickname, status='pending',
                            joined_at=time.time())
        db_session.add(member)
        db_session.commit()
    return {"success": True}


@app.route('/api/teams/<int:team_id>/respond', methods=['POST'])
def respond_team(team_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        team = db_session.get(Team, team_id)
        if not team or team.leader_id != current_user:
            return {"error": "권한이 없습니다."}, 403
        member_id = int(request.form.get('member_id', 0))
        action = request.form.get('action', '')  # 'accept' | 'reject'
        member = db_session.get(TeamMember, member_id)
        if not member or member.team_id != team_id:
            return {"error": "멤버를 찾을 수 없습니다."}, 404
        if action == 'accept':
            accepted_count = len(db_session.exec(
                select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.status == 'accepted')
            ).all())
            if accepted_count >= team.max_members:
                return {"error": "팀 정원이 꽉 찼습니다."}, 400
            member.status = 'accepted'
        elif action == 'reject':
            member.status = 'rejected'
        else:
            return {"error": "잘못된 액션입니다."}, 400
        db_session.add(member)
        db_session.commit()
    return {"success": True}


# ───────────── 구인하기 (관심 표현) ─────────────
@app.route('/api/profiles/<int:profile_id>/interest', methods=['POST'])
def recruit_interest(profile_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    nickname = session.get('nickname', current_user)
    with Session(engine) as db_session:
        profile = db_session.get(Profile, profile_id)
        if not profile:
            return {"error": "프로필을 찾을 수 없습니다."}, 404
        if profile.user_id == current_user:
            return {"error": "본인 게시글에는 구인할 수 없습니다."}, 400
        existing = db_session.exec(
            select(RecruitInterest).where(
                RecruitInterest.profile_id == profile_id,
                RecruitInterest.sender_id == current_user
            )
        ).first()
        if existing:
            return {"error": "이미 구인 신청을 보냈습니다."}, 400
        interest = RecruitInterest(
            profile_id=profile_id,
            sender_id=current_user,
            created_at=time.time()
        )
        db_session.add(interest)
        notif = Notification(
            user_id=profile.user_id,
            sender_id=current_user,
            sender_nickname=nickname,
            profile_id=profile_id,
            profile_name=profile.name,
            is_read=False,
            created_at=time.time()
        )
        db_session.add(notif)
        db_session.commit()
    return {"success": True}


# ───────────── 알림 ─────────────
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        notifs = db_session.exec(
            select(Notification)
            .where(Notification.user_id == current_user)
            .order_by(Notification.created_at.desc())
        ).all()
        unread = sum(1 for n in notifs if not n.is_read)
    return {
        "notifications": [
            {
                "id": n.id,
                "sender_nickname": n.sender_nickname,
                "profile_name": n.profile_name,
                "notif_type": n.notif_type,
                "is_read": n.is_read,
                "created_at": n.created_at
            } for n in notifs[:20]
        ],
        "unread": unread
    }


@app.route('/api/profiles/<int:profile_id>/view', methods=['POST'])
def view_profile(profile_id):
    if 'user_id' not in session:
        return {"success": False}, 401
    current_user = session['user_id']
    nickname = session.get('nickname', current_user)
    with Session(engine) as db_session:
        profile = db_session.get(Profile, profile_id)
        if not profile or profile.user_id == current_user:
            return {"success": False}
        # 이미 같은 사람이 같은 프로필에 view 알림을 보낸 경우 중복 방지
        existing = db_session.exec(
            select(Notification).where(
                Notification.user_id == profile.user_id,
                Notification.sender_id == current_user,
                Notification.notif_type == 'view',
                Notification.profile_id == profile_id
            )
        ).first()
        if existing:
            return {"success": True}
        notif = Notification(
            user_id=profile.user_id,
            sender_id=current_user,
            sender_nickname=nickname,
            profile_id=profile_id,
            profile_name=profile.name,
            notif_type='view',
            is_read=False,
            created_at=time.time()
        )
        db_session.add(notif)
        db_session.commit()
    return {"success": True}


# ───────────── DM ─────────────
@app.route('/api/dm/unread', methods=['GET'])
def dm_unread():
    if 'user_id' not in session:
        return {"unread": 0}
    current_user = session['user_id']
    with Session(engine) as db_session:
        count = len(db_session.exec(
            select(DirectMessage).where(
                DirectMessage.receiver_id == current_user,
                DirectMessage.is_read == False
            )
        ).all())
    return {"unread": count}


@app.route('/api/dm/conversations', methods=['GET'])
def dm_conversations():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        messages = db_session.exec(
            select(DirectMessage).where(
                or_(DirectMessage.sender_id == current_user,
                    DirectMessage.receiver_id == current_user)
            ).order_by(DirectMessage.created_at.desc())
        ).all()
        users = db_session.exec(select(User)).all()
        nickname_map = {u.username: (u.nickname or u.username) for u in users}
    conv_map = {}
    for msg in messages:
        partner = msg.receiver_id if msg.sender_id == current_user else msg.sender_id
        if partner not in conv_map:
            conv_map[partner] = {
                'user_id': partner,
                'nickname': nickname_map.get(partner, partner),
                'last_message': msg.message,
                'last_time': msg.created_at,
                'unread': 0
            }
        if msg.receiver_id == current_user and not msg.is_read:
            conv_map[partner]['unread'] += 1
    convs = sorted(conv_map.values(), key=lambda x: x['last_time'], reverse=True)
    return {"conversations": convs}


@app.route('/api/dm/<other_user_id>', methods=['GET'])
def get_dm(other_user_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        messages = db_session.exec(
            select(DirectMessage).where(
                or_(
                    and_(DirectMessage.sender_id == current_user,
                         DirectMessage.receiver_id == other_user_id),
                    and_(DirectMessage.sender_id == other_user_id,
                         DirectMessage.receiver_id == current_user)
                )
            ).order_by(DirectMessage.created_at.asc())
        ).all()
        for msg in messages:
            if msg.receiver_id == current_user and not msg.is_read:
                msg.is_read = True
                db_session.add(msg)
        db_session.commit()
        other_user = db_session.exec(select(User).where(User.username == other_user_id)).first()
        other_nickname = (other_user.nickname or other_user_id) if other_user else other_user_id
    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "message": m.message,
                "created_at": m.created_at,
                "is_mine": m.sender_id == current_user
            } for m in messages
        ],
        "other_nickname": other_nickname
    }


@app.route('/api/dm/<other_user_id>', methods=['POST'])
def send_dm(other_user_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    message_text = request.form.get('message', '').strip()
    if not message_text:
        return {"error": "메시지를 입력해주세요."}, 400
    with Session(engine) as db_session:
        other_user = db_session.exec(select(User).where(User.username == other_user_id)).first()
        if not other_user:
            return {"error": "사용자를 찾을 수 없습니다."}, 404
        dm = DirectMessage(
            sender_id=current_user,
            receiver_id=other_user_id,
            message=message_text,
            created_at=time.time()
        )
        db_session.add(dm)
        db_session.commit()
        db_session.refresh(dm)
    return {"success": True, "message": {
        "id": dm.id, "message": dm.message,
        "created_at": dm.created_at, "is_mine": True
    }}


@app.route('/api/notifications/read-all', methods=['POST'])
def read_all_notifications():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        notifs = db_session.exec(
            select(Notification).where(
                Notification.user_id == current_user,
                Notification.is_read == False
            )
        ).all()
        for n in notifs:
            n.is_read = True
            db_session.add(n)
        db_session.commit()
    return {"success": True}


@app.route('/api/profiles/<int:profile_id>', methods=['PUT'])
def update_profile(profile_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        profile = db_session.get(Profile, profile_id)
        if not profile:
            return {"error": "프로필을 찾을 수 없습니다."}, 404
        if profile.user_id != current_user:
            return {"error": "권한이 없습니다."}, 403
        name = request.form.get('name', '').strip()
        class_number = request.form.get('class_number', '').strip()
        major = request.form.get('major', '').strip()
        bio = request.form.get('bio', '').strip()
        past_languages = request.form.get('past_languages', '').strip()
        current_languages = request.form.get('current_languages', '').strip()
        profile_image = request.form.get('profile_image', '').strip()
        if not name or not class_number or not major:
            return {"error": "이름, 반/번호, 전공은 필수입니다."}, 400
        profile.name = name
        profile.class_number = class_number
        profile.major = major
        profile.bio = bio
        profile.past_languages = past_languages
        profile.current_languages = current_languages
        if profile_image:
            profile.profile_image = profile_image
        db_session.add(profile)
        db_session.commit()
    return {"success": True}


@app.route('/api/profiles/<int:profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401
    current_user = session['user_id']
    with Session(engine) as db_session:
        profile = db_session.get(Profile, profile_id)
        if not profile:
            return {"error": "프로필을 찾을 수 없습니다."}, 404
        if profile.user_id != current_user:
            return {"error": "권한이 없습니다."}, 403
        db_session.delete(profile)
        db_session.commit()
    return {"success": True}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
