import os,sys,win32api
import time

def file_reader(filepath):

    try:
        fp = open(filepath,'r',encoding='utf-8')
        content =fp.read()
    except:
        fp = open(filepath,'r',encoding='gbk')
    fp.close()
    return content

def file_write(filepath,filecontent):
    fp = open(filepath, 'w',encoding='utf-8')
    fp.write(filecontent)
    fp.close()

def format_date(format="%Y-%m-%d %H:%M:%S", times=None):
    if not times: times = int(time.time())
    time_local = time.localtime(times)
    return time.strftime(format, time_local)

def get_resources(path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, path)

def format_utc_time(timestamp):
    t = timestamp.replace('Z', '').replace('T', ' ').split('.')
    timestamp = int(time.mktime(time.strptime(t[0], '%Y-%m-%d %H:%M:%S')) + 8 * 3600)
    if len(t) ==2:
        timestamp = int(str(timestamp) + t[1])
    else:
        import random
        timestamp = int(str(timestamp) + str(random.randint(0,999)))
    return timestamp



def get_rootpath():
    if getattr(sys, 'frozen', False):
        absPath = os.path.dirname(os.path.abspath(sys.executable))
    elif __file__:
        absPath = os.path.dirname(os.path.abspath(__file__))
    return absPath + "\\"

def getFileVersion(file_name):
    try:
        info = win32api.GetFileVersionInfo(file_name, os.sep)
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        version = '%d.%d.%d.%d' % (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))
        return version
    except Exception as e:
        return "None"


def console_log(content, show=True):
    console = "[%s]%s" % (format_date(), content)
    color_id = 37
    level = 'LOG'
    if str_include(console, '[INFO]') != -1:
        color_id = 32
        level = 'INFO'
    if str_include(console, '[WARNING]') != -1:
        color_id = 33
        level = 'WARNING'
    if str_include(console, '[ERROR]') != -1:
        color_id = 31
        level = 'ERROR'
    log = "\033[%dm%s\033[0m" % (color_id, console)
    print(log)

def str_include(str, include):
    try:
        index = str.index(include)
        return index
    except:
        return -1