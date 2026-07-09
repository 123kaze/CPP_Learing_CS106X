import functools

def myfunc(a, b=2):
    "myfunc() 的文档字符串"
    print('  调用 myfunc 的参数：', (a, b))

def show_details(name, f, is_partial=False):
    "显示一个可调用对象的细节"
    print('{}:'.format(name))
    print('  对象：', f)
    if not is_partial:
        print('  __name__:', f.__name__)
    if is_partial:
        print('  func:', f.func)
        print('  args:', f.args)
        print('  keywords:', f.keywords)
    return

show_details('myfunc', myfunc)
myfunc('a', 3)
print()

# 为参数 b 设置另一个默认值
# 但要求调用者提供参数 a
p1 = functools.partial(myfunc, b=4)
show_details('默认关键词参数的偏对象', p1, True)
p1('传递参数 a')
p1('覆盖参数 b', b=5)
print()

# 为参数 a 与 b 都设置默认值
p2 = functools.partial(myfunc, '默认的参数 a', b=99)

show_details('多个默认值的偏对象', p2, True)