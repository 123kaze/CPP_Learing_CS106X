import queue
import threading
import time
from concurrent.futures import Future


class ThreadPool:
    def __init__(self, num_threads):
        self.tasks = queue.Queue()
        self.stop = False
        self.workers = []

        for _ in range(num_threads):
            t = threading.Thread(target=self.worker)
            t.start()
            self.workers.append(t)

    def worker(self):
        while True:
            item = self.tasks.get()

            if item is None:
                break

            func, args, kwargs, future = item

            try:
                result = func(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            finally:
                self.tasks.task_done()

    def submit(self, func, *args, **kwargs):
        future = Future()
        self.tasks.put((func, args, kwargs, future))
        return future

    def shutdown(self):
        for _ in self.workers:
            self.tasks.put(None)

        for t in self.workers:
            t.join()