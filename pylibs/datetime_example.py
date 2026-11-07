"""
@file datetime_example.py
@brief Python 日期时间标准库用法示例，面向算法题

特点：
1. date 表示年月日，datetime 表示年月日和时分秒。
2. timedelta 表示时间差，自动处理跨月、跨年和闰年。
3. 日期对象不可变，可比较、排序，也可以作为字典键。
4. date / datetime 支持公历年份 1..9999，不适合任意大年份。

常用操作时间复杂度：
- 日期加减、比较、星期计算、日期序数转换：O(1)。
- 固定长度日期字符串的解析和格式化：O(1)。
- 日期列表排序：O(n log n)。
- 闭区间内某星期的出现次数：本示例用整周分解做到 O(1)。
"""

import calendar
from datetime import date, datetime, time, timedelta


def days_between(start, end):
    """返回 end - start 的天数，可为负；两端均计入时需另加 1。"""
    return (end - start).days


def add_days(day, offset):
    """返回 offset 天后的日期，offset 为负时表示往前。"""
    return day + timedelta(days=offset)


def day_of_year(day):
    """返回年内第几天，1 月 1 日为第 1 天。"""
    return (day - date(day.year, 1, 1)).days + 1


def date_from_day_of_year(year, number):
    """将某年的第 number 天还原为日期，不允许越到下一年。"""
    first = date(year, 1, 1)
    limit = 366 if calendar.isleap(year) else 365
    if not 1 <= number <= limit:
        raise ValueError("年内天数必须在 1 到当年总天数之间")
    return first + timedelta(days=number - 1)


def count_weekday(start, end, weekday):
    """统计闭区间 [start, end] 中某星期的次数，周一为 0，周日为 6。"""
    if not 0 <= weekday <= 6:
        raise ValueError("weekday 必须在 0..6 之间")
    if start > end:
        return 0
    full_weeks, extra_days = divmod((end - start).days + 1, 7)
    # 完整的一周各星期恰好一次，只需判断不足一周的尾段。
    offset = (weekday - start.weekday()) % 7
    return full_weeks + int(offset < extra_days)


def main():
    print("========== Python datetime 用法示例 ==========")

    # 1. 创建和初始化
    print("\n1. 创建和初始化:")
    day = date(2024, 2, 29)
    moment = datetime(2024, 2, 29, 23, 30, 15)
    clock = time(23, 30, 15)
    duration = timedelta(days=2, hours=3, minutes=4)
    print(f"date: {day}")
    print(f"datetime: {moment}")
    print(f"time: {clock}")
    print(f"timedelta: {duration}")
    print(f"字段访问: {day.year} 年 {day.month} 月 {day.day} 日")
    print(f"从 datetime 取日期 / 时刻: {moment.date()} / {moment.time()}")

    # 2. 字符串转日期 / 时间
    print("\n2. 字符串解析:")
    print(f"YYYY-MM-DD: {date.fromisoformat('2024-02-29')}")
    print(f"YYYYMMDD: {datetime.strptime('20240229', '%Y%m%d').date()}")
    parsed = datetime.strptime("2024/02/29 23:30:15", "%Y/%m/%d %H:%M:%S")
    print(f"自定义格式: {parsed}")

    # 3. 日期 / 时间转字符串
    print("\n3. 格式化输出:")
    print(f"isoformat(): {day.isoformat()}")
    print(f"strftime(): {moment.strftime('%Y/%m/%d %H:%M:%S')}")
    print("格式符: %Y 年, %m 月, %d 日, %H 时, %M 分, %S 秒")

    # 4. 日期偏移和时间差
    print("\n4. 日期偏移和时间差:")
    print(f"2024-02-28 的 2 天后: {add_days(date(2024, 2, 28), 2)}")
    print(f"2025-01-01 的 1 天前: {add_days(date(2025, 1, 1), -1)}")
    print(f"跨越午夜: {moment + timedelta(hours=1)}")
    gap = datetime(2024, 3, 2, 1, 0) - datetime(2024, 2, 29, 0, 0)
    print(f"时间差: {gap}, days={gap.days}, seconds={gap.seconds}")
    print(f"总秒数 total_seconds(): {gap.total_seconds()}")
    negative = timedelta(seconds=-1)
    print(f"负一秒: days={negative.days}, seconds={negative.seconds}")
    print(f"负一秒的总秒数: {negative.total_seconds()}")

    # 5. 比较、排序和星期
    print("\n5. 比较、排序和星期:")
    dates = [date(2024, 3, 1), date(2023, 12, 31), day]
    print(f"排序: {[d.isoformat() for d in sorted(dates)]}")
    print(f"2024-02-29 < 2024-03-01: {day < date(2024, 3, 1)}")
    names = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
    print(f"{day}: weekday()={day.weekday()}, {names[day.weekday()]}")
    print(f"isoweekday()={day.isoweekday()} (周一 1, 周日 7)")

    # 6. 闰年、月份天数和日期合法性
    print("\n6. calendar 辅助判断:")
    for year in (1900, 2000, 2024, 2025):
        print(f"{year} 年是闰年: {calendar.isleap(year)}")
    first_weekday, month_days = calendar.monthrange(2024, 2)
    print(f"2024 年 2 月: 月初 weekday={first_weekday}, 共 {month_days} 天")
    try:
        date(2025, 2, 29)
    except ValueError:
        print("2025-02-29 无效，date 构造时会抛出 ValueError")
    print(f"replace 返回新对象: {day.replace(day=28)}, 原对象仍为 {day}")

    # 7. 算法题应用
    print("\n7. 算法题应用:")
    start, end = date(2024, 2, 28), date(2024, 3, 1)
    print(f"场景1: 两日期相差 {days_between(start, end)} 天")
    print(f"        若两端都计入，则有 {days_between(start, end) + 1} 天")
    print(f"场景2: {day} 是当年的第 {day_of_year(day)} 天")
    print(f"        2024 年第 60 天是 {date_from_day_of_year(2024, 60)}")
    ordinal = day.toordinal()
    print(f"场景3: 日期离散化: {day} -> {ordinal} -> {date.fromordinal(ordinal)}")
    monday = date(2024, 1, 1)
    sunday = date(2024, 1, 14)
    print(f"场景4: [{monday}, {sunday}] 内有 {count_weekday(monday, sunday, 0)} 个周一")

    # 8. 注意事项
    print("\n8. 注意事项:")
    print("1. 只处理年月日用 date，不需要自行枚举每个月的天数")
    print("2. timedelta 不支持 months / years，月份不能统一按 30 天计算")
    print("3. seconds 是去掉整天后的秒数，总秒数取 total_seconds()")
    print("4. time 对象不能直接相减；先用 datetime.combine(day, clock) 结合日期")
    print("5. 超出年份 1..9999 或非公历日期题，应自己实现日期规则")
    print("\n========== datetime 示例结束 ==========")


if __name__ == "__main__":
    main()
