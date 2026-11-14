
import pytest
from parser import parse_qasm


def test_qasm3_bell():
    source = """
    OPENQASM 3.0;
    qubit[2] q;
    bit[2] c;
    h q[0];
    cx q[0], q[1];
    c = measure q;
    """

    ir = parse_qasm(source)

    assert ir["version"] == "3.0"
    assert ir["num_qubits"] == 2
    assert ir["num_clbits"] == 2

    assert ir["operations"][0] == {
        "name": "h",
        "targets": [0],
        "controls": [],
        "parameters": []
    }

    assert ir["operations"][1] == {
        "name": "cx",
        "targets": [1],
        "controls": [0],
        "parameters": []
    }

    assert ir["operations"][2]["classical_targets"] == [0, 1]


def test_qasm2_bell():
    source = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    h q[0];
    cx q[0], q[1];
    measure q -> c;
    """

    ir = parse_qasm(source)

    assert ir["version"] == "2.0"
    assert ir["num_qubits"] == 2
    assert ir["num_clbits"] == 2

    assert ir["operations"][1]["controls"] == [0]
    assert ir["operations"][1]["targets"] == [1]

    assert ir["operations"][2]["classical_targets"] == [0, 1]


def test_parameterized_gate():
    source = """
    OPENQASM 2.0;
    qreg q[1];
    rx(pi/2) q[0];
    """

    ir = parse_qasm(source)

    assert ir["operations"][0]["name"] == "rx"
    assert ir["operations"][0]["targets"] == [0]
    assert ir["operations"][0]["parameters"] == ["pi/2"]


def test_reset_and_barrier():
    source = """
    OPENQASM 2.0;
    qreg q[2];
    barrier q;
    reset q[0];
    """

    ir = parse_qasm(source)

    assert ir["operations"][0]["name"] == "barrier"
    assert ir["operations"][0]["targets"] == [0, 1]

    assert ir["operations"][1]["name"] == "reset"
    assert ir["operations"][1]["targets"] == [0]


def test_unknown_statement():
    source = """
    OPENQASM 2.0;
    qreg q[1];
    invalid_statement q[0];
    """

    with pytest.raises(ValueError):
        parse_qasm(source)
