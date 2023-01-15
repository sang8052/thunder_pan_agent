import tools
from peewee import  *
# 设置默认的数据库的地址

db_filepath= tools.get_rootpath() + 'database.db'
db = DatabaseProxy()


class BaseModel(Model):

    class Meta:
        database = db