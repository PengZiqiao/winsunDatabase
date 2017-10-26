import json
import os

from lxml import etree
from winsun.tools import GisSpider

from model import MonthBook, MonthSale, MonthSold, WeekBook, WeekSale, WeekSold
from model import Session, MianjiDuan, DanjiaDuan, ZongjiaDuan, TaoXing
from query import todate

path = 'E:/gisDataBase'


def load(filename):
    with open(f'{path}/{filename}.json') as f:
        return json.load(f)


def jiegou(by):
    arg = {
        '面积段': (MianjiDuan, 'acreage'),
        '单价段': (DanjiaDuan, 'aveprice'),
        '总价段': (ZongjiaDuan, 'tprice')
    }[by]
    s = Session()
    obj = load(arg[1])
    for rec in obj:
        m = arg[0]()
        m.id = rec['id']
        m.name = rec[by]
        m.low = rec[f'{arg[1]}_low']
        m.high = rec[f'{arg[1]}_high']
        s.add(m)
    s.commit()


def type():
    s = Session()
    obj = load('type')
    for rec in obj:
        m = TaoXing()
        m.id = rec['id']
        m.name = rec['套型']
        print(m)
        s.add(m)
    s.commit()


def market(obj, by):
    model = {
        'month_book': MonthBook,
        'month_sale': MonthSale,
        'month_sold': MonthSold,
        'week_book': WeekBook,
        'week_sale': WeekSale,
        'week_sold': WeekSold
    }[by]
    s = Session()
    for rec in obj:
        m = model()
        m.id = rec['id']
        m.dist = rec['区属']
        m.plate = rec['板块']
        m.zone = rec['片区']
        m.usage = rec['功能']
        m.set = rec['件数']
        m.space = rec['面积']
        m.price = rec['均价']
        m.money = rec['金额']
        m.mjd_id = rec['面积段']
        m.djd_id = rec['单价段']
        m.zjd_id = rec['总价段']
        m.taoxing_id = rec['套型']
        m.proj_id = rec['prjid']
        m.proj_name = rec['projectname']
        m.pop_name = rec['popularizename']
        m.permit_id = rec['permitid']
        m.permit_no = rec['permitno']
        m.permit_date = todate(rec['perdate'])
        m.update_time = rec['update_time']
        m.presaleid = rec['presaleid']
        if 'month' in by:
            m.date = todate(rec['年月'])
        else:
            m.week = rec['星期']
            m.start = todate(rec['start_date'])
            m.end = todate(rec['end_date'])
        s.add(m)
    s.commit()


def init_db():
    for by in ['面积段', '总价段', '总价段']:
        jiegou(by)
    type()

    walk = list(list(os.walk(path)))[1:]
    for path_, _, files in walk:
        by = path_.split('\\')[1]
        for file in files:
            print(by, file)
            obj = load(f"{by}/{file.replace('.json','')}")
            market(obj, by)


class GisAPI:
    def __init__(self):
        self.path = 'E:/gisDataBase'

        # 通过selenium登陆gis
        g = GisSpider()
        self.driver = g.driver
        self.wait = g.wait

        self.wait.until(lambda driver: driver.find_element_by_link_text("更改密码"))

        # 获得日期选项
        self.driver.get('http://winsun.house365.com/sys/dataout')
        self.wait.until(lambda driver: driver.find_element_by_name("m2"))
        tree = etree.HTML(self.driver.page_source)
        self.week_option = tree.xpath("//select[@name='w2']/option/@value")
        self.month_option = tree.xpath("//select[@name='m2']/option/@value")

    def get(self, **kwargs):
        # get
        url = 'http://winsun.house365.com/sys/dataout/data'
        for i, each in enumerate(kwargs):
            arg = f'{each}={kwargs[each]}'
            if i == 0:
                url += f'?{arg}'
            else:
                url += f'&{arg}'
        self.driver.get(url)
        self.wait.until(lambda driver: driver.find_element_by_xpath("//pre"))
        tree = etree.HTML(self.driver.page_source)
        return tree.xpath("//pre/text()")[0]

    def write(self, file, text):
        with open(file, 'w') as f:
            f.write(text)
        return None

    def get_write(self, type_, opt, t):
        text = self.get(type=type_, t1=opt, t2=opt, t=t)
        file = f'{self.path}/{type_}_{t}/{opt}.json'
        print(file)
        self.write(file, text)
        return text

    def get_all(self):
        for type_ in ['week', 'month']:
            for t in ['sale', 'book', 'sold']:
                for opt in eval(f'self.{type_}_option'):
                    self.get_write(type_, opt, t)
        return None

    def update(self, type_):
        for t in ['sale', 'book', 'sold']:
            opt = eval(f'self.{type_}_option[0]')
            text = self.get_write(type_, opt, t)
            market(json.loads(text), f'{type_}_{t}')
        return None


if __name__ == '__main__':
    gis = GisAPI()
    type_ = input('Do you want to update week or month data?')
    gis.update(type_)
    gis.driver.close()
