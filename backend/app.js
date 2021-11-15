const express = require('express')
var mysql = require('mysql');
const https = require('https')
const dbconstants = require('./dbconstants')
const { log } = require('console');

app = express()

function getCoordinates(address) {
    lat = 0
    lon = 0
    return "(" + lat + "," + log + ")"
}

// app.set('view engine', 'ejs')
// app.set('views', path.join(__dirname, './views'))
// app.use(express.static(path.join(__dirname, './static')))

var con = mysql.createConnection({
    host: dbconstants.host,
    user: dbconstants.username,
    password: dbconstants.password,
    database: "food_order"
});

con.connect(function (err) {
    if (err) throw err;
    console.log("DB Connection is Successful!");
    con.query("CREATE DATABASE IF NOT EXISTS food_order", function (err, result) {
        if (err) throw err;
        else
            console.log("Database created");
    });

    con.query("CREATE TABLE IF NOT EXISTS users(username varchar(30) PRIMARY KEY, fullname varchar(150), address varchar(150), coordinates varchar(150), email varchar(100), type INTEGER, register_date Date DEFAULT (CURRENT_DATE))", function (err, result) {
        console.log("Users table created");
    });
});


app.get('/api/login', function (request, res) {

})

app.post('/api/register', function (request, res) {
    req = request.query
    username = req.username
    fullname = req.fullname
    address = req.address
    email = req.email
    type = req.type

    coordinates = getCoordinates(address.replace(" ", "+"))
    console.log(coordinates)

    var sql = "INSERT INTO users (username, fullname, address, email UNIQUE, type) VALUES ?";
    var values = [
        [username, fullname, address, email, type],
    ];

    con.query(sql, [values], function (err, result) {
        if (err && err.code == "ER_DUP_ENTRY") {
            console.log("Username already exist")
            res.send(1062)
        }
        console.log("User " + username + " inserted");
        res.send(200)

    });

})

app.listen(8080)