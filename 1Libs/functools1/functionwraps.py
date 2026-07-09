import functools

def show_details(name, f):
    "显示可调用对象的细节。"
    print('{}:'.format(name))
    print('  object:', f)
    print('  __name__:', end=' ')
    try:
        print(f.__name__)
    except AttributeError:
        print('(no __name__)')
    print('  __doc__', repr(f.__doc__))
    print()

def simple_decorator(f):
    @functools.wraps(f)
    def decorated(a='decorated defaults', b=1):
        print('  decorated:', (a, b))
        print('  ', end=' ')
        return f(a, b=b)
    return decorated

def myfunc(a, b=2):
    " myfunc() 并不复杂"
    print('  myfunc:', (a, b))
    return

# 原始函数
show_details('myfunc', myfunc)
myfunc('unwrapped, default b')
myfunc('unwrapped, passing b', 3)
print()

# 显式封装
wrapped_myfunc = simple_decorator(myfunc)
show_details('wrapped_myfunc', wrapped_myfunc)
wrapped_myfunc()
wrapped_myfunc('args to wrapped', 4)
print()

class A:
    def __init__(self, func):      # 接收被装饰的函数
        self.func = func

    def __call__(self, *args, **kwargs):
        print('对象被调用了')
        return self.func(*args, **kwargs)

# 用装饰器语法封装
@A
@simple_decorator
def decorated_myfunc(a, b):
    myfunc(a, b)
    return

show_details('decorated_myfunc', decorated_myfunc)
decorated_myfunc()
decorated_myfunc('args to decorated', 4)

decorated_myfunc(1,2)



a = A()
a()

