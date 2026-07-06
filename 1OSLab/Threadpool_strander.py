from concurrent.futures import ThreadPoolExecutor
import time
import threading


def slow_square(x):
    time.sleep(0.5)
    print(f"slow_square({x}) finished on thread {threading.get_ident()}")
    return x * x


def add(a, b):
    return a + b


with ThreadPoolExecutor(max_workers=4) as pool:
    f1 = pool.submit(add, 10, 20)
    f2 = pool.submit(lambda: 100)

    futures = []
    for i in range(1, 9):
        futures.append(pool.submit(slow_square, i))

    print("add result:", f1.result())
    print("lambda result:", f2.result())

    total = 0
    for f in futures:
        total += f.result()

    print("sum of squares:", total)