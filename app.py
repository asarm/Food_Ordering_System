from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import requests
import pandas as pd

app = Flask(__name__)
app.secret_key = "super secret key"

DATABASE = 'system_db.db'

with sqlite3.connect(DATABASE) as database:
    cursor = database.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,email TEXT,password TEXT,user_type INTEGER, address Text,"
        " lat REAL , lng REAL, registred_date Date DEFAULT (datetime('now','localtime')))")

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS couriers(id INTEGER PRIMARY KEY,name TEXT,is_available TEXT,lat REAL,lng)")

    cursor.execute("CREATE TABLE IF NOT EXISTS foodOrder(id INTEGER PRIMARY KEY,content TEXT,orderDate datetime)")

    cursor.execute("CREATE TABLE IF NOT EXISTS menuItem(id INTEGER PRIMARY KEY,ingridients varchar(200))")

    cursor.execute("CREATE TABLE IF NOT EXISTS menu(id INTEGER PRIMARY KEY,menuName varchar(30))")

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS restaurant(id INTEGER PRIMARY KEY, restaurantName varchar(30),address varchar(250),lat Text,lng Text,isOpen binary,averageRating REAL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS review(id INTEGER PRIMARY KEY,rating INTEGER,reviewDate datetime)")

    cursor.execute("CREATE TABLE IF NOT EXISTS consistsOf (orderId INTEGER,menuId int,PRIMARY KEY(orderId,menuId),"
                   "FOREIGN KEY (orderId) REFERENCES foodOrder(id),FOREIGN KEY (menuId) REFERENCES menu(id) ON UPDATE CASCADE)")

    cursor.execute("CREATE TABLE IF NOT EXISTS has(menuId INTEGER,menuitemId INTEGER,PRIMARY KEY(menuId, menuItemId),"
                   "FOREIGN KEY (menuId) REFERENCES menu(id) ON UPDATE CASCADE,"
                   "FOREIGN KEY (menuitemId) REFERENCES menuItem(id) ON UPDATE CASCADE)")

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS needs(menuItemId INTEGER,orderId INTEGER,menuId INTEGER,PRIMARY KEY(menuItemID, orderId, menuId),"
        "FOREIGN KEY (menuItemId) REFERENCES menuItem(id) ON UPDATE CASCADE,"
        "FOREIGN KEY (orderId) REFERENCES menu(id),FOREIGN KEY (menuId) REFERENCES consistsof(menuId) ON UPDATE CASCADE)")
    try:  ##Without try-catch, throws a duplicate error.
        ## Foreign keys
        script = ("ALTER TABLE foodOrder ADD COLUMN courierID int REFERENCES couriers(id) ON UPDATE CASCADE;"
                  "ALTER TABLE foodOrder ADD COLUMN userUserName varchar(30) REFERENCES users(username) ON UPDATE CASCADE;"
                  "ALTER TABLE couriers ADD COLUMN orderId int REFERENCES foodOrder(id) ON UPDATE CASCADE;"
                  "ALTER TABLE review ADD COLUMN restaurantId int REFERENCES restaurant(id) ON UPDATE CASCADE;"
                  "ALTER TABLE review ADD COLUMN userUserName int REFERENCES users(username) ON UPDATE CASCADE;"
                  "ALTER TABLE menu ADD COLUMN restaurantId int REFERENCES restaurant(id) ON UPDATE CASCADE;")
        cursor.executescript(script)
    except:
        pass


@app.route("/", methods=["GET", "POST"])
def loginView():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        username, user_type, address, lat, lng, valid_password = "", "", "", "", "", ""

        cursor.execute("SELECT username,password,user_type, address, lat, lng FROM users WHERE email=(?)", (email,))
        query = cursor.fetchall()

        if len(query) == 0:
            print("user does not exists")
        else:
            username = query[0][0]
            valid_password = query[0][1]
            user_type = query[0][2]
            address = query[0][3]
            lat = query[0][4]
            lng = query[0][5]

        if password == valid_password:
            updateUserInfo(username, user_type, email, password, address, lat, lng)

            if user_type == 0:
                return redirect('home')
            elif user_type == 1:
                return redirect('home')

    if not session.get('logged_in'):
        return render_template('auth/login.html', title='Login')
    else:
        return redirect('home')


@app.route("/adminRegister", methods=["GET", "POST"])
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
                       (username, email, password, 1, address.lower(), lat, lng))
        database.commit()
        return redirect(url_for("loginView", title="Login"))

    return render_template('auth/adminRegister.html', title='Admin Register')


@app.route("/register", methods=["GET", "POST"])
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
                       (username, email, password, 0, address.lower(), lat, lng))
        database.commit()
        return redirect(url_for("loginView", title="Login"))

    return render_template('auth/register.html', title='Register')


@app.route("/home", methods=["GET", "POST"])
def homeView():
    if not session.get('logged_in'):
        return render_template('auth/login.html', title='Login')
    if session["user_type"] == 1:
        data = getAllDbData(toGet=["users", "restaurant", "couriers"], limit=4)
        session["isFiltered"], session["filteredData"] = False, {}

        return render_template('admin/adminHome.html', title='Admin Page', username=session["username"], data=data)
    else:
        return render_template('user/homePage.html', title='Home', username=session["username"])


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

    return render_template('admin/insert_operations/addCourier.html', username=session["username"])


@app.route("/userSettings", methods=["GET", "POST"])
def userSettings():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    cursor.execute("SELECT username, email, password, address, lat, lng FROM users")

    oldUsername = session['username']
    oldEmail = session['email']
    oldPassword = session['password']
    oldAddress = session['address']

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]

        if address != oldAddress:
            coordinates = searchCoordinates(address)
            lat, lng = coordinates[0], coordinates[1]
            cursor.execute("UPDATE users SET username=?,email=?,password=?,address=?,lat=?,lng=?"
                           " WHERE username =(?)", (name, email, password, address, lat, lng, oldUsername,))
        else:
            cursor.execute("UPDATE users SET username=?,email=?,password=?,address=?"
                           " WHERE username =(?)", (name, email, password, address, oldUsername,))

        database.commit()

        updateUserInfo(name, 0, email, password, address)
        return redirect(url_for("homeView", title="Home"))

    return render_template('user/userSettings.html', username=oldUsername, address=oldAddress, email=oldEmail,
                           password=oldPassword)


@app.route("/addRestaurant", methods=["GET", "POST"])
def addRestaurant():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        coordinates = searchCoordinates(address)
        lat, lng = coordinates[0], coordinates[1]

        cursor.execute(
            "INSERT INTO restaurant(restaurantName, address, lat, lng, isOpen, averageRating) VALUES(?, ?, ?, ?, ?, ?)",
            (name, address, lat, lng, 1, 0.0))
        database.commit()
        return redirect(url_for("homeView", title="Login"))

    return render_template('admin/insert_operations/addRestaurant.html', username=session["username"])


@app.route("/addUser", methods=["GET", "POST"])
def addUser():
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

    return render_template('admin/insert_operations/addUser.html', title='Register', username=session["username"])

@app.route("/users", methods=["GET", "POST"])
def allUsers():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy'].lower()

            if session["isFiltered"] == False:
                command = "SELECT username,email,address,registred_date,user_type as type FROM users ORDER BY "+str(orderBy)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["users"] = query
            else:
                df = pd.DataFrame(session["filteredData"]["users"],
                                  columns=['username', 'email','address','registred_date','type'])
                df = df.sort_values(by=orderBy)
                session["filteredData"]["users"] = df.values.tolist()

        if 'filter' in request.form:
            filtered_cols, expected_vals = [], []
            q = ""

            for c in request.form.keys():
                if request.form[c] != '' and request.form[c] != "filter":
                    if request.form[c] == "on":
                        filtered_cols.append("user_type")
                        expected_vals.append(1)
                    else:
                        filtered_cols.append(c)
                        expected_vals.append(request.form[c])

            if len(expected_vals) > 0:
                if filtered_cols[0] != "user_type":
                    q += filtered_cols[0]+" LIKE "+f"'%{expected_vals[0]}%'"
                else:
                    q += " user_type = 1"

                if len(expected_vals) > 1:
                    for index in range(1, len(expected_vals)):
                        if filtered_cols[index] != "user_type":
                            q += " and " + filtered_cols[index]+" LIKE " + f"'%{expected_vals[index]}%'"
                    if filtered_cols.count("user_type") > 0:
                        q += " and user_type = 1"

                command = "SELECT username,email,address,registred_date,user_type as type FROM users WHERE "+q
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["users"] = query
            else:
                session["filteredData"] = getAllDbData(toGet=["users"])
            session["isFiltered"] = True

    else:
        session["filteredData"] = getAllDbData(toGet=["users"])
        session["isFiltered"] = False

    return render_template("admin/list_operations/list_users.html", username=session["username"], data=session["filteredData"])

@app.route("/restaurants", methods=["GET", "POST"])
def allRestaurants():
    data = {}
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy'].lower()
            print(orderBy)
            command = "SELECT restaurantName as Name, address, averageRating as Rating, isOpen as open FROM restaurant ORDER BY "+str(orderBy)
            cursor.execute(command)
            query = cursor.fetchall()
            data["restaurant"] = query

        if 'filter' in request.form:
            filtered_cols, expected_vals = [], []
            q = ""

            for c in request.form.keys():
                if request.form[c] != '' and request.form[c] != "filter":
                    if request.form[c] == "on":
                        filtered_cols.append("isOpen")
                        expected_vals.append(1)
                    else:
                        filtered_cols.append(c)
                        expected_vals.append(request.form[c])

            print(expected_vals)
            print(filtered_cols)

            if len(expected_vals) > 0:
                if filtered_cols[0] != "isOpen":
                    q += filtered_cols[0]+" LIKE "+f"'%{expected_vals[0]}%'"
                else:
                    q += " isOpen = 1"

                if len(expected_vals) > 1:
                    for index in range(1, len(expected_vals)):
                        if filtered_cols[index] != "isOpen":
                            q += " and " + filtered_cols[index]+" LIKE " + f"'%{expected_vals[index]}%'"
                    if filtered_cols.count("isOpen") > 0:
                        q += " and isOpen = 1"

                command = "SELECT restaurantName as Name, address, averageRating as Rating, isOpen as open FROM restaurant WHERE "+q
                print(command)
                cursor.execute(command)
                query = cursor.fetchall()
                data["restaurant"] = query
            else:
                data = getAllDbData(toGet=["restaurant"])
    else:
        data = getAllDbData(toGet=["restaurant"])

    return render_template("admin/list_operations/list_restaurants.html", username=session["username"], data=data)

@app.route("/couriers", methods=["GET", "POST"])
def allCouriers():
    data = {}
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy']
            command = "SELECT id as Number, name as Name, is_available as Availability FROM couriers ORDER BY "+str(orderBy)
            print(command)
            cursor.execute(command)
            query = cursor.fetchall()
            data["couriers"] = query
            
        if 'filter' in request.form:
            filtered_cols, expected_vals = [], []
            q = ""

            for c in request.form.keys():
                if request.form[c] != '' and request.form[c] != "filter":
                    if request.form[c] == "on":
                        filtered_cols.append("is_available")
                        expected_vals.append(1)
                    else:
                        filtered_cols.append(c)
                        expected_vals.append(request.form[c])

            print(expected_vals)
            print(filtered_cols)

            if len(expected_vals) > 0:
                if filtered_cols[0] != "is_available":
                    q += filtered_cols[0]+" LIKE "+f"'%{expected_vals[0]}%'"
                else:
                    q += " is_available = 1"

                if len(expected_vals) > 1:
                    for index in range(1, len(expected_vals)):
                        if filtered_cols[index] != "is_available":
                            q += " and " + filtered_cols[index]+" LIKE " + f"'%{expected_vals[index]}%'"
                    if filtered_cols.count("is_available") > 0:
                        q += " and is_available = 1"

                command = "SELECT id as Number, name as Name, is_available as Availability FROM couriers WHERE "+q
                cursor.execute(command)
                query = cursor.fetchall()
                data["couriers"] = query
            else:
                data = getAllDbData(toGet=["couriers"])
    else:
        data = getAllDbData(toGet=["couriers"])

    return render_template("admin/list_operations/list_couriers.html", username=session["username"], data=data)


@app.route("/selectRestaurant", methods=["GET", "POST"])
def selectRestaurant():
    data = {}
    query = getAllDbData(toGet=["restaurant"])
    data = query
    return render_template('user/selectRestaurant.html', title='Restaurants', username=session["username"], data=data)

@app.route("/selectMenu", methods=["GET", "POST"])
def selectMenu():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        selectedRestaurantId = request.form["selectedRestaurant"]
        command = "SELECT id,menuName,restaurantId FROM menu WHERE restaurantId="+selectedRestaurantId
        cursor.execute(command)
        query = cursor.fetchall()
        print(selectedRestaurantId)
        print(query)

    return render_template('user/selectMenu.html', title='Menus', username=session["username"],)

@app.route("/exit", methods=["GET"])
def exit():
    session["username"] = None
    session["logged_in"] = False
    session["user_type"] = None

    return redirect('/')


def updateUserInfo(username, user_type, email, password, address, lat=None, lng=None):
    session["username"] = username
    session["user_type"] = user_type
    session["email"] = email
    session["password"] = password
    session["address"] = address
    if lat != None and lng != None:
        session["lat"] = lat
        session["lng"] = lng
    session["logged_in"] = True


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


def getUsers(cursor, limit=None):
    if limit != None:
        cursor.execute(
            "SELECT username,email,address,registred_date,user_type FROM users ORDER BY registred_date desc LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT username,email,address,registred_date,user_type FROM users ORDER BY registred_date desc")
    query = cursor.fetchall()

    return query


def getCouriers(cursor, limit=None):
    cursor.execute("SELECT id,name, is_available,lat,lng,orderId FROM couriers ORDER BY id desc")
    query = cursor.fetchall()

    return query


def getRestaurants(cursor, limit=None):
    cursor.execute("SELECT restaurantName,address,isOpen,averageRating,id FROM restaurant ORDER BY id desc")
    query = cursor.fetchall()

    return query


def getAllDbData(toGet, limit=None):
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    data = {}
    for entity in toGet:
        if entity == "couriers":
            data[entity] = getCouriers(cursor, limit)
        if entity == "users":
            data[entity] = getUsers(cursor, limit)
        if entity == "restaurant":
            data[entity] = getRestaurants(cursor, limit)
        else:
            pass
    return data


if __name__ == '__main__':
    app.run(debug=True)
