from smartfast.smartir.operations.call import Call
from smartfast.core.variables.variable import Variable
from smartfast.core.declarations.solidity_variables import SolidityVariable


class Transfer(Call):
    def __init__(self, destination, value):
        assert isinstance(destination, (Variable, SolidityVariable))
        self._destination = destination
        super().__init__()

        self._call_value = value

    def can_send_eth(self):
        return True

    @property
    def call_value(self):
        return self._call_value

    @property
    def read(self):
        return [self.destination, self.call_value]

    @property
    def destination(self):
        return self._destination

    def __str__(self):
        value = "value:{}".format(self.call_value)
        return "Transfer dest:{} {}".format(self.destination, value)
