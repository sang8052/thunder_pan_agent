
from peewee import *
from . import base

class dbConfig(base.BaseModel):

    keyword = CharField(help_text='数据库的关键字')
    value = CharField(help_text='对应的值')

