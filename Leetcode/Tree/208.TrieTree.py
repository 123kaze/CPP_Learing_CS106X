class Trie:

    def __init__(self):
        self.child = [None] * 26
        self.isEnd = False

    def searchPrefix(self, pre: str) -> "Trie":
        node = self
        for ch in pre:
            idx = ord(ch) - ord("a")
            if node.child[idx] is None:
                return None
            node = node.child[idx]
        return node

    def insert(self, word: str) -> None:
        node = self
        for ch in word:
            idx = ord(ch) - ord("a")
            if node.child[idx] is None:
                node.child[idx] = Trie()
            node = node.child[idx]
        node.isEnd = True

    def search(self, word: str) -> bool:
        node = self.searchPrefix(word)
        return node is not None and node.isEnd

    def startsWith(self, prefix: str) -> bool:
        node = self.searchPrefix(prefix)
        return node is not None


# Your Trie object will be instantiated and called as such:
# obj = Trie()
# obj.insert(word)
# param_2 = obj.search(word)
# param_3 = obj.startsWith(prefix)


# 调库办法
class Trie:

    def __init__(self):
        self.word_tree = {}
        self.word = set()

    def insert(self, word: str) -> None:
        self.word.add(word)
        pre_node = self.word_tree
        for c in word:
            if c not in pre_node:
                pre_node[c] = {}
            pre_node = pre_node[c]

    def search(self, word: str) -> bool:
        return word in self.word

    def startsWith(self, prefix: str) -> bool:
        pre_node = self.word_tree
        for c in prefix:
            if c in pre_node:
                pre_node = pre_node[c]
                continue
            return False
        return True
