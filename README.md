Food_Ordering_System

Şimdilik dbde food_order adında bir database olması lazım kendi oluşturmuyor. Tabloları kendi oluşturuyor (şimdilik sadece User).

node js pcde kurlu olmalı ve phpmyadmin e erişebiliyor olmanız lazım.
eğer çalıştıracaksanız backend/dbconstants dosyasındaki değişkenleri kendi db bilgilerinize göre ayarlayın

sadece ilk kez çalıştıracaksanız:
npm i express, mysql, https

backend i çalıştırmak için:
nodemon app.js

user types:
type 1 = admin
type 0 = user

DBye üye eklemek (kayıt olmak için)
(POST) http://localhost:8080/api/register?username=arda&fullname=mert+arda+asar&address=mef+university&email=asarm@mef.edu.tr&type=1

Şuan 2 farklı yanıt döndürebilir gerektikçe bu yanıtları çoğaltırız:
200 -> OK
1062 -> User(row) already exist
