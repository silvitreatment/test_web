from flask import Flask , render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/articles/new')
def new_article():
    return render_template('new_arcticle.html')

@app.route('/articles', methods=["POST"])
def create_article():
    title = request.form['title']
    content = request.form['content']


    return redirect(url_for('index'))

@app.route('/articles/<int:article_id/edit>')
def edit_article(article_id):
    return render_template('edit_article.html', article=None)

@app.route("/")
def index():
    return 'Hello world!'

@app.route('/articles/<int:article_id>/update', method=['POST'])
def update_article(article_id):
    title = request.form['title']
    content = request.form['content']

    return redirect(url_for('show_article', article_id=article_id))

@app.route('/articles/<int:article_id>')
def show_article(article_id):
    return render_template('article_detail.html', article=True)
