from smartfast.core.solidity_types import ElementaryType
from smartfast.smartir.operations.lvalue import OperationWithLValue
from smartfast.smartir.utils.utils import is_valid_lvalue, is_valid_rvalue


class CodeSize(OperationWithLValue):
    def __init__(self, value, lvalue):
        super().__init__()
        assert is_valid_rvalue(value)
        assert is_valid_lvalue(lvalue)
        self._value = value
        self._lvalue = lvalue
        lvalue.set_type(ElementaryType("uint256"))

    @property
    def read(self):
        return [self._value]

    @property
    def value(self):
        return self._value

    def __str__(self):
        return "{} -> CODESIZE {}".format(self.lvalue, self.value)
