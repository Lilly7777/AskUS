from flask import Flask
from flask import render_template
from flask import request
from flask import flash
from hashlib import sha256
from flask import redirect
from flask_sqlalchemy import SQLAlchemy as sql

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///askus.db" #TODO Ignore

database = sql(app)

class Member(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    uname = database.Column(database.String, nullable = False)
    email = database.Column(database.String, nullable = False)
    passwd = database.Column(database.String, nullable = False)

    @staticmethod
    def hash(passwd):
        return sha256(passwd.encode('utf-8')).hexdigest()

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == 'POST':
        pass 
        # TODO


@app.route("/login")
def login():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == 'POST':
        uname = request.form['inputUname']
        passwd = request.form['inputPasswd']
        #TODO token

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    if request.method == 'POST':
        uname = request.form['inputUname']
        email = request.form['inputEmail']
        passwd = request.form['inputPasswd']
        conf_passwd = request.form['inputConf_Passwd']

        if passwd == conf_passwd:
            database.session.add(Member(uname=uname, email = email, passwd = Member.hash(passwd)))
            database.session.commit()
            return redirect("/")
        else:
            flash("Password does not match")
        #TODO token

if __name__ == '__main__':
    app.run(debug=True)

