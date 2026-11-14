
import re
from ir import create_ir, add_operation


# =========================================
# SUPPORTED GATES
# =========================================

SUPPORTED_GATES = {
    "id", "h", "x", "y", "z",
    "s", "sdg", "t", "tdg",
    "rx", "ry", "rz",
    "u", "u1", "u2", "u3",
    "cx", "cnot", "cy", "cz",
    "ch", "swap", "ccx", "cswap",
}


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
        # h q[0];
        # cx q[0], q[1];
        # rz(pi/2) q[0];
        # ---------------------------------

        match = re.fullmatch(
            r"(\w+)\s*(?:\((.*?)\))?\s+(.+)",
            statement
        )

        if match:

            gate, params, operands = match.groups()

            gate = gate.lower()

            # Validate gate
            if gate not in SUPPORTED_GATES:
                raise ValueError(f"Unsupported gate: {gate}")

            # Extract parameters
            parameters = []

            if params:
                parameters = [
                    p.strip()
                    for p in params.split(",")
                ]

            # Extract operands
            operand_refs = [
                operand.strip()
                for operand in operands.split(",")
            ]

            qubits = []

            for operand in operand_refs:

                qubits.extend(
                    resolve_register(
                        operand,
                        qregs
                    )
                )

            # Controlled gate: CX / CNOT
            if gate in ("cx", "cnot"):

                if len(qubits) != 2:
                    raise ValueError(
                        "CX requires exactly two qubits"
                    )

                controls = [qubits[0]]
                targets = [qubits[1]]

                gate = "cx"

            else:

                controls = []
                targets = qubits

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
