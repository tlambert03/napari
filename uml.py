import pathlib
import json
from collections import defaultdict
from textwrap import indent

out = json.loads(pathlib.Path("connections.json").read_text())

targets = set()
[targets.update(vv) for v in out.values() for vv in v.values()]

packages = {
    "Layer": ["Shapes", "Labels", "Points", "Surface", "Image", "Vectors"]
}


t = defaultdict(list)
for target in targets:
    kls, meth = target.split(".", maxsplit=1)
    t[kls].append(target)

for sup, values in packages.items():
    for v in values:
        if v in t:
            t[sup].append((v, t.pop(v)))
        else:
            t[sup].append((v, []))
t['Dims'] = []


def make_group(name, children):
    _type = "package" if name in packages else "frame"
    lines = [f'{_type} "{name}" ' + "{"]
    for child in children:
        if isinstance(child, tuple):
            lines.append("\n" + indent(make_group(*child), "  "))
        else:
            lines.append(f"  [{child}]")
    lines.append("}\n")
    return "\n".join(lines)


final = ["@startuml"]
final.extend([make_group(n, t[n]) for n in t])
# def make_connections(out=out):
for kls, dct in out.items():
    for event, connections in dct.items():
        for target in connections:
            final.append(f"{kls} --> [{target}] : {event}")
final += ["@enduml"]
final = "\n".join(final)
