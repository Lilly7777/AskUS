from flask import Flask
from flask import render_template
from flask import request
from flask import flash
from flask import url_for
from flask import jsonify
from hashlib import sha256
from flask import redirect
from flask_sqlalchemy import SQLAlchemy as sql
from itsdangerous import TimedJSONWebSignatureSerializer
from itsdangerous import BadSignature
from itsdangerous import SignatureExpired
from functools import wraps
from datetime import datetime
import json
import re
        

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///askus.db"
app.secret_key = "z7zNJscnjeprNqpEeBLXJTUnDkPL3y7P"

database = sql(app)

regexem = '^[a-z0-9]+?[\._]?[a-z0-9]+[@]\w+[.]\w+$'
regexpw = '^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,}$'

def checkemail(email):
    if (re.search(regexem, email)):
        return 1
    else:
        return 0

def checkpass(password):
    if (re.search(regexpw, password)):
        return 1
    else:
        return 0
 

class Member(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    uname = database.Column(database.String, nullable = False)
    email = database.Column(database.String, nullable = False)
    passwd = database.Column(database.String, nullable = False)

    def __init__(self, **kwargs):
        if 'passwd' in kwargs:
            kwargs['passwd'] = Member.hash(kwargs['passwd'])
        super(Member, self).__init__(**kwargs)

    @staticmethod
    def hash(passwd):
        return sha256(passwd.encode('utf-8')).hexdigest()

    def verify_passwd(self, passwd):
        if self.passwd == Member.hash(passwd):
            return True
        else:
            return False

    def gen_token(self):
        ser = TimedJSONWebSignatureSerializer(app.secret_key, expires_in=3600)
        return ser.dumps({'uname': self.uname})
    
    @staticmethod
    def find_by_token(token):
        if not token:
            return None

        try:
            ser = TimedJSONWebSignatureSerializer(app.secret_key)
            payload = ser.loads(token)
            return Member.query.filter_by(uname=payload.get('uname')).first()
        except SignatureExpired:
            return None


class Category(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    title = database.Column(database.String, nullable = False)
    desc = database.Column(database.String, nullable = False)
    
class Post(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    title = database.Column(database.String, nullable = False)
    uname = database.Column(database.String, nullable = False)
    content = database.Column(database.String, nullable = False)
    timestamp = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    category_id = database.Column(database.Integer, database.ForeignKey(Category.id), nullable=False)

def verify_token(token):
    ser = TimedJSONWebSignatureSerializer(app.secret_key)
    try:
        ser.loads(token)
    except SignatureExpired:
        return False
    except BadSignature:
        return False
    return True

def stop_logged_users(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('token')
        if token != None and verify_token(token):
            flash('You\'re already logged in.')
            return redirect('/')
        return func(*args, **kwargs)
    return wrapper

def require_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('token')
        if not token or not verify_token(token):
            flash('You have to be logged in to access this page')
            return redirect('/login')
        return func(*args, **kwargs)
    return wrapper

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        isLogged = False
        token = request.cookies.get('token')
        if token != None and token != "":
            isLogged = True
        categories = Category.query.all()
        return render_template('index.html', isLogged = isLogged, categories= categories)
    if request.method == 'POST':
        pass


@app.route("/login", methods=['GET', 'POST'])
@stop_logged_users
def login():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == 'POST':
        data = json.loads(request.data.decode('ascii'))
        uname = data['inputUname']
        passwd = data['inputPasswd']
        member = Member.query.filter_by(uname=uname).first()
        if member != None and member.verify_passwd(passwd):
            return jsonify({'token': member.gen_token().decode('ascii')})
        else:
            flash("Incorrect username or password!")
            return jsonify({'token': None})

@app.route("/register", methods=['GET', 'POST'])
@stop_logged_users
def register():
    if request.method == 'GET':
        return render_template('register.html')
    if request.method == 'POST':
        uname = request.form['inputUname']
        email = request.form['inputEmail']
        passwd = request.form['inputPasswd']
        conf_passwd = request.form['inputConf_Passwd']

        validemail = checkemail(email)
        validpw = checkpass(passwd) 
        if validemail == 0:
            flash("Please enter a valid email!")
            return redirect(url_for('register'))
        elif validpw == 0:
            flash("Password must contain at least eight characters, one uppercase letter, one lowercase letter and one number!")
            return redirect(url_for('register'))
        elif passwd != conf_passwd:
            flash("Passwords do not match!")
            return redirect(url_for('register'))
        else:
            database.session.add(Member(uname=uname, email = email, passwd = passwd))
            database.session.commit()
            return redirect("/")



@app.route("/add-category", methods=['GET', 'POST'])
@require_login
def add_category():
    if request.method =='GET':
        return render_template('add-category.html') #TODO
    if request.method == 'POST':
        title = request.form['inputTitle']
        desc = request.form['inputDesc']
        if not Category.query.filter_by(title=title).first():
            database.session.add(Category(title=title, desc=desc))
            database.session.commit()
        else:
            flash("A category with this title already exists.")
            return redirect(url_for('add_category'))
        return redirect('/')

@app.route("/category/<category_id>", methods=['GET', 'POST'])
def category_page(category_id):
    isLogged = False
    token = request.cookies.get('token')
    if token != None and token != "":
        isLogged = True
    posts = Post.query.filter_by(category_id=category_id)
    token = request.cookies.get('token')
    uname = ""
    if Member.find_by_token(token):
        uname = Member.find_by_token(token).uname
    return render_template('category.html', category_id=category_id, posts=posts, uname=uname, isLogged = isLogged)

@app.route("/category/<category_id>/add-post", methods=['GET', 'POST'])
def add_post(category_id):
    if request.method =='GET':
        return render_template('add-post.html', category_id=category_id) #TODO
    if request.method == 'POST':
        title = request.form['inputTitle']
        content = request.form['inputContent']
        token = request.cookies.get('token')
        uname = Member.find_by_token(token).uname

        database.session.add(Post(title=title, content=content, uname=uname, category_id=category_id))
        database.session.commit()
        
        return redirect(('/category/' + str(category_id))) 


if __name__ == '__main__':
    app.run(debug=True)

