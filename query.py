from datetime import datetime
from sqlalchemy.sql import func, label
from model import MonthBook, MonthSale, MonthSold, WeekBook, WeekSale, WeekSold, Session

import pandas as pd

ZHUZHAI = ('多层住宅', '高层住宅', '小高层住宅')
BANGONG = ('其它办公', '挑高公寓办公', '平层公寓办公', '乙级办公', '甲级办公')
SHANGYE = ('底商商业', '专业市场商业', '集中商业', '街区商业', '其它商业')
BIESHU = ('叠加别墅', '独立别墅', '双拼别墅', '联排别墅')


def todate(text):
    return datetime.strptime(text, '%Y-%m-%d').date()


class Query:
    s = Session()
    query = s.query

    def dateframe(self, query, index_col):
        return pd.read_sql(query.statement, self.s.bind, index_col=index_col)

    def gxj(self, by, date_range=None, plate=None, zone=None, usage=ZHUZHAI, output_by='range'):
        if output_by == 'range':
            df_group_key = '年月' if by == 'Month' else '星期'
        elif output_by == 'plate':
            df_group_key = '板块'
        elif output_by == 'zone':
            df_group_key = '片区'
        q_sale, q_sold = self.gxj_query(date_range, plate, usage, zone, by)
        # 上市表
        df_sale = self.dateframe(q_sale, df_group_key).groupby(df_group_key).sum()
        df_sale['上市面积'] = (df_sale['上市面积'] / 1e4)
        # 成交表
        df_sold = self.dateframe(q_sold, df_group_key).groupby(df_group_key).sum()
        df_sold['成交均价'] = df_sold['成交金额'] / df_sold['成交面积']
        df_sold['成交面积'] = (df_sold['成交面积'] / 1e4)

        # 合并
        df = pd.concat((df_sale, df_sold), axis=1)
        df = df[['上市面积', '成交面积', '成交均价']]
        df[['上市面积', '成交面积']] = df[['上市面积', '成交面积']].round(2).fillna(0)
        df['成交均价'] = df['成交均价'].round(0)
        return df

    def gxj_query(self, date_range, plate, usage, zone, by):
        # 根据by确定在哪张表里查询
        sale = eval(f'{by}Sale')
        sold = eval(f'{by}Sold')
        date_key = 'date' if by == 'Month' else 'week'

        # 时间
        # 上市
        sale_keys = (
            eval(f'sale.{date_key}'),
            sale.plate,
            sale.zone,
            sale.usage
        )
        q_sale = self.query(
            *sale_keys,
            func.sum(sale.space).label('上市面积')
        ) \
            .group_by(
            *sale_keys
        ) \
            .filter(
            eval(f'sale.{date_key}') >= date_range[0],
            eval(f'sale.{date_key}') <= date_range[1]
        )
        # 成交
        sold_keys = (
            eval(f'sold.{date_key}'),
            sold.plate,
            sold.zone,
            sold.usage
        )
        q_sold = self.query(
            *sold_keys,
            func.sum(sold.space).label('成交面积'),
            func.sum(sold.money).label('成交金额')
        ) \
            .group_by(
            *sold_keys
        ) \
            .filter(
            eval(f'sold.{date_key}') >= date_range[0],
            eval(f'sold.{date_key}') <= date_range[1]
        )
        # 功能
        q_sale = q_sale.filter(sale.usage.in_(usage))
        q_sold = q_sold.filter(sold.usage.in_(usage))
        # 地区
        if plate:
            q_sale = q_sale.filter(sale.plate == plate)
            q_sold = q_sold.filter(sold.plate == plate)
        if zone:
            q_sale = q_sale.filter(sale.zone == zone)
            q_sold = q_sold.filter(sold.zone == zone)

        return q_sale, q_sold


if __name__ == '__main__':
    q = Query()
    a = todate('2017-09-01')
    b = todate('2017-09-01')
    df = q.gxj(by='Month', date_range=(a, b), usage=ZHUZHAI, output_by='plate')
    print(df)
