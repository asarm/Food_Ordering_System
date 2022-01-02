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

    cursor.execute("CREATE TABLE IF NOT EXISTS extra(id INTEGER PRIMARY KEY,name varchar(200), price REAL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS menu(id INTEGER PRIMARY KEY,menuName varchar(30), price REAL, content TEXT)")

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS restaurant(id INTEGER PRIMARY KEY, restaurantName varchar(30),address varchar(250),lat Text,lng Text,isOpen binary,averageRating REAL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS foodOrder(id INTEGER PRIMARY KEY,content TEXT,orderDate Date DEFAULT (datetime('now','localtime')),totalPrice REAL, is_delivered INTEGER DEFAULT(0), is_reviewed INTEGER DEFAULT(0), restaurantId INTEGER, FOREIGN KEY(restaurantId) REFERENCES restaurant(id))")

    
    cursor.execute("CREATE TABLE IF NOT EXISTS review(id INTEGER PRIMARY KEY,rating INTEGER,reviewDate DEFAULT (datetime('now','localtime')))")
    
    '''
    cursor.execute("CREATE TABLE IF NOT EXISTS consistsOf (orderId INTEGER,menuId int,PRIMARY KEY(orderId,menuId),"
                   "FOREIGN KEY (orderId) REFERENCES foodOrder(id),FOREIGN KEY (menuId) REFERENCES menu(id) ON UPDATE CASCADE)")

    cursor.execute("CREATE TABLE IF NOT EXISTS has(menuId INTEGER,menuitemId INTEGER,PRIMARY KEY(menuId, menuItemId),"
                   "FOREIGN KEY (menuId) REFERENCES menu(id) ON UPDATE CASCADE,"
                   "FOREIGN KEY (menuitemId) REFERENCES menuItem(id) ON UPDATE CASCADE)")
    
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS needs(menuItemId INTEGER,orderId INTEGER,menuId INTEGER,PRIMARY KEY(menuItemID, orderId, menuId),"
        "FOREIGN KEY (menuItemId) REFERENCES menuItem(id) ON UPDATE CASCADE,"
        "FOREIGN KEY (orderId) REFERENCES menu(id),FOREIGN KEY (menuId) REFERENCES consistsof(menuId) ON UPDATE CASCADE)")
    '''

    try:
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
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        confirmedOrderId = request.form["confirmedOrder"]

        cursor.execute("UPDATE couriers SET is_available = 1, orderId = NULL, "
                       "lat = (SELECT users.lat FROM users, foodOrder WHERE users.username = foodOrder.userUserName and foodOrder.id = (?)),"
                       "lng = (SELECT users.lng FROM users, foodOrder WHERE users.username = foodOrder.userUserName and foodOrder.id = (?))"
                       "WHERE id = (SELECT id FROM couriers WHERE couriers.orderId=(?))", (confirmedOrderId,confirmedOrderId,confirmedOrderId))
        cursor.execute("UPDATE foodOrder SET is_delivered = 1 WHERE foodOrder.id=(?)", (confirmedOrderId,))
        database.commit()

    if not session.get('logged_in'):
        return render_template('auth/login.html', title='Login')
    if session["user_type"] == 1:
        data = getAllDbData(toGet=["users", "restaurant", "couriers", "menu", "restaurantName","orders"], limit=5)
        session["isFiltered"], session["filteredData"] = False, {}

        return render_template('admin/adminHome.html', title='Admin Page', username=session["username"], data=data)
    else:
        data = getUserViewData()
        return render_template('user/homePage.html', title='Home', username=session["username"], data=data)


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

@app.route("/addMenu", methods=["GET", "POST"])
def addMenu():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        menuName = request.form["Menu"]
        restaurantName = request.form["Restaurant"]
        price = request.form["Price"]
        content = request.form["Content"]

        cursor.execute("INSERT INTO menu(menuName, price, content, restaurantId) VALUES(?, ?, ?, (SELECT id FROM restaurant WHERE restaurantName = (?)))",
                       (menuName, price, content, restaurantName))
        database.commit()
        return redirect(url_for("loginView", title="Home"))

    return render_template('admin/insert_operations/addMenu.html', title='Register', username=session["username"])

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
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy'].lower()

            if session["isFiltered"] == False:
                command = "SELECT restaurantName as Name, address as Address, isOpen as Open, averageRating as Rating FROM restaurant ORDER BY "+str(orderBy)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["restaurant"] = query
            else:
                df = pd.DataFrame(session["filteredData"]["restaurant"],
                                  columns=['name', 'address','open','rating'])
                df = df.sort_values(by=orderBy)
                session["filteredData"]["restaurant"] = df.values.tolist()

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

                command = "SELECT restaurantName as Name, address as Address, isOpen as Open, averageRating as Rating FROM restaurant WHERE "+q
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["restaurant"] = query
            else:
                session["filteredData"] = getAllDbData(toGet=["restaurant"])
            session["isFiltered"] = True

    else:
        session["filteredData"] = getAllDbData(toGet=["restaurant"])
        session["isFiltered"] = False

    return render_template("admin/list_operations/list_restaurants.html", username=session["username"], data=session["filteredData"])

@app.route("/couriers", methods=["GET", "POST"])
def allCouriers():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy'].lower()

            if session["isFiltered"] == False:
                command = "SELECT id as Number, name as Name, is_available as Availability FROM couriers ORDER BY "+str(orderBy)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["users"] = query
            else:
                df = pd.DataFrame(session["filteredData"]["couriers"],
                                  columns=['number', 'name','availability'])
                df = df.sort_values(by=orderBy)
                session["filteredData"]["couriers"] = df.values.tolist()

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
                session["filteredData"]["couriers"] = query
            else:
                session["filteredData"] = getAllDbData(toGet=["couriers"])
            session["isFiltered"] = True

    else:
        session["filteredData"] = getAllDbData(toGet=["couriers"])
        session["isFiltered"] = False

    return render_template("admin/list_operations/list_couriers.html", username=session["username"], data=session["filteredData"])

@app.route("/menus", methods=["GET", "POST"])
def allMenus():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy']

            if session["isFiltered"] == False:
                command = "SELECT menu.id, menuName, price, content, restaurant.restaurantName " \
                          " FROM menu INNER JOIN restaurant ON menu.restaurantId = restaurant.id ORDER BY "+orderBy+" desc "
                print(command)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["menu"] = query
            else:
                df = pd.DataFrame(session["filteredData"]["menu"],
                                  columns=['id','menuName', 'price','content', 'restaurantName'])
                df = df.sort_values(by=orderBy)
                session["filteredData"]["menu"] = df.values.tolist()

        if 'filter' in request.form:
            filtered_cols, expected_vals = [], []
            q = ""

            for c in request.form.keys():
                if request.form[c] != '' and request.form[c] != "filter":
                    filtered_cols.append(c)
                    expected_vals.append(request.form[c])

            if len(expected_vals) > 0:
                for index in range(0, len(expected_vals)):
                    q += filtered_cols[index]+" LIKE " + f"'%{expected_vals[index]}%'"


                command = "SELECT menu.id, menuName, price, content, restaurant.restaurantName " \
                          " FROM menu INNER JOIN restaurant ON menu.restaurantId = restaurant.id and "+q+" ORDER BY menu.id desc "
                print("Command", command)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["menu"] = query
            else:
                session["filteredData"] = getAllDbData(toGet=["menu"])
            session["isFiltered"] = True

    else:
        session["filteredData"] = getAllDbData(toGet=["menu"])
        session["isFiltered"] = False

    return render_template("admin/list_operations/list_menus.html", username=session["username"], data=session["filteredData"])

@app.route("/orders", methods=["GET", "POST"])
def allOrders():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    if request.method == "POST":
        if 'order' in request.form:
            orderBy = request.form['orderBy']

            if session["isFiltered"] == False:
                "SELECT foodOrder.id, content, orderDate, totalPrice, is_delivered,  userUserName, "
                "FROM foodOrder INNER JOIN couriers ON foodOrder.courierID = couriers.id INNER JOIN restaurant ON foodOrder.restaurantId = restaurant.id"
                command = "SELECT foodOrder.id,content,orderDate,totalPrice,is_delivered,couriers.name as courier_name, userUserName, " \
                          "restaurant.restaurantName as restaurant_name" \
                          " FROM foodOrder INNER JOIN couriers ON foodOrder.courierID = couriers.id INNER JOIN restaurant ON foodOrder.restaurantId = restaurant.id" \
                          " ORDER BY "+str(orderBy)
                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["orders"] = query
            else:
                df = pd.DataFrame(session["filteredData"]["orders"],
                                  columns=['id','content', 'orderDate','totalPrice','is_delivered','courier_name','userUserName', 'restaurant_name'])
                df = df.sort_values(by=orderBy)
                session["filteredData"]["orders"] = df.values.tolist()

        if 'filter' in request.form:
            filtered_cols, expected_vals = [], []
            q = ""

            for c in request.form.keys():
                if request.form[c] != '' and request.form[c] != "filter":
                    if request.form[c] == "on":
                        filtered_cols.append("is_delivered")
                        expected_vals.append(1)
                    else:
                        filtered_cols.append(c)
                        expected_vals.append(request.form[c])

            if len(expected_vals) > 0:
                if filtered_cols[0] != "is_delivered" and filtered_cols[0] != "maxprice" and filtered_cols[0] != "minprice":
                    q += filtered_cols[0]+" LIKE "+f"'%{expected_vals[0]}%'"
                else:
                    q += " is_delivered = 1 "

                if len(expected_vals) > 1:
                    for index in range(1, len(expected_vals)):
                        if filtered_cols[index] != "is_delivered":
                            q += " and " + filtered_cols[index]+" LIKE " + f"'%{expected_vals[index]}%'"
                    if filtered_cols.count("is_delivered") > 0:
                        q += " and is_delivered = 1 "

                command = "SELECT foodOrder.id,content,orderDate,totalPrice,is_delivered,couriers.name as courier_name, userUserName, restaurant.restaurantName as restaurant_name " \
                          "FROM foodOrder INNER JOIN couriers ON foodOrder.courierID = couriers.id INNER JOIN restaurant ON foodOrder.restaurantId = restaurant.id " \
                          "and " + q + "ORDER BY foodOrder.id"

                cursor.execute(command)
                query = cursor.fetchall()
                session["filteredData"]["orders"] = query
            else:
                session["filteredData"] = getAllDbData(toGet=["orders"])
                print(session["filteredData"])
            session["isFiltered"] = True

    else:
        session["filteredData"] = getAllDbData(toGet=["orders"])
        session["isFiltered"] = False

    return render_template("admin/list_operations/list_orders.html", username=session["username"],
                           data=session["filteredData"])

@app.route("/selectRestaurant", methods=["GET", "POST"])
def selectRestaurant():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    query = getAllDbData(toGet=["restaurant"])
    data = query
    session["menus"] = []

    toReview = canReview(cursor)

    return render_template('user/selectRestaurant.html', title='Restaurants', username=session["username"], data=data, toReview=toReview)

@app.route("/selectMenu", methods=["GET", "POST"])
def selectMenu():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    command = "SELECT id,name,price FROM extra"
    cursor.execute(command)
    query = cursor.fetchall()
    session["extras"] = query

    if request.method == "POST":
        print(request.form)
        if "selectedRestaurant" in request.form.keys():
            selectedRestaurantId = request.form["selectedRestaurant"]

            command = "SELECT id,menuName,restaurantId,price,content FROM menu WHERE restaurantId="+selectedRestaurantId
            cursor.execute(command)
            query = cursor.fetchall()
            print(selectedRestaurantId)
            session["menus"] = query

        if "selectedMenu" in request.form.keys():
            selected = int(request.form["selectedMenu"])
            command = "SELECT restaurantId FROM menu WHERE id=" + str(f"'{selected}'")
            cursor.execute(command)
            selectedRestaurantId = cursor.fetchall()[0][0]
            command = "SELECT id,menuName,restaurantId,price,content FROM menu WHERE restaurantId=" + str(f"'{selectedRestaurantId}'")
            cursor.execute(command)
            query = cursor.fetchall()

            session["menus"] = query

            return render_template("user/selectMenu.html", username=session["username"], data=session["menus"],
                                   extras=session["extras"], preselected=selected)

        return render_template("user/selectMenu.html", username=session["username"], data=session["menus"], extras= session["extras"])

    return render_template("user/selectMenu.html", username=session["username"], data=session["menus"], extras= session["extras"])

@app.route("/confirmOrder", methods=["GET", "POST"])
def confirmOrder():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    order = {
        "menus":{
        "menuNames": list(),
        "menuPrices": list(),
        "menuRestaurantId": list(),
        },
        "extras":{
        "extraNames": list(),
        "extraPrices": list(),
        },
        "totalCost": 0
    }
    username = str(session["username"])

    if request.method == "POST":
        if len(request.form.getlist("extra")) > 0:
            for extra in request.form.getlist("extra"):
                command = "SELECT name,price FROM extra WHERE name="+ f"'{str(extra)}'"
                cursor.execute(command)
                query = cursor.fetchall()[0]
                order["extras"]["extraNames"].append(query[0])
                order["extras"]["extraPrices"].append(query[1])
                order["totalCost"] += float(query[1])

        if len(request.form.getlist("selectedMenu")) > 0:
            for menu in request.form.getlist("selectedMenu"):
                command = "SELECT menu.menuName, menu.price, menu.id, restaurant.id, restaurant.restaurantName FROM menu, restaurant WHERE menu.restaurantId = restaurant.id and menu.menuName=" + f"'{str(menu)}'" 
                cursor.execute(command)
                query = cursor.fetchall()
                for q in query:
                    if str(q[2]) in request.form.getlist("selectedMenuId"):
                        order["menus"]["menuNames"].append(q[0])
                        order["menus"]["menuPrices"].append(q[1])
                        order["menus"]["menuRestaurantId"].append(q[3])
                        order["totalCost"] += float(q[1])

                
                print(order)

        command = "SELECT lat,lng FROM users WHERE username=" + f"'{str(username)}'"
        cursor.execute(command)
        query = cursor.fetchall()[0]
        print(query)
        command = "SELECT lat-"+str(query[0])+"+lng-"+str(query[1])+" as distance, id as courierID FROM couriers WHERE is_available=1 ORDER BY distance asc LIMIT 1";
        print(command)
        cursor.execute(command)
        query = cursor.fetchall()[0]
        

        content = ""
        content += str(order["menus"]["menuNames"])
        content += str(order["extras"]["extraNames"])

        orderContent = orderArrayToStr(content)

        cursor.execute("INSERT INTO foodOrder(content, totalPrice, restaurantId, courierID, userUserName) VALUES (?,?,?,?,?)",(orderContent, str(order["totalCost"]),order["menus"]["menuRestaurantId"][0],query[1], username))
        database.commit()

        cursor.execute("SELECT id FROM foodOrder ORDER BY id DESC LIMIT 1")
        orderId = cursor.fetchall()[0][0]

        cursor.execute("UPDATE couriers SET is_available=0,orderId=(?) WHERE id=(?)", (orderId,query[1]))
        database.commit()

        return redirect("home")
    return redirect("home")

def getUserViewData():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    # fetch user's coordinates
    cursor.execute("SELECT lat,lng FROM users WHERE username=(?)", (session["username"],))
    query = cursor.fetchall()[0]
    lat, lng = query[0], query[1]

    # fetch user's orders
    cursor.execute("SELECT foodOrder.totalPrice,foodOrder.orderDate,couriers.name, foodOrder.content, foodOrder.id, foodOrder.is_delivered, restaurant.restaurantName "
                   "FROM foodOrder INNER JOIN couriers ON couriers.id = foodOrder.courierID and foodOrder.userUserName=(?) INNER JOIN restaurant ON foodOrder.restaurantId = restaurant.id", (session["username"],))
    orders = cursor.fetchall()

    # fetch cheapest menus
    cursor.execute("SELECT restaurant.restaurantName, restaurant.address, menu.menuName, menu.price, menu.id, restaurant.id, menu.content "
                   "FROM menu INNER JOIN restaurant ON menu.restaurantId = restaurant.id ORDER BY price ASC LIMIT 5")
    cheap_menus = cursor.fetchall()

    # fetch near restaurants
    cursor.execute("SELECT lat-(?)+lng-(?) as distance,* FROM restaurant WHERE isOpen = 1 ORDER BY distance asc LIMIT 5", (lat, lng))
    near_restaurants = cursor.fetchall()


    info = {
        "orders":orders,
        "cheap_menus":cheap_menus,
        "near_restaurants":near_restaurants
    }
    return info

@app.route("/exit", methods=["GET"])
def exit():
    session.clear()

    return redirect('/')

@app.route("/courierDetail", methods=["GET"])
def courierDetail():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    couirerID = request.args.get('courier', default=1, type=int)

    command = "SELECT count(*) FROM foodOrder WHERE foodOrder.courierID ="+str(couirerID)
    cursor.execute(command)
    totalCourierOrder = int(cursor.fetchall()[0][0])

    if totalCourierOrder == 0:
        cursor.execute("SELECT couriers.id,  couriers.name, is_available, couriers.lat, couriers.lng FROM couriers WHERE couriers.id = (?)", (couirerID,))
        query = cursor.fetchall()
        print("Detail:",query)
    else:
        cursor.execute("SELECT couriers.id, couriers.name, is_available, couriers.lat, couriers.lng, foodOrder.is_delivered, foodOrder.orderDate, users.username, foodOrder.id "
                       "FROM couriers INNER JOIN users,foodOrder ON couriers.id = (?) and foodOrder.courierID = (?) and foodOrder.userUserName = users.username", (couirerID,couirerID))


        query = cursor.fetchall()
        print("Detail:",query)
    return render_template("admin/list_operations/courier_detail.html", username=session["username"], data=query, totalOrder=totalCourierOrder)

@app.route("/reviewRestaurant", methods=["GET","POST"])
def reviewRestaurant():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

        restID = request.args.get('restId', default=1, type=int)


        if request.method == "POST":
            rating = request.form["rating"]
            cursor.execute("INSERT INTO review(rating,reviewDate,restaurantId,userUserName) VALUES((?),(datetime('now','localtime')),(?), (?))", (rating, restID, f"{session['username']}"))
            database.commit()
            cursor.execute("UPDATE restaurant SET averageRating = (SELECT avg(rating) FROM review WHERE restaurantId = (?)) WHERE restaurant.id= (?)",
                           (restID, restID))
            return redirect("home")

    return render_template("user/reviewRestaurant.html", username=session["username"], restId = restID)

@app.route("/editRestaurant", methods=["GET","POST"])
def editRestaurant():
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    restID = request.args.get('restId', default=1, type=int)
    print(restID)

    cursor.execute("SELECT restaurantName, address, isOpen FROM restaurant WHERE id=(?)", (restID,))
    query = cursor.fetchall()[0]

    if request.method == "POST":
        newAddress = request.form["restAddress"]
        newName = request.form["restName"]
        isOpen = request.form["isopen"]

        new_lat, new_lng = searchCoordinates(newAddress)

        print(restID, newAddress, newName, isOpen)
        cursor.execute("UPDATE restaurant SET restaurantName=(?), address=(?), lat=(?), lng=(?), isOpen=(?) WHERE id=(?)", (newName, newAddress, new_lat, new_lng, isOpen, restID))
        database.commit()

        return redirect("restaurants")

    return render_template("admin/insert_operations/editRestaurant.html", username=session["username"], restId=restID, restInfo=query)


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

def getMenus(cursor, limit=None):
    cursor.execute("SELECT menu.id, menuName, price, content, restaurant.restaurantName FROM menu INNER JOIN restaurant ON menu.restaurantId = restaurant.id ORDER BY menu.id desc")
    query = cursor.fetchall()
    return query

def getOrders(cursor, limit=None):
    cursor.execute("SELECT foodOrder.id, content, orderDate, totalPrice, is_delivered, couriers.name, userUserName, restaurant.restaurantName "
                   "FROM foodOrder INNER JOIN couriers ON foodOrder.courierID = couriers.id INNER JOIN restaurant ON foodOrder.restaurantId = restaurant.id")

    query = cursor.fetchall()
    return query


def getRestaurantName(cursor, limit=None):
    cursor.execute("SELECT restaurant.restaurantName, menu.menuName, menu.price, menu.id, restaurant.id, menu.content "
                   "FROM menu INNER JOIN restaurant ON menu.restaurantId = restaurant.id")
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
        if entity == "menu":
            data[entity] = getMenus(cursor, limit)
        if entity == "restaurantName":
            data[entity] = getRestaurantName(cursor, limit)
        if entity == "orders":
            data[entity] = getOrders(cursor, limit)
        else:
            pass
    return data

def canReview(cursor):
    cursor.execute("SELECT restaurant.id as restId, foodOrder.restaurantId as orderId, users.username FROM restaurant, foodOrder "
                   "INNER JOIN users ON users.username = foodOrder.userUserName "
                   " WHERE (restaurant.id, users.username) NOT IN (SELECT review.restaurantId, review.userUserName FROM review) "
                   "AND foodOrder.restaurantId = restaurant.id AND username=(?)",
                   (session["username"],))
    

    query = cursor.fetchall()
    print(query)
    reviewedRests = []

    for id in query:
        reviewedRests.append(id[0])

    return reviewedRests

def orderArrayToStr(str):
    with sqlite3.connect(DATABASE) as database:
        cursor = database.cursor()

    orderstr = ''.join(str).replace("[","").replace("]","").replace("'","")
    return orderstr

if __name__ == '__main__':
    app.run(debug=True)
