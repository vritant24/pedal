"""
Type definitions of builtin functions and modules.
"""

from pedal.types.new_types import (make_dataclass, FunctionType, AnyType,
                                   ImpossibleType, NumType, IntType, FloatType, NoneType, BoolType,
                                   TupleType, ListType, StrType, FileType, DictType,
                                   ModuleType, SetType, LiteralInt, LiteralFloat, LiteralStr, LiteralBool,
                                   BUILTIN_MODULES, BUILTIN_NAMES,
                                   int_function, float_function, num_function,
                                   bool_function, void_function, TYPE_TYPE,
                                   IntConstructor, FloatConstructor, BoolConstructor,
                                   ListConstructor, StrConstructor, str_function, GeneratorType, SetConstructor,
                                   FrozenSetConstructor, DictConstructor, TupleConstructor)


BUILTIN_MODULES.update({
    'dataclasses': ModuleType('dataclasses', fields={
        'dataclass': FunctionType('dataclass', definition=make_dataclass)
    }),
    'pprint': ModuleType('pprint',
                         fields={
                             'pprint': FunctionType(name='pprint', returns=NoneType)
                         }),
    'json': ModuleType('json',
                       fields={
                           'loads': FunctionType(name='loads', returns=AnyType),
                           'dumps': FunctionType(name='dumps', returns=StrType)
                       }),
    'random': ModuleType('random',
                         fields={
                             'randint': FunctionType(name='randint', returns=NumType)
                         }),
    'string': ModuleType('string',
                         fields={
                             'letters': StrType(False),
                             'digits': StrType(False),
                             'ascii_letters': StrType(False),
                             'punctuation': StrType(False),
                             'printable': StrType(False),
                             'whitespace': StrType(False),
                             'ascii_uppercase': StrType(False),
                             'ascii_lowercase': StrType(False),
                             'hexdigits': StrType(False),
                             'octdigits': StrType(False),
                         }),
    'math': ModuleType('math',
                       fields={
                           f.name: f for f in [
                               int_function('ceil'),
                               int_function('comb'),
                               float_function('copysign'),
                               num_function('fabs'),
                               int_function('factorial'),
                               int_function('floor'),
                               num_function('fmod'),
                               FunctionType('frexp', returns=lambda: TupleType([FloatType(), IntType()])),
                               float_function('fsum'),
                               int_function('gcd'),
                               bool_function('isclose'),
                               bool_function('isfinite'),
                               bool_function('isinf'),
                               bool_function('isnan'),
                               int_function('isqrt'),
                               int_function('lcm'),
                               num_function('ldexp'),
                               FunctionType('modf', returns=lambda: TupleType([FloatType(), FloatType()])),
                               float_function('nextafter'),
                               int_function('perm'),
                               num_function('prod'),
                               float_function('remainder'),
                               int_function('trunc'),
                               float_function('ulp'),
                               float_function('exp'),
                               float_function('expm1'),
                               float_function('log'),
                               float_function('log1p'),
                               float_function('log2'),
                               float_function('log10'),
                               float_function('pow'),
                               float_function('sqrt'),
                               float_function('acos'),
                               float_function('asin'),
                               float_function('atan'),
                               float_function('atan2'),
                               float_function('cos'),
                               float_function('dist'),
                               float_function('hypot'),
                               float_function('sin'),
                               float_function('tan'),
                               num_function('radians'),
                               num_function('degrees'),
                               float_function('acosh'),
                               float_function('asinh'),
                               float_function('atanh'),
                               float_function('cosh'),
                               float_function('sinh'),
                               float_function('tanh'),
                               float_function('erf'),
                               float_function('erfc'),
                               float_function('gamma'),
                               float_function('lgamma')
                       ]}
   )
})

BUILTIN_MODULES['math'].fields.update({
    'pi': FloatType(),
    'e': FloatType(),
    'tau': FloatType(),
    'inf': FloatType(),
    'nan': FloatType()
})

def round_definition(tifa, function, callee, arguments, named_arguments, location):
    if len(arguments) == 1:
        return IntType()
    elif len(arguments) == 2:
        return FloatType()
    return ImpossibleType()


def map_definition(tifa, function, callee, arguments, named_arguments, location):
    if arguments:
        return GeneratorType(arguments[0].is_empty, arguments[0].iterate())
    return ImpossibleType()


def zip_definition(tifa, function, callee, arguments, named_arguments, location):
    tupled_types = TupleType((t.iterate() for t in arguments))
    return GeneratorType(arguments and arguments[0].is_empty,
                         tupled_types)


# TODO: Type guard with `isinstance`


BUILTIN_NAMES.update({
    f.name: f for f in [
        TYPE_TYPE,
        IntConstructor(), FloatConstructor(), BoolConstructor(), StrConstructor(),
        ListConstructor(), SetConstructor(), FrozenSetConstructor(),
        DictConstructor(), TupleConstructor(),
        void_function('print'), int_function("abs"), int_function('len'),
        int_function('ord'), num_function('pow'), num_function('sum'),
        bool_function('all'), bool_function('any'), bool_function('isinstance'),
        str_function('chr'), str_function('bin'), str_function('repr'), str_function('input'),
        FunctionType('open', returns=FileType),
        FunctionType('map', definition=map_definition),
        FunctionType('round', definition=round_definition),
        FunctionType('sorted', definition='identity'),
        FunctionType('reversed', definition='identity'),
        FunctionType('filter', definition='identity'),
        FunctionType('range', returns=lambda: ListType(False, IntType())),
        FunctionType('dir', returns=lambda: ListType(False, StrType())),
        FunctionType('max', returns='element'),
        FunctionType('min', returns='element'),
        FunctionType('zip', definition=zip_definition),
        FunctionType('__import__', returns=ModuleType),
        FunctionType('globals', returns=lambda: DictType([(StrType(), AnyType())])),
        FunctionType('classmethod', returns='identity'),
        FunctionType('staticmethod', returns='identity'),
    ]
})

BUILTIN_NAMES['__name__'] = StrType()


def get_builtin_module(name):
    """
    Given the name of the module, retrieve its TIFA representation.
    """
    return BUILTIN_MODULES.get(name)


def get_builtin_name(name):
    """
    Given a name, retrieve a copy of its built-in implementation.
    """
    if name in BUILTIN_NAMES:
        return BUILTIN_NAMES[name].clone_mutably()
