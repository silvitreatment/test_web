from flask import Flask , render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask import flash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///knowledge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
app.config['SECRET_KEY'] = 'SOME_SECRET_KEY'  
app.config['ADMIN_USERNAME'] = 'admin'
app.config['ADMIN_PASSWORD'] = 'password123'

db = SQLAlchemy(app)

@app.route('/articles/new')
def new_article():
    return render_template('new_article.html')

@app.route('/articles/<int:article_id>/delete', methods=['POST'])
def delete_article(article_id):
    if not session.get('logged_in'):
        abort(401)
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash('The article is deleted')
    return redirect(url_for('index'))

@app.route('/articles', methods=["POST"])
def create_article():
    if not session.get('logged_in'):
        abort(401)

    title = request.form['title']
    content = request.form['content']

    new_article = Article(title=title, content=content)
    db.session.add(new_article)
    db.session.commit()

    flash('New article successfully added')

    return redirect(url_for('index'))

@app.route('/articles/<int:article_id>/edit')
def edit_article(article_id):
    if not session.get('logged_in'):
        abort(401)
    article = Article.query.get_or_404(article_id)
    return render_template('edit_article.html', article=article)


@app.route('/articles/<int:article_id>/update', methods=['POST'])
def update_article(article_id):
    if not session.get('logged_in'):
        abort(401)
    article = Article.query.get_or_404(article_id)
    article.title = request.form['title']
    article.content = request.form['content']
    db.session.commit()
    flash('Changes are saved') 
    return redirect(url_for('show_article', article_id=article.id))

@app.route('/articles/<int:article_id>')
def show_article(article_id):
    article = Article.query.get_or_404(article_id)
    return render_template('article_detail.html', article=article)

@app.route('/')
def index():
    articles = Article.query.order_by(Article.id.desc()).all()  
    return render_template('index.html', articles=articles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username != app.config['ADMIN_USERNAME']:
            error = 'Неверное имя пользователя'
        elif password != app.config['ADMIN_PASSWORD']:
            error = 'Неверный пароль'
        else:
            session['logged_in'] = True
            flash('Вы успешно вошли в систему')  
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')

def logout():
    session.pop('logged_in', None)
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Article {self.id} {self.title}'
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True, port=8080)



