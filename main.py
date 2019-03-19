#!/bin/python
from client import start_client
from configManager import ConfigManager

if __name__ == '__main__':
    cm=ConfigManager()
    mysql_db_server_ip=cm.getConfigValue('mysql_db_server_ip')
    mysql_user=cm.getConfigValue('mysql_user')
    mysql_password=cm.getConfigValue('mysql_password')
    mysql_db_name=cm.getConfigValue('mysql_db_name')
    REDIS_HOST=cm.getConfigValue('REDIS_HOST')
    REDIS_PORT=cm.getConfigValue('REDIS_PORT')
    REDIS_db=cm.getConfigValue('REDIS_db')
    if mysql_db_server_ip is None or mysql_db_server_ip=='':
        raise Exception('mysql_db_server_ip is not configured')
    if mysql_user is None or mysql_db_server_ip=='':
        raise Exception('mysql_user is not configured')
    if mysql_password is None or mysql_db_server_ip=='':
        raise Exception('mysql_password is not configured')
    if mysql_db_name is None or mysql_db_server_ip=='':
        raise Exception('mysql_db_name is not configured')
    if REDIS_HOST is None or mysql_db_server_ip=='':
        raise Exception('REDIS_HOST is not configured')
    if REDIS_PORT is None or mysql_db_server_ip=='':
        raise Exception('REDIS_PORT is not configured')
    if REDIS_db is None or mysql_db_server_ip=='':
        raise Exception('REDIS_db is not configured')
    start_client(mysql_db_server_ip, mysql_user, mysql_password, mysql_db_name,
                    REDIS_HOST, REDIS_PORT, REDIS_db)