import abc
from smartfast.core.context.context import Context
from smartfast.core.children.child_expression import ChildExpression
from smartfast.core.children.child_node import ChildNode
from smartfast.utils.utils import unroll


class AbstractOperation(abc.ABC):
    @property
    @abc.abstractmethod
    def read(self):
        """
        Return the list of variables READ
        """
        pass  # pylint: disable=unnecessary-pass

    @property
    @abc.abstractmethod
    def used(self):
        """
        Return the list of variables used
        """
        pass  # pylint: disable=unnecessary-pass


class Operation(Context, ChildExpression, ChildNode, AbstractOperation):
    @property
    def used(self):
        """
        By default used is all the variables read
        """
        return self.read

    # if array inside the parameters
    @staticmethod
    def _unroll(l):
        return unroll(l)
