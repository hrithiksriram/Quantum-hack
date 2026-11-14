
import pytest
from parser import parse_qasm


def test_basic_qasm2():
    source = """
    OPENQASM 2.0;
    qreg q[2];
    creg c[2];
    h q[0];
    cx q[0],q[1];
    measure q -> c;
    """
    ir = parse_qasm(source)
    assert ir["num_qubits"] == 2
    assert ir["num_clbits"] == 2
    assert len(ir["operations"]) == 3


def test_basic_qasm3():
    source = """
    OPENQASM 3.0;
    qubit[2] q;
    bit[2] c;
    h q[0];
    cx q[0],q[1];
    c[0] = measure q[0];
    """
    ir = parse_qasm(source)
    assert ir["num_qubits"] == 2
    assert ir["num_clbits"] == 2
    assert len(ir["operations"]) == 3


def test_parameterized_gates():
    source = """
    OPENQASM 3.0;
    qubit q;
    rx(0.5) q;
    ry(1.2) q;
    rz(0.3) q;
    u2(0.1,0.2) q;
    u3(0.1,0.2,0.3) q;
    """
    ir = parse_qasm(source)
    assert len(ir["operations"]) == 5


def test_wrong_parameter_count():
    source = """
    OPENQASM 3.0;
    qubit q;
    u2(0.1) q;
    """
    with pytest.raises(ValueError):
        parse_qasm(source)


def test_invalid_qubit_index():
    source = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[5];
    """
    with pytest.raises(ValueError):
        parse_qasm(source)


def test_unknown_gate():
    source = """
    OPENQASM 3.0;
    qubit q;
    customgate q;
    """
    with pytest.raises(ValueError):
        parse_qasm(source)


def test_duplicate_register():
    source = """
    OPENQASM 3.0;
    qubit[2] q;
    qubit[3] q;
    """
    with pytest.raises(ValueError):
        parse_qasm(source)


def test_reset():
    source = """
    OPENQASM 3.0;
    qubit q;
    reset q;
    """
    ir = parse_qasm(source)
    assert ir["operations"][0]["name"] == "reset"
