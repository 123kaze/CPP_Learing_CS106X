def quickSort(nums,left,right):
    '''
    '''
    if right-left<=1:
        return nums[left:right]
    pivoit = nums[right-1]
    i = left
    j = right-2

    while i<=j:
        if nums[i]<=pivoit:
            i+=1
            continue
        if nums[j]>pivoit:
            j-=1
            continue
        nums[i],nums[j] = nums[j],nums[i]
        i+=1
        j-=1
    
    nums[i],nums[right-1]=nums[right-1],nums[i]
    left1 = quickSort(nums,left,i)
    right1 = quickSort(nums,i+1,right)
    return left1+[pivoit]+right1

def quicksort_inplace(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        quicksort_inplace(arr, low, pi - 1)
        quicksort_inplace(arr, pi + 1, high)

def partition(nums,low,high):
    pivot = nums[high]
    i = low-1
    for j in range(low,high):
        if nums[j]<=pivot:
            i+=1
            nums[i],nums[j]=nums[j],nums[i]
    nums[i+1],nums[high] = nums[high],nums[i+1]
    return i+1


nums = [2,3,4,7,5]
n = len(nums)
nums = quickSort(nums,0,n)
print(nums)
