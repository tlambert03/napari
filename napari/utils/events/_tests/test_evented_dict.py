from unittest.mock import Mock, call

import pytest

from napari.utils.events import EventedDict


@pytest.mark.parametrize(
    'meth',
    [
        # METHOD, ARGS, EXPECTED EVENTS
        # primary interface
        ('__getitem__', ('a',), []),
        ('__setitem__', ('a', 1), [call.set(value=('a', 1, 'hi'))]),
        (
            '__setitem__',
            ('k', 'v'),
            [call.set(value=('k', 'v', EventedDict.NOKEY))],
        ),
        ('__delitem__', ('a',), [call.deleted(value=('a', 'hi'))],),
        # inherited interface
        ('clear', (), [call.deleted(value=('a', 'hi'))],),
        ('copy', (), []),
        ('fromkeys', (('a', 'b', 'c'), 1), []),
        ('get', ('a',), []),
        ('get', ('nonexistent', 'default'), []),
        ('get', ('a'), []),
        ('items', (), []),
        ('keys', (), []),
        ('pop', ('a',), [call.deleted(value=('a', 'hi'))],),
        ('pop', ('nonexistent', 'default'), []),
        ('popitem', (), [call.deleted(value=('a', 'hi'))],),
        ('setdefault', ('a', 5), []),
        (
            'setdefault',
            ('k', 'v'),
            [call.set(value=('k', 'v', EventedDict.NOKEY))],
        ),
        ('update', ({'a': 4},), [call.set(value=('a', 4, 'hi'))]),
    ],
    ids=lambda x: x[0],
)
def test_dict_interface_parity(meth):
    """Test that evented dicts behave like regular dicts, and emit events."""
    method_name, args, expected = meth
    regular_dict = dict(a='hi')
    test_dict = EventedDict(regular_dict)
    test_dict.events = Mock(wraps=test_dict.events)
    test_dict_method = getattr(test_dict, method_name)
    regular_dict_method = getattr(regular_dict, method_name)

    assert test_dict == regular_dict
    assert test_dict_method(*args) == regular_dict_method(*args)
    assert test_dict == regular_dict
    assert test_dict.events.method_calls == expected
