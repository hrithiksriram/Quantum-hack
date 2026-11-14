
import json
from parser import parse_qasm

with open("samples/bell2.qasm", "r") as file:
    source = file.read()

ir = parse_qasm(source)

print(json.dumps(ir, indent=4))
