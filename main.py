from dotenv import dotenv_values
from psycopg2 import Error
import psycopg2
import numpy
import os
import cx_Oracle
import time
import sys
import datetime
import csv

config = dotenv_values(".env")

oracle_host = config['ORACLE_HOST']
oracle_port = config['ORACLE_PORT']
oracle_service = config['ORACLE_SERVICE_NAME']
oracle_user = config['ORACLE_USER']
oracle_pass = config['ORACLE_PASS']

postgres_host = config['POSTGRES_HOST']
postgres_port = config['POSTGRES_PORT']
postgres_database = config['POSTGRES_DATABASE_NAME']
postgres_user = config['POSTGRES_USER']
postgres_pass = config['POSTGRES_PASS']

dsn_tns = cx_Oracle.makedsn(oracle_host, oracle_port, service_name=oracle_service)
connection = cx_Oracle.connect(
    user=oracle_user,
    password=oracle_pass,
    dsn=dsn_tns)

if connection:
    print("Successfully connected to Oracle Database")
    cursor = connection.cursor()

try:
    connectionPostgres = psycopg2.connect(user=postgres_user,
                                  password=postgres_pass,
                                  host=postgres_host,
                                  port=postgres_port,
                                  database=postgres_database)
    cursorPostgres = connectionPostgres.cursor()
    cursorPostgres.execute("SELECT version();")
    record = cursorPostgres.fetchone()
    print("You are connected to - ", record, "\n")
except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    print("PostgreSQL connection is complete")

def progress(count, total, match, status=''):
    if count % match == 0:
        bar_len = 60
        filled_len = int(round(bar_len * count / float(total)))
        percents = round((100.0 * count / float(total)) + 1, 2)
        if percents >= 100 :
            percents = 100

        bar = '=' * filled_len + '-' * (bar_len - (filled_len + 1))

        sys.stdout.write('%s : [%s] %s%s \r' % (status, bar, percents, '%'))
        sys.stdout.flush()  

def convertArrayToList(arr):
    listData = list(arr)
    return listData

def csvNameFormat(name_file):
    name = name_file.upper().replace('.', '_') + ".csv"
    return name

def queryColumnName(tableName, flag):
    tableQuery = tableName.split('.')
    sql = """ SELECT 
                OWNER,
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                DATA_LENGTH,
                DATA_PRECISION,
                DATA_SCALE
            FROM ALL_TAB_COLS
            WHERE TABLE_NAME = '{1}'
            AND OWNER = '{0}'
            AND COLUMN_NAME NOT IN ( 'PASSWORD', 'VERSION', 'ID' )
            ORDER BY COLUMN_ID ASC """.format(tableQuery[0], tableQuery[1])
    cursor.execute(sql)
    listTableName = []
    while True:
        rows = cursor.fetchone()
        if rows is None:
            break
        # print(rows)
        if flag == 1:
            listTableName.append(rows[2].lower())
        if flag == 2:
            listTableName.append(rows)
    return listTableName

def headerColumn(listColumnName):
    listColumn = listColumnName
    l = len(listColumn) - 1
    i = 0
    header = '';

    for d in listColumn:
        if i == l:
            header = header + d
        else:
            header = header + d + ','
        i = i + 1
    header = header + ''
    return header

def convertType(datatype, datalength, precision, scale):
    switcher = {
        "CHAR": 'CHAR({0})'.format(datalength),
        "VARCHAR": 'VARCHAR({0})'.format(datalength),
        "VARCHAR2": 'VARCHAR({0})'.format(datalength),
        "NUMBER": 'NUMERIC({0},{1})'.format(precision, scale),
        "DATE": 'DATE'
    }
    return switcher.get(datatype, -1)

def sqlPaserCreateTable(data, tablename):
    tableName = tablename
    sql = """
        DROP TABLE IF EXISTS {0};
        CREATE TABLE {0}(""".format(tableName)
    length = len(data) - 1
    for idx, val in enumerate(data):
        datatype = convertType(val[3], val[4], val[5], val[6])
        if datatype == -1:
            print("Not match datatype to convert for postgres database = Column:{0}, Type:{1}". format(val[2], val[4]))
            exit()
        if idx == length:
            sql = sql + "\n {0} {1}".format(val[2], datatype) + "\n);"
        else:
            sql = sql + "\n {0} {1}".format(val[2], datatype) + ","
    return sql

def convertDataToCsv(tablename):
    tableName = tablename
    tableColumnName = queryColumnName(tableName, 1)
    sqlCount = "SELECT COUNT(*) FROM {0} WHERE ROWNUM <= 50 ORDER BY bill_period DESC".format(tableName)
    sql = "SELECT * FROM {0} WHERE ROWNUM <= 50 ORDER BY bill_period DESC".format(tableName)
    #sqlCount = "SELECT COUNT(*) FROM {0} ".format(tableName)
    #sql = "SELECT * FROM {0}".format(tableName)
    cursor.execute(sqlCount)
    count = cursor.fetchone()
    count = count[0]
    print("Count {0}".format(count))
    cursor.execute(sql)

    timeNow = datetime.datetime.now().isoformat()
    print("{0} : (Table={1}) Waiting query data to csv...".format(timeNow, tableName))
    fileName = csvNameFormat(tableName)
    csv_file =  open(fileName, 'w')
    csv_writer = csv.writer(csv_file, delimiter=",", lineterminator='\r\n', quotechar = '\\')
    i = 0
    header = headerColumn(tableColumnName)
    csv_writer.writerow(header)
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        row = convertArrayToList(row)
        csv_writer.writerow(row)
        progress(i, count, 10, status='Query data to csv')
        i += 1

    timeNow = datetime.datetime.now().isoformat()
    print("{0} : (Table={1}) Downloaded.".format(timeNow, tableName))
    del(count)
    del(timeNow)

def csvToDatabase(tableName, targetTable):
    fileName = csvNameFormat(tableName)
    tableColumnName = queryColumnName(tableName, 1)
    tableColumn = queryColumnName(tableName, 2)
    sqlCreateTable = sqlPaserCreateTable(tableColumn, targetTable)
    cursorPostgres.execute(sqlCreateTable)
    np_arr1 = numpy.array(tableColumnName)
    with open(fileName, 'r') as f:
        next(f) # Skip the header row.
        cursorPostgres.copy_from(f, targetTable, sep=',', columns=np_arr1)
    connectionPostgres.commit()

def migrateExecute(call_procedure):
    sql = call_procedure
    timeNow = datetime.datetime.now().isoformat()
    print("{0} : (Procedure={1}) Executing....\r".format(timeNow, sql))
    cursorPostgres.execute(sql)
    record = cursorPostgres.fetchone()
    time.sleep(1.5)
    timeNow = datetime.datetime.now().isoformat()
    print("{0} : (Procedure={1}) Executed.\r".format(timeNow, sql))

convertDataToCsv('BILL.UNIT_PROCESS')
convertDataToCsv('BILL.FT_MASTER')
csvToDatabase('BILL.UNIT_PROCESS', 'unit_process')
csvToDatabase('BILL.FT_MASTER', 'ft_master')
migrateExecute("SELECT 1, 2;")
migrateExecute("SELECT 1, 3;")

while True:
    time.sleep(0.100)
    pass
