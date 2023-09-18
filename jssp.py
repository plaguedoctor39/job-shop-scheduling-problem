from pyomo.environ import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


workers_data = {
        1: "Токарно-винторезная",
        2: "Слесарная",
        3: "Вертикально-сверлильная",
        4: "Токарная с ЧПУ",
        5: "Токарно-винторезная",
        6: "Слесарная",
        7: "Вертикально-сверлильная",
        8: "Токарная с ЧПУ",
    }

jobs_data = {
        15: ("Токарно-винторезная", 3, []),
        25: ("Токарная с ЧПУ", 5, [15]),
        35: ("Токарная с ЧПУ", 1, [25]),
        45: ("Вертикально-сверлильная", 7, [35]),
        55: ("Слесарная", 4, [45]),
        100: ("Токарно-винторезная", 2, []),
        110: ("Слесарная", 7, [100]),
        120: ("Токарно-винторезная", 5, []),
        130: ("Слесарная", 3, [120]),
        140: ("Токарная с ЧПУ", 2, [130]),
        150: ("Вертикально-сверлильная", 4, [140]),
    }

project_data = {
        1: [15, 25, 35, 45, 55],
        2: [100, 110],
        3: [120, 130, 140, 150]
    }

shifts_data = {
        1: (0, 8),
        2: (8, 16),
        3: (16, 24)
    }

task_to_project = {j: p for p, job_list in project_data.items() for j in job_list}
def build_and_solve(worker_weight):
    model = ConcreteModel()

    

    def are_unrelated(i, j):
        """Возвращает True, если задачи i и j относятся к разным проектам."""
        return model.task_to_project[i] != model.task_to_project[j]


    # Sets
    model.workers = Set(initialize=workers_data.keys())
    model.jobs = Set(initialize=jobs_data.keys())
    model.shifts = Set(initialize=shifts_data.keys())

    # Parameters
    model.specialization = Param(model.workers, initialize=workers_data)
    model.job_duration = Param(model.jobs, initialize={k: v[1] for k, v in jobs_data.items()})
    # model.job_required_specialization = Param(model.jobs, initialize={k: v[0] for k, v in jobs_data.items()})
    model.job_required_specialization = Param(model.jobs, within=Any, initialize={k: v[0] for k, v in jobs_data.items()})
    model.predecessors = Param(model.jobs, within=Any, initialize={k: v[2] for k, v in jobs_data.items()})
    
    model.task_to_project = Param(model.jobs, initialize=task_to_project)

    model.shift_start = Param(model.shifts, initialize={k: v[0] for k, v in shifts_data.items()})
    model.shift_end = Param(model.shifts, initialize={k: v[1] for k, v in shifts_data.items()})


    # Variables
    model.start_time = Var(model.jobs, domain=NonNegativeReals)
    model.end_time = Var(model.jobs, domain=NonNegativeReals)
    model.worker_assigned = Var(model.jobs, model.workers, domain=Binary)
    model.makespan = Var(domain=NonNegativeReals)
    model.idle_time = Var(model.workers, domain=NonNegativeReals) # время простоя рабочего
    model.idle_time_between_tasks = Var(model.jobs, model.jobs, model.workers, domain=NonNegativeReals) # время простоя между задачами для рабочего
    model.y = Var(model.jobs, model.jobs, model.workers, within=Binary) # вспомогательная бинарная переменная для реализации ограничения неперекрытия

    model.worker_used = Var(model.workers, domain=Binary)
    model.worker_shift = Var(model.workers, model.shifts, domain=Binary)

    # model.overlap = Var(model.jobs, model.jobs, model.workers, domain=Binary)


    bigM = sum(model.job_duration.values())
    # bigM = 1000

    # Objective (You may need to specify the objective depending on your specific requirements)
    # model.obj = Objective(expr=model.makespan, sense=minimize)
    idle_time_weight = 1  # Вы можете регулировать этот вес, чтобы достигнуть баланса между минимизацией простоя и максимальным временем завершения
    # model.obj = Objective(expr=model.makespan + sum(model.idle_time_between_tasks[i, j, k] for i in model.jobs for j in model.jobs for k in model.workers), sense=minimize)
    # model.obj = Objective(expr=sum(model.start_time[j] + model.end_time[j] for j in model.jobs), sense=minimize)
    # model.obj = Objective(expr=sum(model.start_time[j] for j in model.jobs), sense=minimize)
    # worker_weight = 1000  # Чем выше этот вес, тем более предпочтительным становится минимизировать число рабочих
    model.obj = Objective(expr=sum(model.start_time[j] for j in model.jobs) + worker_weight * sum(model.worker_used[k] for k in model.workers), sense=minimize)


    # Constraints


    # Задача не может начаться до завершения всех ее предшественников
    def general_precedence_rule(model, i):
        return model.start_time[i] >= sum(model.end_time[j] for j in model.predecessors[i])
    model.general_precedence_constraint = Constraint(model.jobs, rule=general_precedence_rule)

    # вычисляет время простоя между двумя задачами для рабочего
    # def idle_time_between_tasks_rule(model, i, j, k):
    #     if i != j:
    #         return model.idle_time_between_tasks[i, j, k] >= model.start_time[j] - model.end_time[i] - bigM * (1 - model.worker_assigned[i, k]) - bigM * (1 - model.worker_assigned[j, k])
    #     return Constraint.Skip

    # model.idle_time_between_tasks_constraint = Constraint(model.jobs, model.jobs, model.workers, rule=idle_time_between_tasks_rule)

    # если рабочий используется хотя бы для одной работы, то его переменная worker_used равна 1
    def worker_usage_rule(model, i, k):
        return model.worker_assigned[i, k] <= model.worker_used[k]

    model.worker_usage_constraint = Constraint(model.jobs, model.workers, rule=worker_usage_rule)


    # задачи, назначенные одному рабочему, не перекрываются по времени
    def non_overlap_rule_1(model, i, j, k):
        if i != j and are_unrelated(i, j):
            return model.start_time[j] >= model.end_time[i] - bigM * (1 - model.worker_assigned[i, k]) - bigM * (1 - model.y[i, j, k])
        return Constraint.Skip

    def non_overlap_rule_2(model, i, j, k):
        if i != j and are_unrelated(i, j):
            return model.start_time[i] >= model.end_time[j] - bigM * (1 - model.worker_assigned[j, k]) - bigM * model.y[i, j, k]
        return Constraint.Skip

    model.non_overlap_constraint_1 = Constraint(model.jobs, model.jobs, model.workers, rule=non_overlap_rule_1)
    model.non_overlap_constraint_2 = Constraint(model.jobs, model.jobs, model.workers, rule=non_overlap_rule_2)


    # конечное время задачи равно начальному времени плюс продолжительность
    def end_time_rule(model, i):
        return model.end_time[i] == model.start_time[i] + model.job_duration[i]
    model.end_time_constraint = Constraint(model.jobs, rule=end_time_rule)


    # вычисляет общее время простоя рабочего
    def idle_time_rule(model, k):
        total_assigned_time = sum(model.job_duration[i] * model.worker_assigned[i, k] for i in model.jobs)
        return model.idle_time[k] == model.makespan - total_assigned_time
    model.idle_time_constraint = Constraint(model.workers, rule=idle_time_rule)

    # # минимизирует время простоя между задачами для рабочего
    # def minimized_idle_rule(model, i, j, k):
    #     if i != j:
    #         # If job i is assigned to worker k and starts after job j
    #         idle_time = model.start_time[i] - (model.start_time[j] + model.job_duration[j])
    #         return idle_time <= bigM * (1 - model.worker_assigned[i, k]) + bigM * (1 - model.worker_assigned[j, k])
    #     return Constraint.Skip

    # model.minimized_idle_constraint = Constraint(model.jobs, model.jobs, model.workers, rule=minimized_idle_rule)

    # устанавливает, что все задачи должны завершиться до общего времени завершения
    def makespan_rule(model, i):
        return model.end_time[i] <= model.makespan
    model.makespan_constraint = Constraint(model.jobs, rule=makespan_rule)

    # задача может быть назначена рабочему только если его специализация соответствует требованиям задачи
    def specialization_rule(model, i, k):
        if model.specialization[k] == model.job_required_specialization[i]:
            return model.worker_assigned[i, k] <= 1
        else:
            return model.worker_assigned[i, k] == 0
    model.specialization_constraint = Constraint(model.jobs, model.workers, rule=specialization_rule)

    # убеждается, что каждая задача назначена только одному рабочему
    def job_assignment_rule(model, i):
        return sum(model.worker_assigned[i, k] for k in model.workers) == 1
    model.job_assignment_constraint = Constraint(model.jobs, rule=job_assignment_rule)

    M = 24  # Например, если у вас время в часах и оно может быть от 0 до 24

    # def work_time_start_rule(model, i, k, s):
    #     return model.start_time[i] - model.shift_start[s] >= -M * (1 - model.worker_assigned[i, k])

    # def work_time_end_rule(model, i, k, s):
    #     return model.end_time[i] - model.shift_start[s] >= -M * (1 - model.worker_assigned[i, k])


    # model.work_time_start_constraint = Constraint(model.jobs, model.workers, model.shifts, rule=work_time_start_rule)
    # model.work_time_end_constraint = Constraint(model.jobs, model.workers, model.shifts, rule=work_time_end_rule)


    # Если рабочий назначен на задачу во время смены, то он также должен быть назначен на эту смену
    def worker_shift_assignment_rule(model, k, s):
        problematic_indices = [i for i in model.jobs if model.start_time[i].value is None or model.end_time[i].value is None]
        if problematic_indices:
            print(f"Problematic indices for start_time or end_time: {problematic_indices}")
        
        return sum(
            model.worker_assigned[i, k] for i in model.jobs 
            if model.start_time[i].value is not None and model.end_time[i].value is not None and 
            model.start_time[i].value >= model.shift_start[s] and 
            model.end_time[i].value <= model.shift_end[s]
        ) <= bigM * model.worker_shift[k, s]

    model.worker_shift_assignment_constraint = Constraint(model.workers, model.shifts, rule=worker_shift_assignment_rule)




    # Solve the model
    solver = SolverFactory('cbc')
    solver.solve(model)
    result = solver.solve(model)
    print(solver.solve(model, tee=True))
    print("Solver Status:", result.solver.status)
    print("Solver Termination Condition:", result.solver.termination_condition)



    # Print the solution
    print("\nWorker Assignments with Order:")
    for k in model.workers:
        assigned_jobs = [(j, model.start_time[j].value) for j in model.jobs if model.worker_assigned[j, k].value > 0.5]
        sorted_jobs = sorted(assigned_jobs, key=lambda x: x[1])  
        if sorted_jobs:
            job_sequence = " -> ".join(str(job[0]) for job in sorted_jobs)
            print(f"Worker {k} has tasks: {job_sequence}")
        else:
            print(f"Worker {k} has no tasks assigned.")


    print("Work assignments:")
    for i in model.jobs:
        for k in model.workers:
            if model.worker_assigned[i, k].value > 0.5:  # Проверяем назначен ли рабочий на задачу
                print(f"Job {i} is assigned to worker {k} at start time {model.start_time[i].value} and end time {model.end_time[i].value}")

    print("\nShift assignments:")
    for k in model.workers:
        for s in model.shifts:
            if model.worker_shift[k, s].value > 0.5:  # Проверяем назначен ли рабочий на смену
                print(f"Worker {k} is assigned to shift {s} starting at {model.shift_start[s]} and ending at {model.shift_end[s]}")

    print("\nJobs during shifts:")
    for i in model.jobs:
        for s in model.shifts:
            if model.start_time[i].value >= model.shift_start[s] and model.end_time[i].value <= model.shift_end[s]:
                print(f"Job {i} occurs during shift {s}")

    print("\nWorker Idle Times:")
    for k in model.workers:
        print(f"Worker {k} idle time: {model.idle_time[k].value}")


    final_end_time = max(model.end_time[j].value for j in model.jobs)

    print(f"\nFinal End Time of Last Job: {final_end_time}")


    # If you wish to see the complete status and log of the solver
    # print(solver.solve(model, tee=True))
    return model



def plot_schedule(model, title):
    tasks = []
    starts = []
    ends = []

    for j in model.jobs:
        for k in model.workers:
            if model.worker_assigned[j, k].value > 0.5:
                tasks.append(f"Job {j} by Worker {k}")
                starts.append(model.start_time[j].value)
                ends.append(model.start_time[j].value + jobs_data[j][1])

    colors = {
        1: "red",
        2: "blue",
        3: "green",
        4: "yellow",
        5: "purple",
        6: "cyan",
        7: "orange",
        8: "pink"
    }

    fig, ax = plt.subplots(figsize=(10, len(model.workers) * 3))

    # Для каждого рабочего рисуем задачи, назначенные ему
    for idx, k in enumerate(model.workers):
        assigned_jobs = [(j, model.start_time[j].value, model.start_time[j].value + jobs_data[j][1]) for j in model.jobs if model.worker_assigned[j, k].value > 0.5]
        sorted_jobs = sorted(assigned_jobs, key=lambda x: x[1])
        for job in sorted_jobs:
            project_id = task_to_project[job[0]]
            ax.broken_barh([(job[1], job[2] - job[1])], (idx*3, 2), facecolors=(colors[project_id]))
            duration = jobs_data[job[0]][1]
            job_name = jobs_data[job[0]][0]
            ax.text((2*job[1] + duration) / 2, idx*3 + 1, f"{job_name} ({duration}h)", ha='center', va='center', color='white')

    ax.set_xlabel('Time')
    ax.set_ylabel('Workers')
    ax.set_yticks([idx*3 + 1 for idx in range(len(model.workers))])
    ax.set_yticklabels([f"Worker {k}" for k in model.workers])
    ax.grid(True)

    legend_elements = [Patch(facecolor=colors[i], edgecolor='gray', label=f'Project {i}') for i in project_data.keys()]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))

    ax.set_title(title)
    plt.tight_layout()
    plt.show()




def plot_combined_schedule(model1, model2, title1="First Model", title2="Second Model"):
    project_colors_dark = {
        1: "red",
        2: "blue",
        3: "green",
    }
    project_colors_light = {
        1: "pink",
        2: "lightblue",
        3: "lightgreen",
    }

    fig, ax = plt.subplots(figsize=(12, len(model1.workers) * 3))

    for idx, k in enumerate(model1.workers):
        assigned_jobs1 = [(j, model1.start_time[j].value, model1.end_time[j].value) for j in model1.jobs if model1.worker_assigned[j, k].value > 0.5]
        sorted_jobs1 = sorted(assigned_jobs1, key=lambda x: x[1])
        for job in sorted_jobs1:
            duration = job[2] - job[1]
            ax.broken_barh([(job[1], duration)], (idx*3, 2), facecolors=project_colors_dark[model1.task_to_project[job[0]]])
            ax.text(job[1] + duration / 2, idx * 3 + 1, f"J{job[0]} ({duration}h)", ha='center', va='center', fontsize=8, color='black')

    for idx, k in enumerate(model2.workers):
        assigned_jobs2 = [(j, model2.start_time[j].value, model2.end_time[j].value) for j in model2.jobs if model2.worker_assigned[j, k].value > 0.5]
        sorted_jobs2 = sorted(assigned_jobs2, key=lambda x: x[1])
        for job in sorted_jobs2:
            duration = job[2] - job[1]
            ax.broken_barh([(job[1], duration)], (idx*3, 2), facecolors=project_colors_light[model2.task_to_project[job[0]]], alpha=0.5)
            ax.text(job[1] + duration / 2, idx * 3 + 1, f"J{job[0]} ({duration}h)", ha='center', va='center', fontsize=8, color='black')

    ax.set_xlabel('Time')
    ax.set_ylabel('Workers')
    ax.set_yticks([idx*3 + 1 for idx in range(len(model1.workers))])
    ax.set_yticklabels([f"Worker {k}" for k in model1.workers])
    ax.grid(True)

    legend_elements = [
        Patch(facecolor='red', label='Project 1 - Model 1'),
        Patch(facecolor='blue', label='Project 2 - Model 1'),
        Patch(facecolor='green', label='Project 3 - Model 1'),
        Patch(facecolor='pink', label='Project 1 - Model 2', alpha=0.5),
        Patch(facecolor='lightblue', label='Project 2 - Model 2', alpha=0.5),
        Patch(facecolor='lightgreen', label='Project 3 - Model 2', alpha=0.5)
    ]

    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    plt.tight_layout()
    plt.show()






model_1000 = build_and_solve(1000)
plot_schedule(model_1000, "Schedule with worker_weight = 1000")

model_minus_1 = build_and_solve(-1)
plot_schedule(model_minus_1, "Schedule with worker_weight = -1")
# plot_combined_schedule(model_1000, model_minus_1, "worker_weight = 1000", "worker_weight = -1")
