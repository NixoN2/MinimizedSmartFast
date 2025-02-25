"""
Module detecting shadowing of state variables
"""

from smartfast.detectors.abstract_detector import AbstractDetector, DetectorClassification
from smartfast.core.declarations.function import Function, FunctionType


class StateShadowing(AbstractDetector):
    """
    Shadowing of state variable
    """

    ARGUMENT = 'shadowing-state'
    HELP = 'State variables shadowing'
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.EXACTLY

    WIKI = 'https://github.com/crytic/smartfast/wiki/Detector-Documentation#state-variable-shadowing'

    WIKI_TITLE = 'State variable shadowing'
    WIKI_DESCRIPTION = 'Detection of state variables shadowed.'
    WIKI_EXPLOIT_SCENARIO = '''
```solidity
contract BaseContract{
    address owner;

    modifier isOwner(){
        require(owner == msg.sender);
        _;
    }

}

contract DerivedContract is BaseContract{
    address owner;

    constructor(){
        owner = msg.sender;
    }

    function withdraw() isOwner() external{
        msg.sender.transfer(this.balance);
    }
}
```
`owner` of `BaseContract` is never assigned and the modifier `isOwner` does not work.'''

    WIKI_RECOMMENDATION = 'Remove the state variable shadowing.'


    def detect_shadowing(self, contract):
        ret = []
        variables_fathers = []
        variables_fathers_used = []
        for father in contract.inheritance:
            # print(father.name)
            # print("functions:")
            # print([v.name for v in father.functions+father.modifiers])
            # print([v.is_implemented for v in father.functions+father.modifiers])
            # print([v.name for v in father.functions_and_modifiers_declared])
            # print([v.is_implemented for v in father.functions_and_modifiers_declared])
            # print("is_implemented:")
        # if any(f.is_implemented for f in father.functions + father.modifiers):
            # print([v.name for v in father.state_variables_declared])
            variables_used = [list(set(v.all_state_variables_read() + v.all_state_variables_written())) for v in father.functions_and_modifiers_declared if v.function_type not in [FunctionType.CONSTRUCTOR_VARIABLES, FunctionType.CONSTRUCTOR_CONSTANT_VARIABLES]]
            variables_used = list(set([v for sub in variables_used for v in sub]))
            variables_fathers_used += variables_used
            variables_fathers += father.state_variables_declared
            # print(father.name)
            # print([v.name for v in variables_fathers_used])

        variables_fathers_used = list(set(variables_fathers_used))
        # print([v.name for v in variables_fathers_used])
        for var in contract.state_variables_declared:
            shadow = [v for v in variables_fathers if v.name == var.name and v in variables_fathers_used]
            if shadow:
                ret.append([var] + shadow)
        return ret

    def _detect(self):
        """ Detect shadowing

        Recursively visit the calls
        Returns:
            list: {'vuln', 'filename,'contract','func', 'shadow'}

        """
        results = []
        for c in self.contracts:
            # print(c.name)
            # print("----------")
            shadowing = self.detect_shadowing(c)
            if shadowing:
                for all_variables in shadowing:
                    shadow = all_variables[0]
                    variables = all_variables[1:]
                    info = [shadow, ' shadows:\n']
                    for var in variables:
                        info += ["\t- ", var, "\n"]

                    res = self.generate_result(info)
                    results.append(res)


        return results
