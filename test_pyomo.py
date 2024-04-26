from pyomo.environ import *
from pyomo.opt import SolverFactory

mps_file_path = 'model30_10_100.mps'

model = ConcreteModel()

solver = SolverFactory('cbc')

results = solver.solve(None, keepfiles=False, tmpdir=None, options={'filename': mps_file_path})

# Проверяем, была ли модель успешно решена
if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
    # Выводим результаты
    # Обратите внимание, что при таком подходе мы не можем напрямую получить значение целевой функции, 
    # поскольку модель загружается и решается внутри решателя
    print('Решение найдено. Статус:', results.solver.status)
elif results.solver.termination_condition == TerminationCondition.infeasible:
    print('Модель не имеет решения.')
else:
    # Нечто иное произошло
    print('Статус решателя:', results.solver.status)
