import functools
import inspect
import sys

from napari.utils.naming import (
    numbered_patt,
    inc_name_count,
    sep,
    start,
    magic_name,
)


def test_re_base_brackets():
    assert numbered_patt.search('layer [12]').group(0) == '12'
    assert numbered_patt.search('layer [e]').group(0) == ''
    assert numbered_patt.search('layer 12]').group(0) == ''
    assert numbered_patt.search('layer [12').group(0) == ''
    assert numbered_patt.search('layer[12]').group(0) == ''
    assert numbered_patt.search('layer 12').group(0) == ''
    assert numbered_patt.search('layer12').group(0) == ''
    assert numbered_patt.search('layer').group(0) == ''


def test_re_other_brackets():
    assert numbered_patt.search('layer [3] [123]').group(0) == '123'


def test_re_first_bracket():
    assert numbered_patt.search(' [42]').group(0) == '42'
    assert numbered_patt.search('[42]').group(0) == '42'


def test_re_sub_base_num():
    assert numbered_patt.sub('8', 'layer [7]', count=1) == 'layer [8]'


def test_re_sub_base_empty():
    assert numbered_patt.sub(' [3]', 'layer', count=1) == 'layer [3]'


def test_inc_name_count():
    assert inc_name_count('layer [7]') == 'layer [8]'
    assert inc_name_count('layer') == f'layer{sep}[{start}]'
    assert inc_name_count('[41]') == '[42]'


def eval_with_filename(source, filename=__file__):
    frame = inspect.currentframe().f_back
    code = compile(source, filename, 'eval')
    return eval(code, frame.f_globals, frame.f_locals)


walrus = sys.version_info >= (3, 8)
magic_name = functools.partial(
    magic_name, path_prefix=magic_name.__code__.co_filename
)


def test_basic():
    """Check that name is guessed correctly."""
    assert magic_name(42) is None

    z = 5
    assert magic_name(z) == 'z'

    if walrus:
        assert eval_with_filename("magic_name(y:='SPAM')") == 'y'


globalval = 42


def test_global():
    """Check that it works with global variables."""
    assert magic_name(globalval) == 'globalval'


def test_function_chains():
    """Check that nothing weird happens with function chains."""

    def foo():
        return 42

    assert magic_name(foo()) is None


def test_assignment():
    """Check that assignment expressions do not confuse it."""
    result = magic_name(17)
    assert result is None

    t = 3
    result = magic_name(t)
    assert result == 't'

    if walrus:
        result = eval_with_filename('magic_name(d:=42)')
        assert result == 'd'


def test_path_prefix():
    """Test that path prefixes work as expected."""
    mname = functools.partial(magic_name, path_prefix=__file__)

    def foo(x):
        def bar(y):
            return mname(y)

        return bar(x)

    assert eval_with_filename('foo(42)', 'hi.py') is None

    r = 8  # noqa
    assert eval_with_filename('foo(r)', 'bye.py') == 'r'

    if walrus:
        assert eval_with_filename('foo(i:=33)', 'rye.py') == 'i'
