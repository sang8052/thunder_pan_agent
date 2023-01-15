import requests
import json,tools,time
from datetime import  datetime

from peewee import *
from models import config

def get_db_config(keyword):
   oconfig = config.dbConfig().select().where(config.dbConfig.keyword == keyword)
   if len(oconfig) > 0:
      return oconfig[0].value
   else:
      return None

def get_captcha_token():
    expire_time = get_db_config('captcha.expires_at')
    expire_time = int(expire_time)
    if expire_time > int(time.time()):
        return  get_db_config('captcha.token')
    else:
        tools.console_log('[INFO]更新 captcha_token')
        url = "https://xluser-ssl.xunlei.com/v1/shield/captcha/init"
        device = {
            "action": "get:/drive/v1/tasks",
            "client_id": get_db_config('captcha.client_id'),
            "device_id": get_db_config('captcha.device_id'),
            "meta": {
                "captcha_sign": get_db_config('captcha.captcha_sign'),
                "client_version":get_db_config('captcha.client_version'),
                "email": "",
                "package_name": get_db_config('captcha.package_name'),
                "phone_number": "",
                "timestamp": get_db_config('captcha.timestamp'),
                "user_id": get_db_config('captcha.user_id'),
                "username": ""
            }
        }
        headers = {
            'Content-Type': 'text/plain;charset=UTF-8',
            'Origin': 'https://pan.xunlei.com',
            'Referer': 'https://pan.xunlei.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        }
        response = requests.request("POST", url, headers=headers, data=json.dumps(device))
        response =  json.loads(response.text)
        config.dbConfig.update(value = response['captcha_token']).where(config.dbConfig.keyword == 'captcha.token').execute()
        config.dbConfig.update(value =str(int(time.time()) + 300)).where(config.dbConfig.keyword == 'captcha.expires_at').execute()
        tools.console_log('[INFO]新的 captcha_token: ' + response['captcha_token'] )
        return response['captcha_token']

def get_authorization_token():
    expire_time = get_db_config('credentials.expires_at')
    expire_time = int(expire_time)
    if expire_time > int(time.time()):
        return get_db_config('credentials.access_token')
    else:
        tools.console_log('[INFO]更新 access_token')
        url = "https://xluser-ssl.xunlei.com/v1/auth/token"
        #device = json.loads(tools.file_reader('device.json'))
        payload = json.dumps({
            "client_id": get_db_config('captcha.client_id'),
            "grant_type": "refresh_token",
            "refresh_token":get_db_config('credentials.refresh_token')
        })
        headers = {
            'content-type': 'application/json',
            'origin': 'https://pan.xunlei.com',
            'referer': 'https://pan.xunlei.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'x-action': '401',
            'x-client-id': get_db_config('captcha.client_id'),
            'x-device-id': get_db_config('captcha.device_id'),
            'x-device-sign': get_db_config('device_id'),
            'x-protocol-version': '301',
            'x-sdk-version': '3.4.20'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response = json.loads(response.text)
        config.dbConfig.update(value=response['access_token']).where(config.dbConfig.keyword == 'credentials.access_token').execute()
        config.dbConfig.update(value=response['refresh_token']).where(config.dbConfig.keyword == 'credentials.refresh_token').execute()
        config.dbConfig.update(value=str(int(time.time()) + 43200)).where(config.dbConfig.keyword == 'credentials.expires_at').execute()

        tools.console_log('[INFO]新的 access_token: ' +  response['access_token'])
        tools.console_log('[INFO]新的 refresh_token: ' +response['refresh_token'])
        return response['access_token']