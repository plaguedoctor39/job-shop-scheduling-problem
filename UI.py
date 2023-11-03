from jssp import *
from pyomo.common.timing import report_timing, TicTocTimer

timer = TicTocTimer()
timer.tic('start')
report_timing()
print('Building model')
print('--------------')
model11 = build_model(1,1,1,1,hard_deadline=False)
# model11 = load_model_from_file()
timer.toc('Built model')
# model11.worker_assigned[55,10].set_value(0)
# model11.worker_assigned[55,10].fix()  
solve_model(model11)
model11, changes = remove_conflicting_assignments(model11)
if changes:
    solve_model(model11)
# Для добавления пользовательского решения (доделать)
# saved_solution = {}
# for v in model11.component_objects(Var):
#     saved_solution[v.name] = v

# for v_name, value in saved_solution.items():
#     getattr(model11, v_name).value = value  

# model11.worker_assigned[35,16].set_value(1)
# model11.worker_assigned[35,16].fix() 
# solve_model(model11)
timer.toc('Solved')
# Итерация по всем рабочим и временным периодам и вывод их статуса недоступности
# for worker in model11.workers:
#     for time in model11.time_periods:
#         unavailable = model11.WorkerUnavailable[worker, time].value
#         if model11.worker_unavailability[worker]:
#             print(f"Worker {worker} at time {time}: {model11.worker_unavailability[worker]} {unavailable} {'Unavailable' if unavailable else 'Available'} {[model11.WorkDuringTime[j, worker, time].value for j in model11.jobs]}")

#         print(f'{[model11.WorkDuringTime[j, worker, time].value for j in model11.jobs]}')


plot_gantt_schedule(model11, mode='workers')
# save_model_to_file(model11)
# plot_schedule(model11, show=True, mode='workers')
# solution_to_file(model11)
# plot_worker_utilization(model11)
# do_n_solutions(5, model11)