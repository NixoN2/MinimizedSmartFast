from smartfast.core.children.child_node import ChildNode
from smartfast.core.variables.variable import Variable


class TemporaryVariable(ChildNode, Variable):

    COUNTER = 0

    def __init__(self, node, index=None):
        super().__init__()
        if index is None:
            self._index = TemporaryVariable.COUNTER
            TemporaryVariable.COUNTER += 1
        else:
            self._index = index
        self._node = node

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, idx):
        self._index = idx

    @property
    def name(self):
        return "TMP_{}".format(self.index)

    def __str__(self):
        return self.name
