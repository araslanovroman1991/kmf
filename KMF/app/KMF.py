from flask import Flask, render_template, request, session, redirect, url_for, abort, flash, send_file
from flask_wtf import Form
from wtforms import SelectField
from flask_login import LoginManager
import configparser
from pathlib import Path
import psycopg2
from contextlib import closing
import requests
from datetime import timedelta
from random import randint, randrange
import pandas as pd
import uuid
from xlsxwriter import Workbook

app = Flask(__name__)
config = configparser.ConfigParser()
myself = Path(__file__).resolve()
configfilename = f'{myself.parents[0]}/config/{myself.name.split(".")[0]}.ini'
sql_path = f'{myself.parents[0]}/config/{myself.name.split(".")[0]}.sql'
config.read(configfilename)
dbname = config["db"]["dbname"]
user = config["db"]["user"]
password = config["db"]["password"]
host = config["db"]["host"]
token = config["telegram"]["token"]
chat_id = config["telegram"]["chat_id"]
app.config['SECRET_KEY'] = config["SECRET_KEY"]["SECRET_KEY"]

#Время жизни сессии
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=10)

#Аутентификация пользователя
def acces_root(usr,pswd):
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read().split(";")[0].replace("$username$",f'{usr}').replace("$pass$",f'{pswd}')
                cursor.execute(sql_script)
                result=cursor.fetchall()[0][0]
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=2
    return(result)   

#Загрузка полей в форму
def get_fields(field):
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read().split(";")[field]
                cursor.execute(sql_script)
                result=cursor.fetchall()
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=["Нет данных"]
    return(result) 

#Получение данных по сумме на счете, типа операции
def get_amount_plmin(name,field):
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read().split(";")[field].replace("$name$",f'{name}')
                cursor.execute(sql_script)
                result=cursor.fetchall()
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=["Нет данных"]
    return(result) 

#Получение сырых данных в pandas
def get_pdf(fio_client,d_from,d_to):
    uuid_nm=str(uuid.uuid4())
    pdf_pth=f'{myself.parents[0]}/data_store/{uuid_nm}.xlsx'
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read()
                sql_script1=sql_script.split(";")[7].replace("$fio_client$",fio_client).replace("$d_from$",d_from).replace("$d_to$",d_to)
                cursor.execute(sql_script1)
                result=cursor.fetchall()
                colnames = [desc[0] for desc in cursor.description]
                df=pd.DataFrame(result)
                if len(df) > 0:
                    df=df.apply(pd.to_numeric, errors='ignore')
                    for x in range(0,len(colnames)):
                        df=df.rename(columns={df.columns[x]:f'{colnames[x]}'})
                    #массив неблокированных транзакций
                    not_bl=df.loc[:].query("type_blocked==0").fillna("")
                    #массив блокированных транзакций
                    bl=df.loc[:].query("type_blocked==1").fillna("")
                    sum_bl_pl=not_bl.loc[:].query('amount_com > 0')
                    sum_bl_min=not_bl.loc[:].query('amount_com < 0')
                    #сумма доходов за период
                    sum_bl_pl_all=sum_bl_pl[:][["amount_com"]].sum().iloc[0]
                    #сумма расходов за период
                    sum_bl_min_all=sum_bl_min[:][["amount_com"]].sum().iloc[0]
                    #переназываем поля
                    col_rus=["Дата проведения по счету", "Номер карты", "Тип операции", "Страна", "Город", "ID объекта", "Название объекта", "Код авторизации", "MCC код", "Сумма", "Валюта", "Комисия", "Сумма с учетом комиссии RUR"]
                    msv=[]
                    for xx in [not_bl,bl]:
                        for x in range(0,len(col_rus)):
                            xx=xx.rename(columns={xx.columns[x]:f'{col_rus[x]}'})
                        xx=xx.drop(["type_blocked"],axis=1)
                        msv.append(xx)
                else:
                    df="Печалька"
                #сумма на счете сейчас
                sum_account_now=get_amount_plmin(fio_client,3)[0][0]
                #сумма на счете на начало и конец периода
                sql_script2=sql_script.split(";")[8].replace("$fio_client$",fio_client).replace("$d_from$",d_from).replace("$d_to$",d_to)
                cursor.execute(sql_script2)
                result=cursor.fetchall()
                sum_account_frst=result[0][0]
                sum_account_lst=result[1][0]
                #Создание массива с данными счета
                period=str(d_from) + " - " +str(d_to)
                cl=pd.DataFrame({'Период запроса': [period], 'Текущая сумма на счете': [sum_account_now], 'Сумма на начало периода':[sum_account_frst], 'Сумма на конец периода':[sum_account_lst]})
                #данные расчетного счета клиента
                sql_script3=sql_script.split(";")[9].replace("$fio_client$",fio_client)
                cursor.execute(sql_script3)
                result=cursor.fetchall()
                colnames = [desc[0] for desc in cursor.description]
                client=pd.DataFrame(result)
                client=client.apply(pd.to_numeric, errors='ignore')
                for x in range(0,len(colnames)):
                    client=client.rename(columns={client.columns[x]:f'{colnames[x]}'})
                #Сохраняем данные
                with closing(pd.ExcelWriter(pdf_pth)) as writer:
                    try:
                        msv[0].to_excel(writer, sheet_name="Активные транзакции", index=False)
                        msv[1].to_excel(writer, sheet_name="Заблокированные транзакции", index=False)
                    except:
                        pass
                    client.to_excel(writer, sheet_name="Данные клиента", index=False)
                    cl.to_excel(writer, sheet_name="Данные по счету", index=False)
                result=1
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=0
    return([result,uuid_nm,pdf_pth]) 

# Запись сырых данных в таблицу
def insert_raw(date,type_operation,fio_client,auth_code,type_blocked,amount,amount_com):
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read().split(";")[5].replace("$date$",str(date)).replace("$type_operation$",str(type_operation)).replace("$fio_client$",str(fio_client))
                sql_script=sql_script.replace("$auth_code$",str(auth_code)).replace("$type_blocked$",str(type_blocked)).replace("$amount$",str(amount)).replace("$amount_com$",str(amount_com))
                cursor.execute(sql_script)
                conn.commit()
                result=1
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=0
    return(result) 

#Запись данных при изменении суммы на счете
def insert_sum(fio_client,amount):
    try:
        with closing(psycopg2.connect(dbname=dbname,user=user,password=password,host=host)) as conn:
            cursor=conn.cursor()
            with open(sql_path) as sql:
                sql_script=sql.read().split(";")[6].replace("$fio_client$",str(fio_client)).replace("$amount$",str(amount))
                cursor.execute(sql_script)
                conn.commit()
                result=1
    except Exception as e:
        requests.get(f"""https://api.telegram.org/{token}/sendMessage?chat_id={chat_id}&text={e}""")
        result=0
    return(result) 

@app.route("/login", methods=["POST","GET"])
def login():
    if 'userLogged' in session:
        return redirect(url_for('settings', username=session["userLogged"]))
    elif request.method == 'POST':
        if acces_root(request.form["username"],request.form["pass"]) == 1:
            session['userLogged'] = request.form['username']
            return redirect(url_for('settings', username=session["userLogged"]))
        else:
            flash("Неверно введенные данные. Попробуйте еще раз либо обратитесь к администратору.")
    return render_template('login.html')

@app.route("/settings")
def settings():
    if 'userLogged' not in session:
        return redirect(url_for('login'))
    else:
        return render_template('settings.html')

@app.route("/get_transactions", methods=['GET', 'POST'])
def get_transactions():
    if 'userLogged' not in session:
        return redirect(url_for('login'))
    else:
        fio=[x[0] for x in get_fields(1)]
        type_oper=[x[0] for x in get_fields(2)]
        if request.method == 'POST':
            date=request.form["date"]
            fo=request.form["fio"]
            tp=str(request.form["type_oper"]).strip()
            amount=request.form["amount"]
            auth_code=randrange(100000, 999999) 
            if len(date) > 0 and len(fo) > 0 and len(tp) > 0 and (len(amount) > 0 and int(amount)>0):
                sum_fo=get_amount_plmin(fo,3)
                if sum_fo=="Нет данных" or len(sum_fo) == 0:
                    sum = float(0)
                if len(sum_fo) > 0:
                    sum = float(sum_fo[0][0])

                try:
                    plmin=str(get_amount_plmin(tp,4)[0][0])
                except:
                    plmin="+"

                if plmin == "-":
                    diff = sum-float(amount)
                    if diff < 0:
                        result=insert_raw(date,tp,fo,auth_code,1,float(amount),-float(amount))
                        if result==1:
                            flash("Недостаточно средств на счете. Транзакция заблокирована. Успешно записана в БД")
                        else:
                            flash("Недостаточно средств на счете. Транзакция заблокирована. Проблема записи в БД")
                    else:
                        result=insert_raw(date,tp,fo,auth_code,0,float(amount),-float(amount))
                        if result==1:
                            flash(f'Транзакция прошла успешно. Данные успешно записаны в БД.')
                        else:
                            flash("Транзакция прошла успешно. Проблема записи в БД")
                        
                        result=insert_sum(fo,diff)
                        if result==1:
                            flash(f'Сумма на счете обновлена. Данные успешно записаны в БД. Сейчас на счете {get_amount_plmin(fo,3)[0][0]} рублей')
                        else:
                            flash("Сумма на счете не обновлена. Проблема записи в БД")
                else:
                    result=insert_raw(date,tp,fo,auth_code,0,float(amount),float(amount))
                    if result==1:
                        flash(f'Транзакция прошла успешно. Данные успешно записаны в БД. Сейчас на счете')
                    else:
                         flash("Транзакция прошла успешно. Проблема записи в БД")
                    
                    sum=sum+float(amount)
                    result=insert_sum(fo,sum)
                    if result==1:
                        flash(f'Сумма на счете обновлена. Данные успешно записаны в БД. Сейчас на счете {get_amount_plmin(fo,3)[0][0]} рублей')
                    else:
                        flash("Сумма на счете не обновлена. Проблема записи в БД")
            else:
                flash("Некорректно введенные данные. Попробуйте еще раз")

        return render_template('get_transactions.html',fio=fio,type_oper=type_oper)
    
@app.route("/get_statement", methods=['GET', 'POST'])
def get_statement():
    if 'userLogged' not in session:
        return redirect(url_for('login'))
    else:
        fio=[x[0] for x in get_fields(1)]
        if request.method == 'POST':
            d_f=request.form["d_from"]
            d_t=request.form["d_to"]
            d_fio=request.form["fio"]
            if len(d_f) > 0 and len(d_t) > 0 and len(d_fio):
                result=get_pdf(str(d_fio),str(d_f),str(d_t))
                if result[0]==1:
                    # flash(f'Документ успешно сохранен')
                    return send_file(result[2])     
                else:
                    flash("Проблема при сохранении документа")    
            else:
                flash("Необходимо корректно заполнить данные")

        return render_template('get_statement.html',fio=fio)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5555,debug=True)


