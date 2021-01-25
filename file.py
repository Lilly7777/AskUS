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
import json
        

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///askus.db"
app.secret_key = "z7zNJscnjeprNqpEeBLXJTUnDkPL3y7P"

database = sql(app)

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

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        token = request.cookies.get('token')
        print("Token: ", token)
        return render_template('index.html')
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

        if passwd == conf_passwd:
            database.session.add(Member(uname=uname, email = email, passwd = passwd))
            database.session.commit()
            return redirect("/")
        else:
            flash("Password does not match")
            return redirect(url_for('register'))

if __name__ == '__main__':
    app.run(debug=True)

