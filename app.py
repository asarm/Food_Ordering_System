from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "super secret key"

DATABASE = 'system_db.db'
with sqlite3.connect(DATABASE) as database:
    cursor = database.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,email TEXT,password TEXT,user_type INTEGER, address Text,"
                   " lat REAL , lng REAL, registred_date Date DEFAULT (datetime('now','localtime')))")

    cursor.execute("CREATE TABLE IF NOT EXISTS couriers(courier_id INTEGER PRIMARY KEY,name TEXT,is_available TEXT,lat REAL,lng REAL)")
    
    cursor.execute("CREATE TABLE IF NOT EXISTS foodOrder(id int PRIMARY KEY,content TEXT,orderDate datetime,userUserName varchar(30),courierID int)")

    cursor.execute("CREATE TABLE IF NOT EXISTS menuItem(id int PRIMARY KEY,ingridients varchar(200))")

    cursor.execute("CREATE TABLE IF NOT EXISTS needs(menuItemId int,orderId int,menuId int,PRIMARY KEY(menuItemID, orderId, menuId))")

    cursor.execute("CREATE TABLE IF NOT EXISTS consistsOf (orderId int,menuId int,PRIMARY KEY(orderId,menuId))")

    cursor.execute("CREATE TABLE IF NOT EXISTS menu(id int PRIMARY KEY,menuName varchar(30),restaurantId int)")

    cursor.execute("CREATE TABLE IF NOT EXISTS restaurant(id int PRIMARY KEY,restaurantName varchar(30),address varchar(250),isOpen binary,averageRating real)")

    cursor.execute("CREATE TABLE IF NOT EXISTS restaurant(id int PRIMARY KEY,restaurantName varchar(30),address varchar(250),isOpen binary,averageRating real)")

    cursor.execute("CREATE TABLE IF NOT EXISTS review(id int PRIMARY KEY,rating int,reviewDate datetime,restaurantId int,userUserName varchar(30))")

    cursor.execute("CREATE TABLE IF NOT EXISTS has(menuId int,menuitemId int,PRIMARY KEY(menuId, menuitemId))")


@app.route("/", methods=["GET","POST"])
def loginView():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        valid_password = ""

        cursor.execute("SELECT username,password,user_type FROM users WHERE email=(?)", (email,))
        query = cursor.fetchall()

        if len(query) == 0:
            print("user is not exists")
        else:
            username = query[0][0]
            valid_password = query[0][1]
            user_type = query[0][2]

        if password == valid_password:
            session["username"] = username
            session["user_type"] = user_type
            session["logged_in"] = True

            if user_type == 0:
                return redirect('home')
            elif user_type == 1:
                return render_template('adminHome.html', title='Home', username= session["username"])

    if not session.get('logged_in'):
        return render_template('login.html', title='Login')
    else:
        return redirect('home')

@app.route("/adminRegister", methods=["GET","POST"])
def adminRegisterView():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]
        coordinates = searchCoordinates(address)
        lat, lng = coordinates[0], coordinates[1]

        cursor.execute("INSERT INTO users(username,email,password,user_type, address, lat, lng) VALUES(?,?,?,?,?,?,?)",
                       (username, email, password, 1, address, lat, lng))
        database.commit()
        return redirect(url_for("loginView", title="Login"))

    return render_template('adminRegister.html', title='Admin Register')

@app.route("/register", methods=["GET","POST"])
def registerView():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]
        coordinates = searchCoordinates(address)
        lat, lng = coordinates[0], coordinates[1]

        cursor.execute("INSERT INTO users(username,email,password,user_type, address, lat, lng) VALUES(?,?,?,?,?,?,?)",
                       (username, email, password, 0, address, lat, lng))
        database.commit()
        return redirect(url_for("loginView", title="Login"))

    return render_template('register.html', title='Register')

@app.route("/home", methods=["GET","POST"])
def homeView():
    if not session.get('logged_in'):
        return render_template('login.html', title='Login')
    if session["user_type"] == 1:
        return render_template('adminHome.html', title='Admin Page', username=session["username"])
    if session["user_type"] == 0:
        return render_template('homePage.html', title='Home', username= session["username"])

@app.route("/addCourier", methods=["GET", "POST"])
def addCourier():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        coordinates = searchCoordinates(address)
        lat, lng = coordinates[0], coordinates[1]

        cursor.execute("INSERT INTO couriers(name,is_available,lat,lng) VALUES(?,?,?,?)",
                       (name, 1, lat, lng))
        database.commit()
        return redirect(url_for("homeView", title="Login"))

    return render_template('addCourier.html')

@app.route("/exit", methods=["GET"])
def exit():
    session["username"] = None
    session["logged_in"] = False
    session["user_type"] = None

    return redirect('/')


def searchCoordinates(address):
    address = address.replace(" ", "+")
    base_url = "http://py4e-data.dr-chuck.net/json?"

    resp = requests.get(
        base_url,
        params={"key": 42, "address": address}
    ).json()["results"][0]["geometry"]["location"]

    lat = resp["lat"]
    lng = resp["lng"]

    return lat, lng

if __name__ == '__main__':
    app.run(debug=True)
