from cylp.cy import CyClpSimplex
s = CyClpSimplex()
s.readMps('model.mps')

s.initialSolve()

print(f"Optimal value of objective function: {round(s.objectiveValue, 3)}")

if s.getStatusString() == "optimal":
    print("The solution is optimal.")
else:
    print(f"Solution status: {s.getStatusString()}")
