from collections import defaultdict
from typing import List
class Solution:
    def longestWord(self, words: List[str]) -> str:
        words.sort(key=lambda x:( -len(x),x))
        wordset = set(words)
        def can_form(word,flag):
            if not word:
                return True

            for i in range(1,len(word)+1):
                prfix = word[:i]
                if prfix in wordset and (not flag or i != len(word)):
                    if can_form(word[i:], False):
                        return True

            return False

        for w in words:
            if can_form(w, True):
                return w

        return ""
