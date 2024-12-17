import sqlite3
from flask import Flask, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import DataRequired, EqualTo, Length
from flask import flash, render_template, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# SQLite データベースの初期化
DATABASE = 'memo_app.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 辞書のような形で取得
    return conn

# ユーザーモデル（Flask-Login用）
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# ログインマネージャの設定
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ユーザーログイン情報の取得
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user['id'], user['username'], user['password'])
    return None

# パスワード変更フォームの定義
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('現在のパスワード', validators=[DataRequired()])
    new_password = PasswordField('新しいパスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('新しいパスワード確認', validators=[DataRequired(), EqualTo('new_password', message="パスワードが一致しません。")])

# パスワード変更ページ
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        # 現在のパスワードが正しいか確認
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = ?", (current_user.id,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], current_password):
            # 新しいパスワードをハッシュ化して更新
            hashed_password = generate_password_hash(new_password)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, current_user.id))
            conn.commit()
            conn.close()

            flash('パスワードが変更されました！', 'success')
            return redirect(url_for('index'))
        else:
            flash('現在のパスワードが間違っています。', 'error')

    return render_template('change_password.html', form=form)

# データベースの初期化関数
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # ユーザーテーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # メモテーブル作成（categoryカラムを追加）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    conn.commit()
    conn.close()
    

# アプリケーション初期化時にデータベースを初期化
with app.app_context():
    init_db()

# ホームページ（メモ表示）
@app.route('/', methods=['GET'])
@login_required
def index():
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    sort_order = request.args.get('sort', 'asc')
    start_date = request.args.get('start_date', '')  # 開始日
    end_date = request.args.get('end_date', '')      # 終了日

    conn = get_db()
    cursor = conn.cursor()

    order_by = "title ASC" if sort_order == 'asc' else "title DESC"

    query = "SELECT * FROM notes WHERE user_id = ?"
    params = [current_user.id]
    
    if search_query:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
    
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)

    query += f" ORDER BY {order_by}"
    cursor.execute(query, tuple(params))
    notes = cursor.fetchall()
    conn.close()

    return render_template('index.html', notes=notes, sort_order=sort_order, search_query=search_query)


# ログインページ
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['password']))
            return redirect(url_for('index'))
        else:
            flash('ログイン失敗: ユーザー名かパスワードが間違っています。')
    return render_template('login.html')

# ログアウト
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 新規ユーザー登録
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        
        flash('ユーザー登録完了！ログインしてください。')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# メモ作成
@app.route('/create_note', methods=['GET', 'POST'])
@login_required
def create_note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form['category']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (user_id, title, content, category, created_at) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
            (current_user.id, title, content, category)
        )
        conn.commit()
        conn.close()

        flash('メモが作成されました！')
        return redirect(url_for('index'))

    return render_template('create_note.html')


@app.route('/note_detail/<int:note_id>', methods=['GET'])
@login_required
def note_detail(note_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content, category, created_at FROM notes WHERE id = ? AND user_id = ?", 
        (note_id, current_user.id)
    )
    note = cursor.fetchone()
    conn.close()

    if note:
        return {
            "id": note["id"],
            "title": note["title"],
            "content": note["content"],
            "category": note["category"],
            "created_at": note["created_at"]
        }
    else:
        return {"error": "メモが見つかりません。"}, 404




# メモ編集
@app.route('/edit_note/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_note(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (id, current_user.id))
    note = cursor.fetchone()
    
    if not note:
        flash('権限がありません。')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notes 
            SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ? AND user_id = ?
        """, (title, content, id, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    conn.close()
    return render_template('edit_note.html', note=note)


# メモ削除
@app.route('/delete_note/<int:id>')
@login_required
def delete_note(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (id, current_user.id))
    conn.commit()
    conn.close()
    
    flash('メモが削除されました！')
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)