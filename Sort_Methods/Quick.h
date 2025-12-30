// quicksort.h
#ifndef QUICKSORT_H
#define QUICKSORT_H

#include <vector>
#include <algorithm>

/**
 * @file quicksort.h
 * @brief 快速排序算法实现
 * 
 * 提供快速排序算法的分区和排序函数
 */

/**
 * @brief 分区函数（原percision函数）
 * 
 * 使用Hoare分区方案，将数组分为两部分：
 * - 左边：小于等于pivot的元素
 * - 右边：大于等于pivot的元素
 * 
 * @param a 待排序的数组引用
 * @param left 分区左边界（包含）
 * @param right 分区右边界（包含）
 * @return int 分区后pivot元素的最终位置
 */
int partition(std::vector<int>& a, int left, int right);

/**
 * @brief 快速排序主函数
 * 
 * 对数组a中[left, right]范围内的元素进行快速排序
 * 
 * @param a 待排序的数组引用
 * @param left 排序左边界
 * @param right 排序右边界
 */
void quickSort(std::vector<int>& a, int left, int right);

#endif // QUICKSORT_H