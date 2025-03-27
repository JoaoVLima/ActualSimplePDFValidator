class Node:
    def __init__(self, info=''):
        self.info = info
        self.children = []

    def __str__(self):
        return self.info

    def add_child(self, child):
        self.children.append(child)
        return True

    def height(self):
        if not self.children:
            return 1
        return 1 + max([child.height() for child in self.children])

    def find_node(self, target):
        if self.info == target:
            return self

        for child in self.children:
            if child.info == target:
                return child
            found = child.find_node(target)
            if found:
                return found

    def print(self, level=0):
        result = "\t" * level + str(self) + "\n"
        for child in self.children:
            result += child.print(level + 1)
        return result


class Tree:
    def __init__(self, root=None):
        if root and not isinstance(root, Node):
            root = Node(root)
        self.root = root

    def __str__(self):
        return self.print()

    def is_empty(self):
        return self.root is None

    def height(self):
        return self.root.height()

    def find_node(self, target):
        if self.is_empty():
            return None
        return self.root.find_node(target)

    def add_child(self, target, node):
        if self.is_empty():
            return None

        if not isinstance(target, Node):
            target = self.find_node(target)

        if not isinstance(node, Node):
            node = Node(node)

        return target.add_child(node)

    def print(self):
        if self.is_empty():
            return ''
        return self.root.print()
