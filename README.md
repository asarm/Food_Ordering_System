Food_Ordering_System

npm i express, mysql, https
nodemon app.js

type 1 = admin
type 0 = user

DBye üye eklemek (kayıt olmak için)
(POST) http://localhost:8080/api/register?username=arda&fullname=mert+arda+asar&address=mef+university&email=asarm@mef.edu.tr&type=1

2 farklı yanıt döndürebilir:
200 -> OK
1062 -> User(row) already exist
