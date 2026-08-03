from collections import Counter

def query1(nums):
    c = Counter(nums)
    res = []
    for num in nums:
        res.append(c[num])

    return res
def query(nums,k):
    for _ in range(k):
        nums = query1(nums)

    return nums


if __name__ == '__main__':
    nums = 