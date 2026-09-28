"""枚举满足每个人喜好的分书方案。"""

from collections.abc import Iterator
import sys


def enumerate_assignments(
    preferences: list[list[int]], book_count: int
) -> Iterator[tuple[int, ...]]:
    """按字典序生成所有不重复的书籍分配方案。"""
    person_count = len(preferences)
    assigned_books = [False] * book_count
    assignment = [0] * person_count

    def backtrack(person: int):
        if person == person_count:
            yield tuple(assignment)
            return

        for book in range(book_count):
            if not preferences[person][book] or assigned_books[book]:
                continue

            assigned_books[book] = True
            assignment[person] = book + 1
            yield from backtrack(person + 1)
            assigned_books[book] = False

    yield from backtrack(0)


def read_problem() -> tuple[list[list[int]], int] | None:
    """读取人数、书籍数及喜好关系矩阵。"""
    first_line = sys.stdin.buffer.readline().split()
    if not first_line:
        return None

    person_count, book_count = map(int, first_line)
    preferences = [
        list(map(int, sys.stdin.buffer.readline().split()))
        for _ in range(person_count)
    ]
    return preferences, book_count


def main() -> None:
    problem = read_problem()
    if problem is None:
        return

    preferences, book_count = problem
    for assignment in enumerate_assignments(preferences, book_count):
        print("(" + ", ".join(map(str, assignment)) + ")")


if __name__ == "__main__":
    main()
