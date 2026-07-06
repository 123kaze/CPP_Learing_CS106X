# #include <iostream>
#include <threads.h>

class Th
_Exported on 07/06/2026 at 08:44:40 GMT+8 from Claude via WayLog_


**User**

#include <iostream>
#include <threads.h>

class ThreadPool {
public:
    explicit ThreadPool(size_t threads) : stop_(false) {
        for (size_t i = 0; i < threads; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(mutex_);
                        cv_.wait(lock, [this] { 
                            return stop_ || !tasks_.empty(); 
                        });
                        if (stop_ && tasks_.empty()) return;
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }

    template<class F, class... Args>
    auto submit(F&& f, Args&&... args) 
        -> std::future<std::invoke_result_t<F, Args...>> 
    {
        using return_type = std::invoke_result_t<F, Args...>;
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        std::future<return_type> result = task->get_future();
        {
            std::lock_guard<std::mutex> lock(mutex_);
            tasks_.emplace([task]() { (*task)(); });
        }
        cv_.notify_one();
        return result;
    }

    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& w : workers_) w.join();
    }

private:
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex mutex_;
    std::condition_variable cv_;
    bool stop_;
};补充一下头文件

---


**Claude**

已补充所有需要的头文件，并替换掉错误的 `<threads.h>`（C 头文件）：

| 头文件 | 用途 |
|---|---|
| `<vector>` | `std::vector` |
| `<queue>` | `std::queue` |
| `<thread>` | `std::thread` |
| `<mutex>` | `std::mutex`, `std::unique_lock`, `std::lock_guard` |
| `<condition_variable>` | `std::condition_variable` |
| `<functional>` | `std::function`, `std::bind` |
| `<future>` | `std::future`, `std::packaged_task` |
| `<memory>` | `std::make_shared` |

---
