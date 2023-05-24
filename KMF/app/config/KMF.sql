/* Валидация пользователя */
SELECT count(*)
FROM kmf.spr_users
WHERE username='$username$' AND pass='$pass$';
/* ФИО клиентов */
SELECT fio_client
FROM kmf.spr_clients;
/* Типы операций */
SELECT name
FROM kmf.spr_transaction;
/* Текущая сумма на счете указанного клиента*/
SELECT hst.amount::float
FROM kmf.balance_value_history as hst
INNER JOIN kmf.spr_clients as cl ON cl.id=hst.card_number
WHERE cl.fio_client like '%$name$%'
ORDER BY hst.date_time DESC
LIMIT 1;
/* Плюс/минус */
SELECT plmin
FROM kmf.spr_transaction
WHERE name like '%$name$%';
/* Запись сырых данных */
INSERT INTO kmf.raw_data (date,card_number,type_operation,curency,object_id, auth_code, type_blocked, country,
amount,comission,amount_com)
SELECT '$date$' as date, cl.card_number, ts.type_operation, 'RUR' as curency, ts.object_id, 
$auth_code$ as auth_code, $type_blocked$ as type_blocked, 'RUS' as country,
$amount$ as amount, 00.00 as comission, $amount_com$ as amount_com
FROM (	
SELECT dd.id as type_operation, 'transact' as transact, obj.id as object_id FROM kmf.spr_transaction as dd
LEFT JOIN kmf.spr_objects as obj ON obj.type_op=dd.id
WHERE name LIKE '%$type_operation$%'
order by random() LIMIT 1) AS ts
LEFT JOIN (SELECT id as card_number, 'transact' as transact 
FROM kmf.spr_clients
WHERE fio_client like '%$fio_client$%') as cl ON cl.transact=ts.transact;
/* Запись информации по счету */
INSERT INTO kmf.balance_value_history (card_number,amount)
SELECT id, $amount$ as amount
FROM kmf.spr_clients st
WHERE st.fio_client like '%$fio_client$%';
/* Получение выписки по счету */
SELECT dt.date,cl.card_number,trn.name,dt.country,obj.city,
obj.number_object,obj.name_object,
dt.auth_code,obj.mcc_code,dt.amount,dt.curency,dt.comission,dt.amount_com,dt.type_blocked
FROM kmf.raw_data as dt
LEFT JOIN kmf.spr_clients as cl ON cl.id=dt.card_number
LEFT JOIN kmf.spr_objects as obj ON obj.id=dt.object_id
LEFT JOIN kmf.spr_transaction as trn ON trn.id=dt.type_operation
WHERE dt.date >= TO_DATE('$d_from$','YYYY-MM-DD') AND dt.date <= TO_DATE('$d_to$','YYYY-MM-DD')
AND cl.fio_client like '%$fio_client$%';
/* Получение суммы по счету на первую и последнюю дату */
SELECT COALESCE((
SELECT hst.amount::float as amount
FROM kmf.balance_value_history as hst
INNER JOIN kmf.spr_clients as cl ON cl.id=hst.card_number
WHERE cl.fio_client like '%$fio_client$%'
and hst.date_time::date <= TO_DATE('$d_from$','YYYY-MM-DD')
ORDER BY hst.date_time DESC
LIMIT 1),'0')
UNION ALL
SELECT COALESCE((
SELECT hst.amount::float as amount
FROM kmf.balance_value_history as hst
INNER JOIN kmf.spr_clients as cl ON cl.id=hst.card_number
WHERE cl.fio_client like '%$fio_client$%'
and hst.date_time::date <= TO_DATE('$d_to$','YYYY-MM-DD') 
ORDER BY hst.date_time DESC
LIMIT 1),'0');
/* Получение реквизитов клиента */
SELECT contract_number,card_number,currency,bank_details,fio_client,account_numb::float
FROM kmf.spr_clients
WHERE fio_client like '%$fio_client$%';





