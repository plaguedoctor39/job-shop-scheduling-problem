from jssp import *


model11 = build_model(1,1)
solve_model(model11, True)
plot_schedule(model11)
solution_to_file(model11)
plot_worker_utilization(model11)
# do_n_solutions(5, model11)