import logging
import re
from typing import List, TYPE_CHECKING, Union, Dict

from smartfast.core.declarations.function_contract import FunctionContract
from smartfast.core.expressions.literal import Literal
from smartfast.core.solidity_types.array_type import ArrayType
from smartfast.core.solidity_types.elementary_type import (
    ElementaryType,
    ElementaryTypeName,
)
from smartfast.core.solidity_types.function_type import FunctionType
from smartfast.core.solidity_types.mapping_type import MappingType
from smartfast.core.solidity_types.type import Type
from smartfast.core.solidity_types.user_defined_type import UserDefinedType
from smartfast.core.variables.function_type_variable import FunctionTypeVariable
from smartfast.solc_parsing.exceptions import ParsingError

if TYPE_CHECKING:
    from smartfast.core.declarations import Structure, Enum
    from smartfast.core.declarations.contract import Contract

logger = logging.getLogger("TypeParsing")

# pylint: disable=anomalous-backslash-in-string


class UnknownType:  # pylint: disable=too-few-public-methods
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name


def _find_from_type_name(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-arguments
    name: str,
    functions_direct_access: List["Function"],
    contracts_direct_access: List["Contract"],
    structures_direct_access: List["Structure"],
    all_structures: List["Structure"],
    enums_direct_access: List["Enum"],
    all_enums: List["Enum"],
) -> Type:
    name_elementary = name.split(" ")[0]
    if "[" in name_elementary:
        name_elementary = name_elementary[0 : name_elementary.find("[")]
    if name_elementary in ElementaryTypeName:
        depth = name.count("[")
        if depth:
            return ArrayType(ElementaryType(name_elementary), Literal(depth, "uint256"))
        return ElementaryType(name_elementary)
    # We first look for contract
    # To avoid collision
    # Ex: a structure with the name of a contract
    name_contract = name
    if name_contract.startswith("contract "):
        name_contract = name_contract[len("contract ") :]
    if name_contract.startswith("library "):
        name_contract = name_contract[len("library ") :]
    var_type = next((c for c in contracts_direct_access if c.name == name_contract), None)

    if not var_type:
        var_type = next((st for st in structures_direct_access if st.name == name), None)
    if not var_type:
        var_type = next((e for e in enums_direct_access if e.name == name), None)
    if not var_type:
        # any contract can refer to another contract's enum
        enum_name = name
        if enum_name.startswith("enum "):
            enum_name = enum_name[len("enum ") :]
        elif enum_name.startswith("type(enum"):
            enum_name = enum_name[len("type(enum ") : -1]
        # all_enums = [c.enums for c in contracts]
        # all_enums = [item for sublist in all_enums for item in sublist]
        # all_enums += contract.smartfast.enums_top_level
        var_type = next((e for e in all_enums if e.name == enum_name), None)
        if not var_type:
            var_type = next((e for e in all_enums if e.canonical_name == enum_name), None)
    if not var_type:
        # any contract can refer to another contract's structure
        name_struct = name
        if name_struct.startswith("struct "):
            name_struct = name_struct[len("struct ") :]
            name_struct = name_struct.split(" ")[0]  # remove stuff like storage pointer at the end
        # all_structures = [c.structures for c in contracts]
        # all_structures = [item for sublist in all_structures for item in sublist]
        # all_structures += contract.smartfast.structures_top_level
        var_type = next((st for st in all_structures if st.name == name_struct), None)
        if not var_type:
            var_type = next((st for st in all_structures if st.canonical_name == name_struct), None)
        # case where struct xxx.xx[] where not well formed in the AST
        if not var_type:
            depth = 0
            while name_struct.endswith("[]"):
                name_struct = name_struct[0:-2]
                depth += 1
            var_type = next((st for st in all_structures if st.canonical_name == name_struct), None)
            if var_type:
                return ArrayType(UserDefinedType(var_type), Literal(depth, "uint256"))

    if not var_type:
        var_type = next((f for f in functions_direct_access if f.name == name), None)
    if not var_type:
        if name.startswith("function "):
            found = re.findall(
                "function \(([ ()\[\]a-zA-Z0-9\.,]*?)\)(?: payable)?(?: (?:external|internal|pure|view))?(?: returns \(([a-zA-Z0-9() \.,]*)\))?",
                name,
            )
            assert len(found) == 1
            params = [v for v in found[0][0].split(",") if v != ""]
            return_values = (
                [v for v in found[0][1].split(",") if v != ""] if len(found[0]) > 1 else []
            )
            params = [
                _find_from_type_name(
                    p,
                    functions_direct_access,
                    contracts_direct_access,
                    structures_direct_access,
                    all_structures,
                    enums_direct_access,
                    all_enums,
                )
                for p in params
            ]
            return_values = [
                _find_from_type_name(
                    r,
                    functions_direct_access,
                    contracts_direct_access,
                    structures_direct_access,
                    all_structures,
                    enums_direct_access,
                    all_enums,
                )
                for r in return_values
            ]
            params_vars = []
            return_vars = []
            for p in params:
                var = FunctionTypeVariable()
                var.set_type(p)
                params_vars.append(var)
            for r in return_values:
                var = FunctionTypeVariable()
                var.set_type(r)
                return_vars.append(var)
            return FunctionType(params_vars, return_vars)
    if not var_type:
        if name.startswith("mapping("):
            # nested mapping declared with var
            if name.count("mapping(") == 1:
                found = re.findall("mapping\(([a-zA-Z0-9\.]*) => ([ a-zA-Z0-9\.\[\]]*)\)", name)
            else:
                found = re.findall(
                    "mapping\(([a-zA-Z0-9\.]*) => (mapping\([=> a-zA-Z0-9\.\[\]]*\))\)", name,
                )
            assert len(found) == 1
            from_ = found[0][0]
            to_ = found[0][1]

            from_type = _find_from_type_name(
                from_,
                functions_direct_access,
                contracts_direct_access,
                structures_direct_access,
                all_structures,
                enums_direct_access,
                all_enums,
            )
            to_type = _find_from_type_name(
                to_,
                functions_direct_access,
                contracts_direct_access,
                structures_direct_access,
                all_structures,
                enums_direct_access,
                all_enums,
            )

            return MappingType(from_type, to_type)

    if not var_type:
        raise ParsingError("Type not found " + str(name))
    return UserDefinedType(var_type)


def parse_type(t: Union[Dict, UnknownType], caller_context):
    # local import to avoid circular dependency
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    # pylint: disable=import-outside-toplevel
    from smartfast.solc_parsing.expressions.expression_parsing import parse_expression
    from smartfast.solc_parsing.variables.function_type_variable import FunctionTypeVariableSolc
    from smartfast.solc_parsing.declarations.contract import ContractSolc
    from smartfast.solc_parsing.declarations.function import FunctionSolc
    from smartfast.solc_parsing.smartfastSolc import SmartfastSolc

    # Note: for convenicence top level functions use the same parser than function in contract
    # but contract_parser is set to None
    if isinstance(caller_context, SmartfastSolc) or (
        isinstance(caller_context, FunctionSolc) and caller_context.contract_parser is None
    ):
        if isinstance(caller_context, SmartfastSolc):
            sl = caller_context.core
            next_context = caller_context
        else:
            assert isinstance(caller_context, FunctionSolc)
            sl = caller_context.underlying_function.smartfast
            next_context = caller_context.smartfast_parser
        structures_direct_access = sl.structures_top_level
        all_structuress = [c.structures for c in sl.contracts]
        all_structures = [item for sublist in all_structuress for item in sublist]
        all_structures += structures_direct_access
        enums_direct_access = sl.enums_top_level
        all_enumss = [c.enums for c in sl.contracts]
        all_enums = [item for sublist in all_enumss for item in sublist]
        all_enums += enums_direct_access
        contracts = sl.contracts
        functions = []
    elif isinstance(caller_context, (ContractSolc, FunctionSolc)):
        if isinstance(caller_context, FunctionSolc):
            underlying_func = caller_context.underlying_function
            # If contract_parser is set to None, then underlying_function is a functionContract
            # See note above
            assert isinstance(underlying_func, FunctionContract)
            contract = underlying_func.contract
            next_context = caller_context.contract_parser
        else:
            contract = caller_context.underlying_contract
            next_context = caller_context

        structures_direct_access = contract.structures + contract.smartfast.structures_top_level
        all_structuress = [c.structures for c in contract.smartfast.contracts]
        all_structures = [item for sublist in all_structuress for item in sublist]
        all_structures += contract.smartfast.structures_top_level
        enums_direct_access = contract.enums + contract.smartfast.enums_top_level
        all_enumss = [c.enums for c in contract.smartfast.contracts]
        all_enums = [item for sublist in all_enumss for item in sublist]
        all_enums += contract.smartfast.enums_top_level
        contracts = contract.smartfast.contracts
        functions = contract.functions + contract.modifiers
    else:
        raise ParsingError(f"Incorrect caller context: {type(caller_context)}")

    is_compact_ast = caller_context.is_compact_ast
    if is_compact_ast:
        key = "nodeType"
    else:
        key = "name"

    if isinstance(t, UnknownType):
        return _find_from_type_name(
            t.name,
            functions,
            contracts,
            structures_direct_access,
            all_structures,
            enums_direct_access,
            all_enums,
        )

    if t[key] == "ElementaryTypeName":
        if is_compact_ast:
            return ElementaryType(t["name"])
        return ElementaryType(t["attributes"][key])

    if t[key] == "UserDefinedTypeName":
        if is_compact_ast:
            return _find_from_type_name(
                t["typeDescriptions"]["typeString"],
                functions,
                contracts,
                structures_direct_access,
                all_structures,
                enums_direct_access,
                all_enums,
            )

        # Determine if we have a type node (otherwise we use the name node, as some older solc did not have 'type').
        type_name_key = "type" if "type" in t["attributes"] else key
        return _find_from_type_name(
            t["attributes"][type_name_key],
            functions,
            contracts,
            structures_direct_access,
            all_structures,
            enums_direct_access,
            all_enums,
        )

    if t[key] == "ArrayTypeName":
        length = None
        if is_compact_ast:
            if t.get("length", None):
                length = parse_expression(t["length"], caller_context)
            array_type = parse_type(t["baseType"], next_context)
        else:
            if len(t["children"]) == 2:
                length = parse_expression(t["children"][1], caller_context)
            else:
                assert len(t["children"]) == 1
            array_type = parse_type(t["children"][0], next_context)
        return ArrayType(array_type, length)

    if t[key] == "Mapping":

        if is_compact_ast:
            mappingFrom = parse_type(t["keyType"], next_context)
            mappingTo = parse_type(t["valueType"], next_context)
        else:
            assert len(t["children"]) == 2

            mappingFrom = parse_type(t["children"][0], next_context)
            mappingTo = parse_type(t["children"][1], next_context)

        return MappingType(mappingFrom, mappingTo)

    if t[key] == "FunctionTypeName":

        if is_compact_ast:
            params = t["parameterTypes"]
            return_values = t["returnParameterTypes"]
            index = "parameters"
        else:
            assert len(t["children"]) == 2
            params = t["children"][0]
            return_values = t["children"][1]
            index = "children"

        assert params[key] == "ParameterList"
        assert return_values[key] == "ParameterList"

        params_vars: List[FunctionTypeVariable] = []
        return_values_vars: List[FunctionTypeVariable] = []
        for p in params[index]:
            var = FunctionTypeVariable()
            var.set_offset(p["src"], caller_context.smartfast)

            var_parser = FunctionTypeVariableSolc(var, p)
            var_parser.analyze(caller_context)

            params_vars.append(var)
        for p in return_values[index]:
            var = FunctionTypeVariable()
            var.set_offset(p["src"], caller_context.smartfast)

            var_parser = FunctionTypeVariableSolc(var, p)
            var_parser.analyze(caller_context)

            return_values_vars.append(var)

        return FunctionType(params_vars, return_values_vars)

    raise ParsingError("Type name not found " + str(t))
