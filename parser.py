
import re
from ir import create_ir, add_operation


# =========================================
# SUPPORTED GATES
# =========================================

GATE_INFO = {
    # Single-qubit gates: (qubits, parameters)
    "id": (1, 0),
    "h": (1, 0),
    "x": (1, 0),
    "y": (1, 0),
    "z": (1, 0),
    "s": (1, 0),
    "sdg": (1, 0),
    "t": (1, 0),
    "tdg": (1, 0),

    "rx": (1, 1),
    "ry": (1, 1),
    "rz": (1, 1),
    "u1": (1, 1),
    "u2": (1, 2),
    "u3": (1, 3),
    "u": (1, 3),

    # Two-qubit gates
    "cx": (2, 0),
    "cnot": (2, 0),
    "cy": (2, 0),
    "cz": (2, 0),
    "ch": (2, 0),
    "swap": (2, 0),

    # Three-qubit gates
    "ccx": (3, 0),
    "cswap": (3, 0),
}

SUPPORTED_GATES = set(GATE_INFO.keys())


# =========================================
# MAIN PARSER
# =========================================

def parse_qasm(source):

    # -------------------------------------
    # REMOVE COMMENTS
    # -------------------------------------

    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)

    # -------------------------------------
    # FIND QASM VERSION
    # -------------------------------------

    version_match = re.search(
        r"OPENQASM\s+(\d+\.\d+)\s*;",
        source,
        re.IGNORECASE
    )

    if not version_match:
        raise ValueError("Missing OPENQASM version declaration")

    version = version_match.group(1)

    if version not in ("2.0", "3.0"):
        raise ValueError(f"Unsupported QASM version: {version}")

    # -------------------------------------
    # CREATE IR
    # -------------------------------------

    ir = create_ir(version)

    qregs = {}
    cregs = {}

    q_offset = 0
    c_offset = 0

    statements = source.split(";")

    # =====================================
    # PASS 1: REGISTER DECLARATIONS
    # =====================================

    for statement in statements:

        statement = statement.strip()

        # QASM 2.0: qreg q[2]
        match = re.fullmatch(
            r"qreg\s+(\w+)\s*\[\s*(\d+)\s*\]",
            statement
        )

        if match:

            name, size = match.groups()
            size = int(size)

            if size <= 0:
                raise ValueError("Register size must be positive")

            if name in qregs:
                raise ValueError(f"Duplicate quantum register: {name}")

            qregs[name] = list(range(q_offset, q_offset + size))
            q_offset += size
            continue

        # QASM 2.0: creg c[2]
        match = re.fullmatch(
            r"creg\s+(\w+)\s*\[\s*(\d+)\s*\]",
            statement
        )

        if match:

            name, size = match.groups()
            size = int(size)

            if size <= 0:
                raise ValueError("Register size must be positive")

            if name in cregs:
                raise ValueError(f"Duplicate classical register: {name}")

            cregs[name] = list(range(c_offset, c_offset + size))
            c_offset += size
            continue

        # QASM 3.0: qubit[2] q
        match = re.fullmatch(
            r"qubit\s*\[\s*(\d+)\s*\]\s*(\w+)",
            statement
        )

        if match:

            size, name = match.groups()
            size = int(size)

            if size <= 0:
                raise ValueError("Register size must be positive")

            if name in qregs:
                raise ValueError(f"Duplicate quantum register: {name}")

            qregs[name] = list(range(q_offset, q_offset + size))
            q_offset += size
            continue

        # QASM 3.0: bit[2] c
        match = re.fullmatch(
            r"bit\s*\[\s*(\d+)\s*\]\s*(\w+)",
            statement
        )

        if match:

            size, name = match.groups()
            size = int(size)

            if size <= 0:
                raise ValueError("Register size must be positive")

            if name in cregs:
                raise ValueError(f"Duplicate classical register: {name}")

            cregs[name] = list(range(c_offset, c_offset + size))
            c_offset += size
            continue

        # QASM 3.0: qubit q
        match = re.fullmatch(
            r"qubit\s+(\w+)",
            statement
        )

        if match:

            name = match.group(1)

            if name in qregs:
                raise ValueError(f"Duplicate quantum register: {name}")

            qregs[name] = [q_offset]
            q_offset += 1
            continue

        # QASM 3.0: bit c
        match = re.fullmatch(
            r"bit\s+(\w+)",
            statement
        )

        if match:

            name = match.group(1)

            if name in cregs:
                raise ValueError(f"Duplicate classical register: {name}")

            cregs[name] = [c_offset]
            c_offset += 1

    # -------------------------------------
    # STORE REGISTER COUNTS
    # -------------------------------------

    ir["num_qubits"] = q_offset
    ir["num_clbits"] = c_offset

    # =====================================
    # REGISTER REFERENCE HELPER
    # =====================================

    def resolve_register(reference, registers):

        match = re.fullmatch(
            r"(\w+)(?:\[\s*(\d+)\s*\])?",
            reference.strip()
        )

        if not match:
            raise ValueError(
                f"Invalid register reference: {reference}"
            )

        name, index = match.groups()

        if name not in registers:
            raise ValueError(f"Unknown register: {name}")

        # Whole register
        if index is None:
            return registers[name][:]

        index = int(index)

        if index >= len(registers[name]):
            raise ValueError(f"Index out of range: {reference}")

        return [registers[name][index]]

    # =====================================
    # PASS 2: OPERATIONS
    # =====================================

    for statement in statements:

        statement = statement.strip()

        if not statement:
            continue

        # Skip version, include, and declarations
        if (
            statement.upper().startswith("OPENQASM")
            or statement.startswith("include")
            or statement.startswith("qreg")
            or statement.startswith("creg")
            or statement.startswith("qubit")
            or statement.startswith("bit")
        ):
            continue

        # ---------------------------------
        # QASM 2.0 MEASUREMENT
        # measure q[0] -> c[0]
        # ---------------------------------

        match = re.fullmatch(
            r"measure\s+(.+?)\s*->\s*(.+)",
            statement
        )

        if match:

            qref, cref = match.groups()

            qindices = resolve_register(qref, qregs)
            cindices = resolve_register(cref, cregs)

            if len(qindices) != len(cindices):
                raise ValueError(
                    "Measurement register sizes do not match"
                )

            add_operation(
                ir,
                "measure",
                qindices,
                classical_targets=cindices
            )

            continue

        # ---------------------------------
        # QASM 3.0 MEASUREMENT
        # c[0] = measure q[0]
        # ---------------------------------

        match = re.fullmatch(
            r"(.+?)\s*=\s*measure\s+(.+)",
            statement
        )

        if match:

            cref, qref = match.groups()

            qindices = resolve_register(qref, qregs)
            cindices = resolve_register(cref, cregs)

            if len(qindices) != len(cindices):
                raise ValueError(
                    "Measurement register sizes do not match"
                )

            add_operation(
                ir,
                "measure",
                qindices,
                classical_targets=cindices
            )

            continue

        # ---------------------------------
        # QASM 3.0 MEASUREMENT
        # measure q[0];
        # ---------------------------------

        match = re.fullmatch(
            r"measure\s+(.+)",
            statement
        )

        if match:

            qindices = resolve_register(
                match.group(1),
                qregs
            )

            add_operation(
                ir,
                "measure",
                qindices
            )

            continue

        # ---------------------------------
        # RESET
        # reset q[0];
        # ---------------------------------

        match = re.fullmatch(
            r"reset\s+(.+)",
            statement
        )

        if match:

            qindices = resolve_register(
                match.group(1),
                qregs
            )

            add_operation(
                ir,
                "reset",
                qindices
            )

            continue

        # ---------------------------------
        # BARRIER
        # barrier q;
        # ---------------------------------

        match = re.fullmatch(
            r"barrier\s+(.+)",
            statement
        )

        if match:

            qindices = resolve_register(
                match.group(1),
                qregs
            )

            add_operation(
                ir,
                "barrier",
                qindices
            )

            continue

        # ---------------------------------
        # GATES
        # ---------------------------------

        match = re.fullmatch(
            r"(\w+)\s*(?:\((.*?)\))?\s+(.+)",
            statement
        )

        if match:

            gate, params, operands = match.groups()

            gate = gate.lower()

            # Validate supported gate
            if gate not in SUPPORTED_GATES:
                raise ValueError(f"Unsupported gate: {gate}")

            expected_qubits, expected_params = GATE_INFO[gate]

            # ---------------------------------
            # EXTRACT PARAMETERS
            # ---------------------------------

            parameters = []

            if params is not None:

                parameters = [
                    p.strip()
                    for p in params.split(",")
                ]

                if any(p == "" for p in parameters):
                    raise ValueError(
                        f"Invalid empty parameter in gate: {gate}"
                    )

            # Validate parameter count
            if len(parameters) != expected_params:
                raise ValueError(
                    f"Gate {gate} expects {expected_params} parameters, "
                    f"but got {len(parameters)}"
                )

            # ---------------------------------
            # EXTRACT OPERANDS
            # ---------------------------------

            operand_refs = [
                operand.strip()
                for operand in operands.split(",")
            ]

            if any(not operand for operand in operand_refs):
                raise ValueError("Empty gate operand")

            qubits = []

            for operand in operand_refs:

                qubits.extend(
                    resolve_register(
                        operand,
                        qregs
                    )
                )

            # Validate qubit count
            if len(qubits) != expected_qubits:
                raise ValueError(
                    f"Gate {gate} expects {expected_qubits} qubits, "
                    f"but got {len(qubits)}"
                )

            # ---------------------------------
            # CONTROLLED GATE: CX / CNOT
            # ---------------------------------

            if gate in ("cx", "cnot"):

                controls = [qubits[0]]
                targets = [qubits[1]]

                gate = "cx"

            else:

                controls = []
                targets = qubits

            # ---------------------------------
            # ADD OPERATION TO IR
            # ---------------------------------

            add_operation(
                ir,
                gate,
                targets,
                controls=controls,
                parameters=parameters
            )

            continue

        # ---------------------------------
        # UNKNOWN STATEMENT
        # ---------------------------------

        raise ValueError(
            f"Unsupported QASM statement: {statement}"
        )

    return ir
