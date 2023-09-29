from cylp.cy import CyClpSimplex
s = CyClpSimplex()
s.readMps('model.mps')

s.initialSolve()

print(round(s.objectiveValue, 3))
