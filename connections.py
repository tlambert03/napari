import napari
import inspect
import re
from collections import defaultdict


def walk_modules(module, _walked=None, pkg='napari'):
    if not _walked:
        _walked = set()
    yield module
    _walked.add(module)
    for name in dir(module):
        attr = getattr(module, name)
        if inspect.ismodule(attr) and attr.__package__.startswith(pkg):
            if attr not in _walked:
                yield from walk_modules(attr, _walked)


def iter_classes(module):
    for name in dir(module):
        attr = getattr(module, name)
        if inspect.isclass(attr) and attr.__module__ == module.__name__:
            yield attr


lines = []
for mod in walk_modules(napari):
    for kls in iter_classes(mod):
        try:
            src = inspect.getsource(kls)
        except Exception:
            continue
        for line in src.splitlines():
            if '.connect(' in line and "`" not in line:
                lines.append(line.replace("self", kls.__name__).strip())

connect_pattern = re.compile(
    r"(?P<source>[a-zA-Z0-9_.]+)\.events\.(?P<event>\w+)"
    r"\.connect\((?P<target>.+)\)"
)

connections: dict = defaultdict(lambda: defaultdict(list))
for line in sorted(lines):
    match = connect_pattern.match(line)
    if match:
        src = match.group("source").split(".")[-1]
        event = match.group("event")
        target = match.group("target")
        connections[src][event].append(target)

# pprint.pprint(connections)
for src, events in sorted(connections.items(), key=lambda s: s[0].lower()):
    for event, targets in sorted(events.items()):
        for i, target in enumerate(targets):
            if i:
                print(f'{"":27} --> {target}')
            else:
                print(f'{src:9} : {event:15} --> {target}')
