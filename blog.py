from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

class RegisterForm(Form):
    name = StringField("İsim Soyisim: ", validators=[validators.Length(min = 4, max = 25)])
    username = StringField("Kullanıcı Adı: ", validators=[validators.Length(min = 4, max = 25)])
    password = PasswordField("Şifre: ", validators=[validators.EqualTo(fieldname = "confirm", message = "Şifreniz uyuşmuyuyor.")])
    confirm = PasswordField("Şifre Doğrulama: ")
    email = StringField("E-Mail: ", validators=[validators.Length(min = 4, max = 40), validators.Email(message = "Lütfen geçerli bir mail adresi giriniz.")])

class LoginForm(Form):
    username = StringField("Kullanıcı Adı: ", validators=[validators.Length(min = 4, max = 25)])
    password = PasswordField("Şifre: ",)

class ArticleForm(Form):
    title = StringField("Başlık: ", validators=[validators.Length(min = 5, max = 30)])
    content = TextAreaField("İçerik: ", validators=[validators.Length(min = 10)])
    

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapmalısınız!", category="danger")
            return redirect(url_for("login"))
    return decorated_function

app = Flask(__name__)
app.secret_key="jblog"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "jblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/mixes")
def mixes():
    return render_template("mixes.html")

@app.route("/mixes/<string:id>")
def mixes_dynamic(id):
    return render_template("mixes.html") + "Article ID" + id

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles"
    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

@app.route("/articles/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(query, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        password = sha256_crypt.encrypt(form.password.data)
        email = form.email.data

        cursor = mysql.connection.cursor()
        query = "INSERT INTO users (name, email, username, passwd) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla kayıt olundu!", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)

@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data
        
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(query, (username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["passwd"]
            if sha256_crypt.verify(password, real_password):
                flash("Giriş başarılı, hoşgeldiniz!", category="success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Girilen kullanıcı adı veya şifre hatalı, lütfen tekrar denein.", category="danger")
                return redirect(url_for("login"))
        else:
            flash("Girilen kullanıcı adı veya şifre hatalı, lütfen tekrar deneyin.", category="danger")
            return redirect(url_for("login"))

    return render_template("login.html", form = form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(query, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE author = %s AND id = %s"
        result = cursor.execute(query, (session["username"], id))
        
        if result > 0:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
        else:
            flash("Böyle bir yazı yok veya bu yazıyı güncelleme yetkiniz yok.", category="danger")
            return redirect(url_for("dashboard"))
    else:
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        query = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor.execute(query, (newTitle, newContent, id))
        mysql.connection.commit()

        flash("Yazı güncellendi.", category="success")
        return redirect(url_for("dashboard"))


@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s AND id = %s"
    result = cursor.execute(query, (session["username"], id))

    if result > 0:
        query2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(query2, (id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir yazı yok veya bu yazıyı silme yetkiniz yok.", category="danger")
        return redirect(url_for("dashboard"))

@app.route("/addarticle", methods = ["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(title, content, author) VALUES(%s, %s, %s)"
        cursor.execute(query, (title, content, session["username"]))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi!", category="success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form = form)
        
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "POST":
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
        result = cursor.execute(query)

        if result > 0:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)
        else:
            flash("Böyle bir makale bulunmamaktadır." + keyword, category="warning")
            return redirect(url_for("articles"))
    else:
        return redirect(url_for("index"))

if __name__ == "__main__":

    app.run(debug = True)