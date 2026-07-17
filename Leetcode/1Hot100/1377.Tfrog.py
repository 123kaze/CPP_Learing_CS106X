from collections import defaultdict
from typing import List

class Solution:
    def frogPosition(self, n: int, edges: List[List[int]], t: int, target: int) -> float:

        ke = defaultdict(list)
        for i,j in edges:
            ke[j].append(i)
            ke[i].append(j)

        def dfs(time,cur,parent,prob:float):
            '''
            dfs(time,cur,parent,prob) =
            :param time: current time
            :param cur: current node
            :param parent: parent node
            :param prob: probability
            :return: the probability = result， 从父亲开始走到这一步的概率
            如果 t == times ，那么概率就相等，直接返回，是路径乘积
            如果 t > times ， 而且target是叶节点
            如果 t > times ， 而且tar不是叶节点，那么0
            如果 t < times ,  那么直接0
            '''

            if time > t:
                return 0.0

            children = [c for c in ke[cur] if parent != c]
            nums = len(children)

            if cur == target:
                if nums == 0 or t == time:
                    return prob
                else:
                    return 0.0

            if nums == 0:
                return 0.0

            for child in children:
                if child != parent:
                    result = dfs(time+1,child,cur,prob/nums)
                    if result > 0:
                        return result

            return 0.0


        return dfs(0,1,1,1.0)





