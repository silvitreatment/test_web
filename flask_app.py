import os
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, abort, g, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///knowledge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'SOME_SECRET_KEY')
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME', 'admin')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'password123')
app.config['ADMIN_EMAILS'] = [e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()]
app.config['MODERATOR_EMAILS'] = [e.strip().lower() for e in os.environ.get('MODERATOR_EMAILS', '').split(',') if e.strip()]
app.config['ADMIN_TELEGRAMS'] = [e.strip().lower() for e in os.environ.get('ADMIN_TELEGRAMS', '').split(',') if e.strip()]
app.config['MODERATOR_TELEGRAMS'] = [e.strip().lower() for e in os.environ.get('MODERATOR_TELEGRAMS', '').split(',') if e.strip()]

db = SQLAlchemy(app)
ROLE_HIERARCHY = {'user': 0, 'moderator': 1, 'admin': 2}


def resolve_role(email=None, username=None):
    return 'user'


def set_current_user(user):
    session['user_id'] = user.id
    session['role'] = user.role


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.current_user:
            return redirect(url_for('login', next=request.url))
        return view(*args, **kwargs)
    return wrapped


def require_roles(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = g.current_user
            if not user or user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.before_request
def load_current_user():
    user_id = session.get('user_id')
    g.current_user = User.query.get(user_id) if user_id else None


@app.context_processor
def inject_user():
    return {
        'current_user': getattr(g, 'current_user', None),
        'app_config': app.config,
    }


_db_ready = False


def ensure_schema():
    inspector = inspect(db.engine)
    try:
        columns = {col['name'] for col in inspector.get_columns('article')}
    except OperationalError:
        db.create_all()
        columns = {col['name'] for col in inspector.get_columns('article')}

    with db.engine.begin() as conn:
        if 'status' not in columns:
            conn.execute(text("ALTER TABLE article ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
        if 'author_name' not in columns:
            conn.execute(text("ALTER TABLE article ADD COLUMN author_name VARCHAR(200)"))
        try:
            user_cols = {col['name'] for col in inspector.get_columns('user')}
        except OperationalError:
            db.create_all()
            user_cols = {col['name'] for col in inspector.get_columns('user')}
        if 'password_hash' not in user_cols:
            conn.execute(text("ALTER TABLE user ADD COLUMN password_hash VARCHAR(255)"))

@app.before_request
def setup_db():
    global _db_ready
    if _db_ready:
        return
    db.create_all()
    ensure_schema()
    _db_ready = True


@app.route('/articles/new')
@require_login
def new_article():
    return render_template('new_article.html')


@app.route('/articles/<int:article_id>/delete', methods=['POST'])
@require_roles('admin')
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash('The article is deleted')
    return redirect(url_for('index'))


@app.route('/articles', methods=["POST"])
@require_login
def create_article():
    title = request.form['title']
    content = request.form['content']

    status = 'published' if g.current_user and g.current_user.role in ('moderator', 'admin') else 'pending'
    author_name = g.current_user.name if g.current_user else None

    new_article = Article(title=title, content=content, status=status, author_name=author_name)
    db.session.add(new_article)
    db.session.commit()

    flash('Материал отправлен на модерацию' if status == 'pending' else 'Новая статья опубликована')

    return redirect(url_for('index'))


@app.route('/articles/<int:article_id>/edit')
@require_roles('moderator', 'admin')
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    return render_template('edit_article.html', article=article)


@app.route('/articles/<int:article_id>/update', methods=['POST'])
@require_roles('moderator', 'admin')
def update_article(article_id):
    article = Article.query.get_or_404(article_id)
    article.title = request.form['title']
    article.content = request.form['content']
    db.session.commit()
    flash('Changes are saved')
    return redirect(url_for('show_article', article_id=article.id))


@app.route('/articles/<int:article_id>')
def show_article(article_id):
    article = Article.query.get_or_404(article_id)
    if article.status != 'published' and (not g.current_user or g.current_user.role not in ('moderator', 'admin')):
        abort(404)
    return render_template('article_detail.html', article=article)


@app.route('/')
def index():
    query = Article.query.order_by(Article.id.desc())
    if not g.current_user or g.current_user.role == 'user':
        articles = query.filter_by(status='published').all()
    else:
        articles = query.all()
    pending = Article.query.filter_by(status='pending').order_by(Article.id.desc()).all() if g.current_user and g.current_user.role in ('moderator', 'admin') else []
    return render_template('index.html', articles=articles, pending_articles=pending)


@app.route('/contacts')
def contacts():
    contacts_data = [
        {
            "initials": "НК",
            "name": "Никита К.",
            "role": "Руководитель кружка",
            "about": "Куратор программы, встречи и стратегическое развитие.",
            "telegram": "#",
            "email": "nikita@example.com",
        },
        {
            "initials": "ЕМ",
            "name": "Екатерина М.",
            "role": "Методист",
            "about": "Помогает с конспектами, редактурой и практическими материалами.",
            "telegram": "#",
            "email": "kate@example.com",
        },
        {
            "initials": "АС",
            "name": "Алексей С.",
            "role": "Ментор по задачам",
            "about": "Разборы олимпиад, менторство и подготовка к интервью.",
            "telegram": "#",
            "email": "alex@example.com",
        },
        {
            "initials": "ВД",
            "name": "Влада Д.",
            "role": "Дизайн и контент",
            "about": "Визуал, UX и поддержка базы знаний в актуальном виде.",
            "telegram": "#",
            "email": "vlad@example.com",
        },
    ]
    return render_template('contacts.html', contacts=contacts_data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST' and request.form.get('login_method') == 'password':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = User.query.filter_by(provider='local', external_id=username).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            set_current_user(user)
            flash('Вы вошли по логину и паролю')
            return redirect(url_for('index'))

        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            if not user:
                user = User(
                    email=None,
                    name=username,
                    provider='local',
                    external_id=username,
                    role='admin',
                    password_hash=generate_password_hash(password)
                )
                db.session.add(user)
            else:
                user.role = 'admin'
                user.password_hash = generate_password_hash(password)
            db.session.commit()
            set_current_user(user)
            flash('Вы вошли как админ')
            return redirect(url_for('index'))

        error = 'Неверное имя пользователя или пароль'

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name = request.form.get('name', '').strip() or username
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not username or not password:
            error = 'Заполните все поля'
        elif password != confirm:
            error = 'Пароли не совпадают'
        elif User.query.filter_by(provider='local', external_id=username).first():
            error = 'Такой пользователь уже существует'
        else:
            user = User(
                name=name,
                provider='local',
                external_id=username,
                role='user',
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            set_current_user(user)
            flash('Регистрация прошла успешно')
            return redirect(url_for('index'))

    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Вы вышли из системы')
    return redirect(url_for('index'))


@app.route('/articles/<int:article_id>/publish', methods=['POST'])
@require_roles('moderator', 'admin')
def publish_article(article_id):
    article = Article.query.get_or_404(article_id)
    article.status = 'published'
    db.session.commit()
    flash('Статья опубликована')
    return redirect(url_for('show_article', article_id=article.id))


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    author_name = db.Column(db.String(200))

    def __repr__(self):
        return f'<Article {self.id} {self.title}>'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))
    name = db.Column(db.String(200))
    role = db.Column(db.String(20), default='user')
    provider = db.Column(db.String(50))
    external_id = db.Column(db.String(255))
    telegram_username = db.Column(db.String(200))
    password_hash = db.Column(db.String(255))

    def __repr__(self):
        return f'<User {self.id} {self.name}>'


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_schema()
    app.run(host="0.0.0.0", debug=True, port=8080)
