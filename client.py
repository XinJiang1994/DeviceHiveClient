import re
import warnings
import MySQLdb
import time
from devicehive import Handler, DeviceHiveApi
from devicehive import DeviceHive
import redis
import sched
import threading

SERVER_URL = 'http://192.168.1.107/api/rest'
# REDIS_HOST='localhost'
# REDIS_PORT=6379
# REDIS_db=0


BACK_INTERVAL=5*60 #UNIT: SECOND
HEART_BEAT_INTERVAL=1*60 # 1 minute
# 'PUT_YOUR_REFRESH_TOKEN_HERE'
SERVER_REFRESH_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJwYXlsb2FkIjp7ImUiOjE1NDY5OTgzMTY2MzgsInQiOjAsInUiOjEsImEiOlswXSwibiI6WyIqIl0sImQiOlsiKiJdfX0.hfY6yYHHN5CEIE0z9QT6rKyD4kTf1yj_e2m7Sv1JB3E'

class MySqlManager():
    def __init__(self,mysql_db_server_ip,mysql_user,mysql_password,mysql_db_name):
        self.mysql_db_server_ip=mysql_db_server_ip
        self.mysql_user=mysql_user
        self.mysql_password=mysql_password
        self.mysql_db_name=mysql_db_name
        self.create_db_if_not_exist(self.mysql_db_server_ip,self.mysql_user,self.mysql_password,self.mysql_db_name)

    def connect_db(self):
        try:
            print (self.mysql_user)
            db = MySQLdb.connect(self.mysql_db_server_ip, self.mysql_user, self.mysql_password, self.mysql_db_name, charset='utf8')
            return db
        except MySQLdb.Error, e:
            print ("Mysql Error %d: %s" % (e.args[0], e.args[1]))

    def disconnect_db(self,db):
        try:
            db.close()
        except MySQLdb.Error, e:
            print ("Mysql Error %d: %s" % (e.args[0], e.args[1]))
        finally:
            db.close()
    def is_table_exist(self,tableName='device_status',host=None, user=None, pw=None,db_name=None):
        ret=False
        if tableName is None:
            raise Exception('tableName param is must')
        if host is None and user is None and pw is None and db_name is None:
            host=self.mysql_db_server_ip
            user=self.mysql_user
            pw=self.mysql_password
            db_name=self.mysql_db_name
        if host is None or user is None or pw is None or db_name is None:
            raise Exception('miss db parameter.')
        try:
            db = MySQLdb.connect(host, user, pw, db_name, charset='utf8')
            cursor = db.cursor()
            sql_show_tables='SHOW TABLES;'
            cursor.execute(sql_show_tables)
            tables=[cursor.fetchall()]  #fetchall return s list of tuple,eg:(('city',),('country',))
            #The following two lines regulize the output to ['city','country']
            table_list=re.findall('(\'.*?\')',str(tables))
            table_list=[re.sub("'",'',each) for each in table_list]
            if tableName in table_list:
                ret=True
            cursor.close()
            db.close()
        except MySQLdb.Error, e:
            print ("Mysql Error %d: %s" % (e.args[0], e.args[1]))
        return ret

    def create_db_if_not_exist(self,host, user, pw, name):
        try:
            db = MySQLdb.connect(host, user, pw, charset='utf8')
            cursor = db.cursor()
            # cursor.execute('show databases')
            # rows = cursor.fetchall()
            # for row in rows:
            #     tmp = "%2s" % row
            #     if name == tmp:
            #         cursor.execute('drop database if exists ' + name)
            cursor.execute('create database if not exists ' + name)
            db.commit()
            cursor.close()
            db.close()
        except MySQLdb.Error, e:
            print ("Mysql Error %d: %s" % (e.args[0], e.args[1]))

    def create_table_if_not_exist(self,sql=None):
        if sql is None:
            sql='''
                CREATE TABLE IF NOT EXISTS `device_status` (
                      `device_id` VARCHAR(100) NOT NULL,
                      `uptime` DOUBLE NULL,
                      `recent_heartbeat` DOUBLE NULL,
                      PRIMARY KEY (`device_id`));
            '''
        try:
            db = MySQLdb.connect(self.mysql_db_server_ip, self.mysql_user, self.mysql_password, self.mysql_db_name,
                                 charset='utf8')
            cursor = db.cursor()
            cursor.execute(sql)
            db.close()
        except MySQLdb.Error, e:
            print ("Mysql Error %d: %s" % (e.args[0], e.args[1]))


    def insertORupdate(self,dev_id,uptime,recent_heartbeat):
        db = MySQLdb.connect(self.mysql_db_server_ip, self.mysql_user, self.mysql_password, self.mysql_db_name)
        cursor = db.cursor()
        rowNums = cursor.execute("SELECT * FROM device_status WHERE  device_id=%s ", (dev_id,))
        if rowNums != 0:
            data = cursor.fetchone()
            print ("Data : ", data)
            r = cursor.execute("UPDATE device_status set recent_heartbeat=%s WHERE device_id=%s ",
                               (recent_heartbeat, dev_id,))
            if r > 0:
                print ("Update % record. " % r)
            db.commit()

        else:
            print("There is no data in DB")
            insert_row = cursor.executemany("INSERT INTO device_status(device_id,uptime,recent_heartbeat) "
                                            "VALUES (%s,%s,%s) ",
                                            [(dev_id, uptime, recent_heartbeat,)])
        db.commit()
        cursor.close()
        db.close()

class MsgSovler():
    def __init__(self,mysql_db_server_ip='localhost',mysql_user='root',mysql_password=None,mysql_db_name=None,
                 REDIS_HOST='localhost',REDIS_PORT=6379,REDIS_db=0):
        self.name='msg solver'
        self.mysql_db_server_ip=mysql_db_server_ip
        self.mysql_user=mysql_user
        self.mysql_password=mysql_password
        self.mysql_db_name=mysql_db_name
        self.mysql_manager = MySqlManager(self.mysql_db_server_ip, self.mysql_user, self.mysql_password, self.mysql_db_name)
        self.mysql_manager.create_table_if_not_exist()
        self.heat_beat_interval=HEART_BEAT_INTERVAL
        pool=redis.ConnectionPool(host=REDIS_HOST,port=REDIS_PORT,db=REDIS_db)
        self.r=redis.StrictRedis(connection_pool=pool)
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self.BACK_INTERVAL=BACK_INTERVAL
        self.redis_to_sql()
        t = threading.Thread(target=self._scheduler.run)
        t.setDaemon(True)
        t.start()
    def redis_to_sql(self):

        keys=self.r.keys()
        print('print keys.........................')
        for key in keys:
            dev_id = key
            uptime = self.r.hget(key,'uptime')
            recent_heartbeat = self.r.hget(key,'recent_heartbeat')
            self.mysql_manager.insertORupdate(dev_id,uptime,recent_heartbeat)
        self._scheduler.enter(self.BACK_INTERVAL, 1, self.redis_to_sql, ())
    def sql_to_redis(self):
        pass

    def heartbeat_msg(self,notification):
        dev_id = notification.device_id
        print("dev_id:", dev_id)
        fieldNums = self.r.hlen(dev_id)
        if fieldNums != 0:
            current_time = time.time()
            self.r.hset(notification.device_id, 'recent_heartbeat', current_time)
        else:
            print("There is no data in DB")
            current_time = time.time()
            attr_dict={
                'uptime': current_time,
                'recent_heartbeat':current_time
            }
            self.r.hmset(notification.device_id,attr_dict)

class ClientHandler(Handler):
    def __init__(self, api, device_id='simple-example-device',
                 mysql_db_server_ip='localhost',mysql_user='root',mysql_password=None,mysql_db_name=None,
                 REDIS_HOST='localhost', REDIS_PORT=6379, REDIS_db=0,
                 accept_command_name='accept_notifications'):
        Handler.__init__(self, api)
        self._device_id = device_id
        self._accept_command_name = accept_command_name
        self._device = None
        self.msgsolver=MsgSovler(mysql_db_server_ip, mysql_user, mysql_password, mysql_db_name,
                                 REDIS_HOST,REDIS_PORT,REDIS_db)

    def handle_connect(self):
        # self.api.subscribe_insert_commands()
        # self.api.subscribe_update_commands()
        print("connected!")
        self.api.subscribe_notifications()

    def handle_command_insert(self, command):
        print(command.command)

    def handle_command_update(self, command):
        print('command update####################################')
        print(command.command)

    def handle_notification(self, notification):
        print('Notification "%s" received' % notification.notification)
        print("sender's device_id is : ", notification.device_id)
        print ("parameter:", notification.parameters)
        print ("CURRENT TIME:", time.time())
        self.msgsolver.heartbeat_msg(notification)
def start_client(mysql_db_server_ip, mysql_user, mysql_password, mysql_db_name,
                    REDIS_HOST, REDIS_PORT, REDIS_db):
    url = SERVER_URL
    refresh_token = SERVER_REFRESH_TOKEN
    dh = DeviceHive(ClientHandler,'IoTServer',
                    mysql_db_server_ip, mysql_user, mysql_password, mysql_db_name,
                    REDIS_HOST, REDIS_PORT, REDIS_db
                    )
    dh.connect(url, refresh_token=refresh_token)


