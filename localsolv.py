import localsolver

with localsolver.LocalSolver() as ls:
    model = ls.read_mps('model.mps')
    
    ls.solve()

    for i in range(1, 4):  
        var_name = f"x{i}"
        value = model.get_value(var_name)
        print(f"{var_name} = {value}")

    for var in model.variables:
        print(f"{var.name} = {var.value}")

    obj_value = model.objective_value
    print(f"Objective value: {obj_value}")