from jssp import *
from pyomo.common.timing import report_timing, TicTocTimer

timer = TicTocTimer()
timer.tic('start')
report_timing()
print('Building model')
print('--------------')
model11 = build_model(1000,0.8,hard_deadline=False)
model11.write(filename='model.mps', format=ProblemFormat.mps)
# model11 = load_model_from_file()
timer.toc('Built model')

# здесь загрузка готового решения, задать файл в функции в jssp.py, убрать комментирование
# model11 = solution_from_file(model11)


# model11.worker_assigned[55,10].set_value(0)
# model11.worker_assigned[55,10].fix()  
solve_model(model11)

# model11.worker_assigned[35,16].set_value(1)
# model11.worker_assigned[35,16].fix() 
# solve_model(model11)
timer.toc('Solved')

plot_gantt_schedule(model11)
plot_gantt_schedule_projects(model11)
plot_worker_utilization_interactive(model11)

# save_model_to_file(model11)
# plot_schedule(model11, show=True, mode='workers')
# solution_to_file(model11)
# plot_worker_utilization(model11)
# do_n_solutions(5, model11)