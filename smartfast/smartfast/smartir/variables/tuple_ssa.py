"""
    This class is used for the SSA version of smartIR
    It is similar to the non-SSA version of smartIR
    as the TupleVariable are in SSA form in both version
"""
from smartfast.smartir.variables.tuple import TupleVariable


class TupleVariableSSA(TupleVariable):  # pylint: disable=too-few-public-methods
    def __init__(self, t):
        super().__init__(t.node, t.index)

        self._non_ssa_version = t

    @property
    def non_ssa_version(self):
        return self._non_ssa_version
