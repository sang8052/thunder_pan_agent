import os.path
import time

import tools,auth
import requests,json
import colorama


from flask import Flask,jsonify,request
from gevent import pywsgi

app = Flask(__name__)


from peewee import *
from models import base,config

from selenium import webdriver as wb
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities




def init_login():
   tools.console_log('[INFO]Selenium 组件初始化中...')
   chrome_driver = r"resources/chromedriver.exe"
   chrome_app = r"resources/chrome.exe"
   chrome_driver = tools.get_resources(chrome_driver)
   tools.console_log('[INFO]chrome_driver path:' + chrome_driver)
   chrome_app = tools.get_resources(chrome_app)
   tools.console_log('[INFO]chrome_app path:' + chrome_driver)
   capabilities = DesiredCapabilities.CHROME
   capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
   s = Service(chrome_driver)
   chrome_options = wb.ChromeOptions()
   chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
   chrome_options.add_argument("--start-maximized")
   chrome_options.add_argument("--no-sandbox")
   chrome_options.add_argument("--disable-cache")
   chrome_options.add_argument("--disable-extensions")
   chrome_options.binary_location = chrome_app

   tools.console_log('[INFO]Selenium 组件初始化结束')

   if not os.path.exists(base.db_filepath):
      initTable = True
   else:
      initTable = False

   db = base.db
   db.initialize(SqliteDatabase(base.db_filepath, pragmas={'journal_mode': 'wal'}))
   db.connect()
   if initTable:
      db.create_tables([config.dbConfig])
      tools.console_log('[INFO]数据库初始化成功!')

   # 检测数据库中是否已经设置了 用户的账户信息
   oconfig = config.dbConfig().select().where(config.dbConfig.keyword == 'device_id')
   if len(oconfig) == 0:
      tools.console_log('[WARNING]请先登录迅雷账户!')
      b = wb.Chrome(service=s, options=chrome_options, desired_capabilities=capabilities)
      b.get("https://pan.xunlei.com")
      time.sleep(3)
      tools.console_log('[INFO]等待用户登录网盘中')
      isLogin = False
      while not isLogin:
         url = b.current_url
         if url == 'https://pan.xunlei.com/?path=%2F':
            isLogin = True
         else:
            isLogin = False
            time.sleep(1)

      tools.console_log('[INFO]用户登录成功')
      time.sleep(3)
      tools.console_log('获取网络请求日志')
      logs = [json.loads(log['message'])['message'] for log in b.get_log('performance')]
      for log in logs:
         try:
            if log["params"]["request"]["url"] == 'https://xluser-ssl.xunlei.com/v1/shield/captcha/init':
               postData = json.loads(log["params"]["request"]["postData"])
               captcha_request = postData
         except:
            pass

      config.dbConfig.create(keyword='captcha.client_id', value=captcha_request['client_id']).save()
      config.dbConfig.create(keyword='captcha.device_id', value=captcha_request['device_id']).save()
      for k in captcha_request['meta']:
         config.dbConfig.create(keyword='captcha.' + k, value=captcha_request['meta'][k]).save()

      localStorage = b.execute_script('return localStorage;')
      config.dbConfig.create(keyword='device_id', value=localStorage['deviceid']).save()
      for key in localStorage:
         if 'captcha' in key:
            captcha = json.loads(localStorage[key])
            captcha['expires_at'] = int(time.time()) + 300
            for k in captcha:
               config.dbConfig.create(keyword='captcha.' + k, value=captcha[k]).save()
         if 'credentials' in key:
            credentials = json.loads(localStorage[key])
            credentials['expires_at'] = int(time.time()) + 43200
            for k in credentials:
               config.dbConfig.create(keyword='credentials.' + k, value=credentials[k]).save()
      b.close()
      tools.console_log('[INFO] 写入用户 token 数据到数据库成功')

def get_db_config(keyword):
   oconfig = config.dbConfig().select().where(config.dbConfig.keyword == keyword)
   if len(oconfig) > 0:
      return oconfig[0].value
   else:
      return None


@app.route("/api",methods=['GET','POST','PUT'])
def api_index():
    return jsonify({"code":0,"msg":"","data":None})

@app.route('/api/file_list/',methods=['POST'])
def get_file_list():
    parent_id = request.json['parent_id']
    tools.console_log('列出文件信息列表,[parent_id:' + parent_id + "]")
    url = "https://api-pan.xunlei.com/drive/v1/files?parent_id="  + parent_id +\
          "&limit=1000&with_audit=true&filters=%7B%22phase%22%3A%7B%22eq%22%3A%22PHASE_TYPE_COMPLETE%22%7D%2C%22trashed%22%3A%7B%22eq%22%3Afalse%7D%7D"
    headers = {
      'Authorization': 'Bearer ' + auth.get_authorization_token(),
      'Origin': 'https://pan.xunlei.com',
      'Referer': 'https://pan.xunlei.com/',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
      'content-type': 'application/json',
      'x-client-id': get_db_config('captcha.client_id'),
      'x-device-id': get_db_config('captcha.device_id'),
    }
    headers['x-captcha-token'] = auth.get_captcha_token()
    response = requests.request("GET", url, headers=headers).text
    try:
        files = json.loads(response)['files']
        return jsonify({"code":0,"msg":"","data":files})
    except:
        return jsonify({"code": 500, "msg": "读取文件列表失败", "data": json.loads(response)})

@app.route('/api/make_dir/',methods=['POST'])
def post_make_dir():
   dirname = request.json['dirname']
   parent_id = request.json['parent_id']
   tools.console_log("新建文件夹,[parent_id:%s],[dirname:%s]" % (parent_id,dirname))
   url = "https://api-pan.xunlei.com/drive/v1/files"
   payload = {"kind": "drive#folder", "name": dirname, "parent_id": parent_id, "space": ""}
   headers = {
      'Authorization': 'Bearer ' + auth.get_authorization_token(),
      'Origin': 'https://pan.xunlei.com',
      'Referer': 'https://pan.xunlei.com/',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
      'content-type': 'application/json',
      'x-client-id': get_db_config('captcha.client_id'),
      'x-device-id': get_db_config('captcha.device_id'),
   }
   headers['x-captcha-token'] = auth.get_captcha_token()
   response = requests.request("POST", url, headers=headers, data=json.dumps(payload)).text
   try:
      files = json.loads(response)['file']['id']
      return jsonify({"code": 0, "msg": "", "data": files})
   except:
      return jsonify({"code": 500, "msg": "新建文件夹失败", "data": json.loads(response)})


@app.route('/api/delete_file/',methods=['POST'])
def patch_delete_file():
    file_id = request.json['file_id']
    tools.console_log("删除文件或文件夹,[file_id:%s]" % (file_id))
    url = "https://api-pan.xunlei.com/drive/v1/files/" + file_id + "/trash"
    headers = {
        'Authorization': 'Bearer ' + auth.get_authorization_token(),
        'Origin': 'https://pan.xunlei.com',
        'Referer': 'https://pan.xunlei.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'content-type': 'application/json',
        'x-client-id': get_db_config('captcha.client_id'),
        'x-device-id': get_db_config('captcha.device_id'),
    }
    headers['x-captcha-token'] = auth.get_captcha_token()
    response = requests.request("PATCH", url, headers=headers).text
    return jsonify({"code": 0, "msg": "删除文件成功", "data": json.loads(response)})


# 新建磁力任务
@app.route('/api/create_task/',methods=['POST'])
def post_create_task():
    magnet = request.json['magnet']
    parent_id = request.json['parent_id']

    tools.console_log("新建磁力任务,[parent_id:%s],[magnet:%s]" % (parent_id,magnet))
    url = "https://api-pan.xunlei.com/drive/v1/files"
    payload = {
                "hash":"","kind": "drive#file", "name": magnet, "params": {"require_links":"false"},
                "parent_id": parent_id,"size":0,"unionId":"","upload_type":"UPLOAD_TYPE_URL",
                "url":{"files":[],"url":magnet}
               }
    headers = {
        'Authorization': 'Bearer ' + auth.get_authorization_token(),
        'Origin': 'https://pan.xunlei.com',
        'Referer': 'https://pan.xunlei.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'content-type': 'application/json',
        'x-client-id': get_db_config('captcha.client_id'),
        'x-device-id': get_db_config('captcha.device_id'),
    }
    headers['x-captcha-token'] = auth.get_captcha_token()
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload)).text
    try:
        task_id = json.loads(response)['task']['id']
        return jsonify({"code": 0, "msg": "", "data": task_id})
    except:
        return jsonify({"code": 500, "msg": "新建任务失败", "data": json.loads(response)})

# 查询任务列表
@app.route('/api/task_list/',methods=['POST'])
def get_task_list():
   try:
      task_id = request.json['task_id']
   except:
      task_id = ''
   tools.console_log("查询任务列表,[task_id:%s]" % (task_id))
   if task_id == '':
       url = "https://api-pan.xunlei.com/drive/v1/tasks?limit=100&phaseCheck=false&page_token=&type=offline"
       headers = {
           'Authorization': 'Bearer ' + auth.get_authorization_token(),
           'Origin': 'https://pan.xunlei.com',
           'Referer': 'https://pan.xunlei.com/',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
           'content-type': 'application/json',
           'x-client-id': get_db_config('captcha.client_id'),
           'x-device-id': get_db_config('captcha.device_id'),
       }
       headers['x-captcha-token'] = auth.get_captcha_token()
       response = requests.request("GET", url, headers=headers).text
       tasks = json.loads(response)['tasks']
       return jsonify({"code": 0, "msg": "", "data": tasks})
   else:
       url = "https://api-pan.xunlei.com/drive/v1/tasks?id=" + task_id
       headers = {
           'Authorization': 'Bearer ' + auth.get_authorization_token(),
           'Origin': 'https://pan.xunlei.com',
           'Referer': 'https://pan.xunlei.com/',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
           'content-type': 'application/json',
           'x-client-id': get_db_config('captcha.client_id'),
           'x-device-id': get_db_config('captcha.device_id'),
       }
       headers['x-captcha-token'] = auth.get_captcha_token()
       response = requests.request("GET", url, headers=headers).text
       tasks = json.loads(response)['tasks']
       return jsonify({"code": 0, "msg": "", "data": tasks[0]})





@app.route('/api/file_info/',methods=['POST'])
def get_file_info():
    file_id = request.json['file_id']
    tools.console_log("查询文件详情,[file_id:%s]" % (file_id))
    url = "https://api-pan.xunlei.com/drive/v1/files/"+file_id+"?space="
    headers = {
        'Authorization': 'Bearer ' + auth.get_authorization_token(),
        'Origin': 'https://pan.xunlei.com',
        'Referer': 'https://pan.xunlei.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'content-type': 'application/json',
       'x-client-id': get_db_config('captcha.client_id'),
       'x-device-id': get_db_config('captcha.device_id'),
    }
    headers['x-captcha-token'] = auth.get_captcha_token()
    response = requests.request("GET", url, headers=headers).text
    return jsonify({"code": 0, "msg": "", "data": json.loads(response)})

if __name__ == '__main__':
   colorama.init(autoreset=True)
   init_login()
   # 启动 flask 线程
   tools.console_log('迅雷云盘 Flask Api')
   tools.console_log('Version:1.2')
   tools.console_log('Sever:http://0.0.0.0:8901')
   server = pywsgi.WSGIServer(("0.0.0.0", 8901), app)
   server.serve_forever()























