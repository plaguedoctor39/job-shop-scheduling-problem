from jssp import *
from pyomo.common.timing import report_timing, TicTocTimer

timer = TicTocTimer()
timer.tic('start')
report_timing()
print('Building model')
print('--------------')
model11 = build_model(1,1,1,hard_deadline=True)
timer.toc('Built model')
solve_model(model11)
# Для добавления пользовательского решения (доделать)
# saved_solution = {}
# for v in model11.component_objects(Var):
#     saved_solution[v.name] = v

# for v_name, value in saved_solution.items():
#     getattr(model11, v_name).value = value  
# model11.worker_assigned[25,8].set_value(1)
# model11.worker_assigned[25,8].fix()  
# model11.worker_assigned[35,16].set_value(1)
# model11.worker_assigned[35,16].fix() 
# solve_model(model11)
timer.toc('Solved')
plot_schedule(model11, show=True)
# solution_to_file(model11)
# plot_worker_utilization(model11)
# do_n_solutions(5, model11)