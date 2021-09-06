import pytest

from napari.utils.context import (
    Constant,
    Expr,
    Name,
    UnaryOp,
    parse_expression,
)
from napari.utils.context._expressions import _iter_names, type2char


def test_names():
    assert Name("n").eval({'n': 5}) == 5

    # currently, evaludating with a missing name is an error.
    with pytest.raises(KeyError):
        assert Name("n").eval({}) is None

    assert repr(Name('n')) == "Name('n')"


def test_constants():
    assert Constant(1).eval() == 1
    assert Constant(3.14).eval() == 3.14
    assert Constant('asdf').eval() == 'asdf'
    assert Constant(b'byte').eval() == b'byte'
    assert str(Constant(b'byte')) == "b'byte'"
    assert Constant(True).eval() is True
    assert Constant(False).eval() is False
    assert Constant(None).eval() is None

    assert repr(Constant(1)) == 'Constant(1)'

    # only {None, str, bytes, bool, int, float} allowed
    with pytest.raises(TypeError):
        Constant((1, 2))  # type: ignore


def test_bool_ops():
    n1 = Name("n1")
    true = Constant(True)
    false = Constant(False)
    assert (n1 & true).eval({'n1': True}) is True
    assert (n1 & false).eval({'n1': True}) is False
    assert (n1 & false).eval({'n1': False}) is False
    assert (n1 | true).eval({'n1': True}) is True
    assert (n1 | false).eval({'n1': True}) is True
    assert (n1 | false).eval({'n1': False}) is False

    # real constants
    assert (n1 & True).eval({'n1': True}) is True
    assert (n1 & False).eval({'n1': True}) is False
    assert (n1 & False).eval({'n1': False}) is False
    assert (n1 | True).eval({'n1': True}) is True
    assert (n1 | False).eval({'n1': True}) is True
    assert (n1 | False).eval({'n1': False}) is False

    # when working with Expr objects:
    # the binary "op" & refers to the boolean op "and"
    assert str(Constant(1) & 1) == '1 and 1'
    # note: using "and" does NOT work to combine expressions
    # (in this case, it would just return the second value "1")
    assert not isinstance(Constant(1) and 1, Expr)


def test_unary_ops():
    assert Constant(1).eval() == 1
    assert (-Constant(1)).eval() == -1
    assert Constant(True).eval() is True
    assert (~Constant(True)).eval() is False


def test_comparison():
    n = Name("n")
    n2 = Name("n2")
    one = Constant(1)

    assert (n == n2).eval({'n': 2, 'n2': 2})
    assert not (n == n2).eval({'n': 2, 'n2': 1})
    assert (n != n2).eval({'n': 2, 'n2': 1})
    assert not (n != n2).eval({'n': 2, 'n2': 2})
    # real constant
    assert (n != 1).eval({'n': 2})
    assert not (n != 2).eval({'n': 2})

    assert (n < one).eval({'n': -1})
    assert not (n < one).eval({'n': 2})
    assert (n <= one).eval({'n': 0})
    assert (n <= one).eval({'n': 1})
    assert not (n <= one).eval({'n': 2})
    # with real constant
    assert (n < 1).eval({'n': -1})
    assert not (n < 1).eval({'n': 2})
    assert (n <= 1).eval({'n': 0})
    assert (n <= 1).eval({'n': 1})
    assert not (n <= 1).eval({'n': 2})

    assert (n > one).eval({'n': 2})
    assert not (n > one).eval({'n': 1})
    assert (n >= one).eval({'n': 2})
    assert (n >= one).eval({'n': 1})
    assert not (n >= one).eval({'n': 0})
    # real constant
    assert (n > 1).eval({'n': 2})
    assert not (n > 1).eval({'n': 1})
    assert (n >= 1).eval({'n': 2})
    assert (n >= 1).eval({'n': 1})
    assert not (n >= 1).eval({'n': 0})

    assert Expr.in_(Constant('a'), Constant('abcd')).eval() is True
    assert Constant('a').in_(Constant('abcd')).eval() is True

    assert Expr.not_in(Constant('a'), Constant('abcd')).eval() is False
    assert Constant('a').not_in(Constant('abcd')).eval() is False


def test_iter_names():
    expr = parse_expression('a if b in c else d > e')
    assert sorted(_iter_names(expr)) == ['a', 'b', 'c', 'd', 'e']


GOOD_EXPRESSIONS = [
    'a and b',
    'a == 1',
    'a if b == 7 else False',
    # valid constants:
    '1',
    '3.14',
    'True',
    'False',
    'None',
    'hieee',
    "b'bytes'",
]

for k, v in type2char.items():
    if isinstance(k, UnaryOp.UnaryOpType):
        GOOD_EXPRESSIONS.append(f"{v} 1" if v == 'not' else f"{v}1")
    else:
        GOOD_EXPRESSIONS.append(f"1 {v} 2")

# these are not supported
BAD_EXPRESSIONS = [
    'a orr b',  # typo
    'a b',  # invalid syntax
    'a = b',  # Assign
    'my.attribute',  # Attribute
    '__import__(something)',  # Call
    'print("hi")',
    '(1,)',  # tuples not yet supported
    '{"key": "val"}',  # dicts not yet supported
    '{"hi"}',  # set constant
    '[]',  # lists constant
    'mylist[0]',  # Index
    'mylist[0:1]',  # Slice
    'f"a"',  # JoinedStr
    'a := 1',  # NamedExpr
    r'f"{a}"',  # FormattedValue
    '[v for v in val]',  # ListComp
    '{v for v in val}',  # SetComp
    r'{k:v for k, v in val}',  # DictComp
    '(v for v in val)',  # GeneratorExp
]


@pytest.mark.parametrize('expr', GOOD_EXPRESSIONS)
def test_serdes(expr):
    assert str(parse_expression(expr)) == expr


@pytest.mark.parametrize('expr', BAD_EXPRESSIONS)
def test_bad_serdes(expr):
    with pytest.raises(SyntaxError):
        parse_expression(expr)
