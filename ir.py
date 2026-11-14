
def create_ir(version):
    return {
        "version": version,
        "num_qubits": 0,
        "num_clbits": 0,
        "operations": []
    }


def add_operation(
    ir,
    name,
    targets,
    controls=None,
    parameters=None,
    classical_targets=None
):
    operation = {
        "name": name,
        "targets": targets,
        "controls": controls or [],
        "parameters": parameters or []
    }

    if classical_targets is not None:
        operation["classical_targets"] = classical_targets

    ir["operations"].append(operation)
