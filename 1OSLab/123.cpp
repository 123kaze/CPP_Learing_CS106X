#include "Threadpool.cpp"

#include <chrono>
#include <string>

int add(int a, int b) {
    return a + b;
}

std::string makeMessage(const std::string& name, int score) {
    return name + " got " + std::to_string(score) + " points";
}

int slowSquare(int x) {
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    std::cout << "slowSquare(" << x << ") finished on thread "
              << std::this_thread::get_id() << std::endl;
    return x * x;
}

void printJob(const std::string& text) {
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    std::cout << "printJob: " << text
              << " on thread " << std::this_thread::get_id() << std::endl;
}

int main() {
    ThreadPool pool(4);

    auto f1 = pool.submit(add, 10, 20);

    auto f2 = pool.submit([] {
        return 100;
    });

    auto f3 = pool.submit(makeMessage, "Alice", 95);

    auto f4 = pool.submit([](int a, int b) {
        return a * b;
    }, 6, 7);

    auto f5 = pool.submit(printJob, "this task returns void");

    std::vector<std::future<int>> squares;
    for (int i = 1; i <= 8; ++i) {
        squares.push_back(pool.submit(slowSquare, i));
    }

    std::cout << "add result: " << f1.get() << std::endl;
    std::cout << "lambda result: " << f2.get() << std::endl;
    std::cout << "message result: " << f3.get() << std::endl;
    std::cout << "multiply result: " << f4.get() << std::endl;

    f5.get();
    std::cout << "void task finished" << std::endl;

    int sum = 0;
    for (auto& future : squares) {
        sum += future.get();
    }
    std::cout << "sum of squares: " << sum << std::endl;
}
