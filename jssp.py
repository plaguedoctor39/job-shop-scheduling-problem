from pyomo.environ import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyomo.opt import ProblemFormat
import random
import numpy as np
import time
import pickle

def save_model(model, filename):
    with open(filename, 'wb') as file:
        pickle.dump(model, file)

def load_model(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

random.seed(12345)

# workers_data = {
#         1: "Токарно-винторезная",
#         2: "Слесарная",
#         3: "Вертикально-сверлильная",
#         4: "Токарная с ЧПУ",
#         5: "Токарно-винторезная",
#         6: "Слесарная",
#         7: "Вертикально-сверлильная",
#         8: "Токарная с ЧПУ",
#         9: "Токарно-винторезная",
#         10: "Слесарная",
#         11: "Вертикально-сверлильная",
#         12: "Токарная с ЧПУ",
#         13: "Токарно-винторезная",
#         14: "Слесарная",
#         15: "Вертикально-сверлильная",
#         16: "Токарная с ЧПУ",
#     }


# jobs_data = {
#         15: ("Токарно-винторезная", 5, []),
#         25: ("Токарная с ЧПУ", 15, [15]),
#         35: ("Токарная с ЧПУ", 20, [25]),
#         45: ("Вертикально-сверлильная", 10, [35]),
#         55: ("Слесарная", 50, [45]),
#         100: ("Токарно-винторезная", 10, []),
#         110: ("Слесарная", 25, [100]),
#         120: ("Токарно-винторезная", 35, []),
#         130: ("Слесарная", 30, [120]),
#         140: ("Токарная с ЧПУ", 5, [130]),
#         150: ("Вертикально-сверлильная", 10, [140]),
#     }

# project_data = {
#         1: [15, 25, 35, 45, 55],
#         2: [100, 110],
#         3: [120, 130, 140, 150]
#     }



# 1. Генерация рабочих
workers_data = {}
specializations = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
num_workers = 10

# Рассчитываем, сколько рабочих каждой специальности нам нужно
workers_per_specialization = num_workers // len(specializations)

for worker_id in range(1, num_workers + 1):
    # Находим специализацию на основе текущего worker_id
    spec_index = (worker_id - 1) % len(specializations)
    workers_data[worker_id] = specializations[spec_index]


# 2. Генерация работ
jobs_data = {}
num_jobs = 20

# Рассчитываем, сколько задач с каждой специализацией нам нужно
jobs_per_specialization = num_jobs // len(specializations)

for job_id in range(1, num_jobs + 1):
    # Находим специализацию на основе текущего job_id
    spec_index = min((job_id - 1) // jobs_per_specialization, len(specializations) - 1)
    job_duration = random.randint(5, 60)
    jobs_data[job_id] = (specializations[spec_index], job_duration, [])


# 3. Генерация проектов и добавление предшественников к работам в проекте
project_data = {}
job_id = 1
project_counter = 1

while job_id <= num_jobs:
    project_size = random.randint(2, 5)  # Случайный размер проекта между 2 и 5
    current_project_jobs = list(range(job_id, min(job_id + project_size, num_jobs + 1)))
    
    project_data[project_counter] = current_project_jobs
    project_counter += 1
    
    # Добавление предшественников для задач в текущем проекте
    for idx, j_id in enumerate(current_project_jobs):
        if idx > 0:  # Если это не первая задача в проекте
            jobs_data[j_id] = (jobs_data[j_id][0], jobs_data[j_id][1], [j_id-1])
            
    job_id += len(current_project_jobs)


# Счетчик для специализаций среди рабочих
worker_specializations_count = {spec: 0 for spec in specializations}
for specialization in workers_data.values():
    worker_specializations_count[specialization] += 1

# Счетчик для требуемых специализаций среди задач
job_specializations_count = {spec: 0 for spec in specializations}
for specialization, _, _ in jobs_data.values():
    job_specializations_count[specialization] += 1

print("Специализации рабочих:")
for spec, count in worker_specializations_count.items():
    print(f"{spec}: {count}")

print("\nТребуемые специализации для задач:")
for spec, count in job_specializations_count.items():
    print(f"{spec}: {count}")


# print(workers_data)
# print(jobs_data)
# print(project_data)



task_to_project = {j: p for p, job_list in project_data.items() for j in job_list}
for j in jobs_data.keys():
    if j not in task_to_project:
        print(f"Job {j} is not assigned to any project!")

# print(task_to_project)
def build_model(weight_balance, weight_makespan):
    start_time = time.time()

    model = ConcreteModel()

    

    def are_unrelated(i, j):
        """Возвращает True, если задачи i и j относятся к разным проектам."""
        return model.task_to_project[i] != model.task_to_project[j]


    # Sets
    model.workers = Set(initialize=list(workers_data.keys()))
    model.jobs = Set(initialize=list(jobs_data.keys()))

    # Parameters
    model.specialization = Param(model.workers, initialize=workers_data)
    model.job_duration = Param(model.jobs, initialize={k: v[1] for k, v in jobs_data.items()})
    # model.job_required_specialization = Param(model.jobs, initialize={k: v[0] for k, v in jobs_data.items()})
    model.job_required_specialization = Param(model.jobs, within=Any, initialize={k: v[0] for k, v in jobs_data.items()})
    model.predecessors = Param(model.jobs, within=Any, initialize={k: v[2] for k, v in jobs_data.items()})
    
    model.task_to_project = Param(model.jobs, initialize=task_to_project)



    # Variables
    model.start_time = Var(model.jobs, domain=NonNegativeReals)
    model.end_time = Var(model.jobs, domain=NonNegativeReals)
    model.worker_assigned = Var(model.jobs, model.workers, domain=Binary)
    model.makespan = Var(domain=NonNegativeReals)
    model.idle_time = Var(model.workers, domain=NonNegativeReals) # время простоя рабочего
    model.idle_time_between_tasks = Var(model.jobs, model.jobs, model.workers, domain=NonNegativeReals) # время простоя между задачами для рабочего
    model.y = Var(model.jobs, model.jobs, model.workers, within=Binary) # вспомогательная бинарная переменная для реализации ограничения неперекрытия

    model.worker_used = Var(model.workers, domain=Binary)
    model.max_work_time = Var(domain=NonNegativeReals)
    model.min_work_time = Var(domain=NonNegativeReals)


    bigM = sum(model.job_duration.values())
    # bigM = 1000

    # Objective (You may need to specify the objective depending on your specific requirements)
    # model.obj = Objective(expr=model.makespan, sense=minimize)
    # model.obj = Objective(expr=model.max_work_time - model.min_work_time, sense=minimize)
    # model.obj = Objective(expr=weight_balance * (model.max_work_time - model.min_work_time) + 
    #                          weight_makespan * model.makespan, sense=minimize)
    model.obj = Objective(expr=weight_balance * (model.max_work_time - model.min_work_time) + 
                      weight_makespan * sum(model.end_time[j] for j in model.jobs), sense=minimize)

    # worker_weight = 1000  # Чем выше этот вес, тем более предпочтительным становится минимизировать число рабочих
    # model.obj = Objective(expr=sum(model.start_time[j] for j in model.jobs) + worker_weight * sum(model.worker_used[k] for k in model.workers), sense=minimize)


    # Constraints


    # Задача не может начаться до завершения всех ее предшественников
    def general_precedence_rule(model, i):
        return model.start_time[i] >= sum(model.end_time[j] for j in model.predecessors[i])
    model.general_precedence_constraint = Constraint(model.jobs, rule=general_precedence_rule)

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

    def worker_time_limit_rule(model, k):
        return sum(model.job_duration[i] * model.worker_assigned[i, k] for i in model.jobs) <= 8*60
    model.worker_time_limit = Constraint(model.workers, rule=worker_time_limit_rule)

    def max_work_time_rule(model, k):
        return model.max_work_time >= sum(model.job_duration[j] * model.worker_assigned[j, k] for j in model.jobs)
    model.max_work_time_constraint = Constraint(model.workers, rule=max_work_time_rule)

    def min_work_time_rule(model, k):
        return model.min_work_time <= sum(model.job_duration[j] * model.worker_assigned[j, k] for j in model.jobs)
    model.min_work_time_constraint = Constraint(model.workers, rule=min_work_time_rule)

    model.write(filename='model.mps', format=ProblemFormat.mps)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Build execution time: {elapsed_time:.2f} seconds")
    
    return model

def solve_model(model):
    # Solve the model
    start_time = time.time()
    solver = SolverFactory('scip')
    solver.options['threads'] = 6
    result = solver.solve(model)
    print('Model Solved')
    print("Solver Status:", result.solver.status)
    print("Solver Termination Condition:", result.solver.termination_condition)
    end_time = time.time()
    elapsed_time = end_time - start_time




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


    # print("\nWorker Idle Times:")
    # for k in model.workers:
    #     print(f"Worker {k} idle time: {model.idle_time[k].value}")

    for k in model.workers:
        assigned_jobs_count = sum(model.worker_assigned[j, k].value for j in model.jobs)
        total_minutes = sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        print(f"Worker {k} ({workers_data[k]}) worked for total time: {hours}h {minutes}m and has {int(assigned_jobs_count)} tasks assigned.")

    # Список времени работы для каждого рабочего
    worker_times = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]

    # Вычисляем среднее время работы
    average_work_time = sum(worker_times) / len(model.workers)

    # Вычисляем стандартное отклонение
    variance = sum((time - average_work_time) ** 2 for time in worker_times) / len(model.workers)
    std_deviation = variance ** 0.5

    # Конвертируем стандартное отклонение в часы и минуты
    std_hours = int(std_deviation // 60)
    std_minutes = int(std_deviation % 60)

    print(f"\nСтандартное отклонение времени работы рабочего: {std_hours}h {std_minutes}m")

    final_end_time = max(model.end_time[j].value for j in model.jobs)

    print(f"\nFinal End Time of Last Job: {final_end_time}")
    print(f"Solve execution time: {elapsed_time:.2f} seconds")
    objective_value = model.obj.expr()
    print(f"Value of the objective function: {objective_value}")

    # If you wish to see the complete status and log of the solver
    # print(solver.solve(model, tee=True))


def plot_schedule(model, title):
    tasks = []
    starts = []
    ends = []
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(project_data)))

    for j in model.jobs:
        for k in model.workers:
            if model.worker_assigned[j, k].value > 0.5:
                tasks.append(f"Job {j} by Worker {k}")
                starts.append(model.start_time[j].value)
                ends.append(model.start_time[j].value + jobs_data[j][1])

    fig, ax = plt.subplots(figsize=(10, len(model.workers) * 0.6))  # уменьшим высоту каждого рабочего для лучшего масштабирования

    for idx, k in enumerate(model.workers):
        assigned_jobs = [(j, model.start_time[j].value, model.start_time[j].value + jobs_data[j][1]) for j in model.jobs if model.worker_assigned[j, k].value > 0.5]
        sorted_jobs = sorted(assigned_jobs, key=lambda x: x[1])
        for job in sorted_jobs:
            project_id = task_to_project[job[0]]
            ax.broken_barh([(job[1], job[2] - job[1])], (idx*0.6, 0.5), facecolors=(colors[project_id % len(colors)]))
            duration = jobs_data[job[0]][1]
            job_name = jobs_data[job[0]][0]
            ax.text((2*job[1] + duration) / 2, idx*0.6 + 0.25, f"{job_name} ({duration}m)", ha='center', va='center', color='white', fontsize=6)

    ax.set_xlabel('Time')
    ax.set_ylabel('Workers')
    ax.set_yticks([idx*0.6 + 0.25 for idx in range(len(model.workers))])
    ax.set_yticklabels([f"Worker {k}" for k in model.workers], fontsize=8)
    ax.grid(True)

    legend_elements = [Patch(facecolor=colors[i % len(colors)], edgecolor='gray', label=f'Project {i}') for i in project_data.keys()]
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


def plot_worker_load(model):
    worker_names = [f"Worker {k} ({workers_data[k]})" for k in model.workers]
    tasks_counts = [sum(model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    total_times = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]

    # Convert total times from minutes to hours for plotting
    total_hours = [t / 60 for t in total_times]

    # Create subplots with 2 y-axes
    fig, ax1 = plt.subplots(figsize=(15, 6))  # Увеличиваем размер фигуры
    ax2 = ax1.twinx()

    # Plot total hours on the first y-axis
    ax1.bar(worker_names, total_hours, color='b', alpha=0.6, label='Total hours worked')
    ax1.set_ylabel('Total hours worked', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xticklabels(worker_names, rotation=45, ha='right')  # Поворачиваем метки x-оси

    # Plot tasks counts on the second y-axis
    ax2.plot(worker_names, tasks_counts, color='r', marker='o', label='Tasks assigned', linestyle='--')
    ax2.set_ylabel('Tasks assigned', color='r')
    ax2.tick_params(axis='y', labelcolor='r')

    # Setting the title and showing the plot
    ax1.set_title('Workers Load')
    fig.tight_layout()
    plt.show()



def plot_worker_utilization(model):
    title = "Worker Utilization and Assigned Jobs"
    worker_names = [f"Worker {k}" for k in model.workers]
    total_minutes = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    assigned_jobs_counts = [sum(model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    max_time = 480  # 8 hours in minutes
    utilization_percentage = [(time_spent/max_time)*100 for time_spent in total_minutes]

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Bar plot for total working time
    bars = ax1.bar(worker_names, total_minutes, color='blue', label='Total Working Time (min)', alpha=0.6)
    ax1.set_ylabel('Total Working Time (min)', color='blue')
    ax1.set_ylim(0, max_time + 50)
    ax1.axhline(max_time, color="red", linestyle="--", label="Max Available Time")
    ax1.set_xticklabels(worker_names, rotation=45, ha='right')  # Поворачиваем метки x-оси

    # Displaying utilization percentage on the bars
    for idx, (util, bar) in enumerate(zip(utilization_percentage, bars)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, height + 5, f"{util:.2f}%", ha='center', color='black', fontsize=9)
    
    # Plotting total assigned jobs on the right y-axis
    ax2 = ax1.twinx()
    ax2.plot(worker_names, assigned_jobs_counts, color='green', marker='o', label='Assigned Jobs Count', linestyle='--')
    ax2.set_ylabel('Number of Assigned Jobs', color='green')
    for i, txt in enumerate(assigned_jobs_counts):
        ax2.annotate(txt, (worker_names[i], assigned_jobs_counts[i] + 0.5), color='green', ha='center')

    # Legends and titles
    fig.tight_layout()
    fig.legend(loc="upper left", bbox_to_anchor=(0.05, 1))
    ax1.set_title(title)

    plt.show()








# model_1000 = build_and_solve(1000)
# plot_schedule(model_1000, "Schedule with worker_weight = 1000")

model11 = build_model(1,1)
solve_model(model11)
# model11.start_time[6].set_value(120)
# model11.start_time[6].fix()
# solve_model(model11)
with open("solution_output.txt", "w") as file:

    # Запись значений переменных
    for v in model11.component_objects(Var, active=True):
        file.write(f"Variable {v}\n")
        varobject = getattr(model11, str(v))
        for index in varobject:
            file.write(f"   {index} {varobject[index].value}\n")

    # Запись значения целевой функции
    for o in model11.component_objects(Objective, active=True):
        file.write(f"Objective {o} value: {value(o)}\n")

def exclude_solution(model):
    current_solution = [(j, k) for j in model.jobs for k in model.workers if model.worker_assigned[j, k].value > 0.5]
    
    num_constraints = sum(1 for _ in model.component_objects(Constraint, active=True))
    model.add_component(
        f"exclude_solution_{num_constraints + 1}", 
        Constraint(expr=sum(model.worker_assigned[j, k] for j, k in current_solution) <= len(current_solution) - 1))

num_solutions = 30
for i in range(num_solutions):
    solve_model(model11)
    print("Solution", i+1)
    
    exclude_solution(model11)

# plot_worker_load(model11)
plot_worker_utilization(model11)

# TODO разряды рабочих и влияние на временной норматив операции. 
# график зависимости норматива от разряда линейный, сменный план по умолчанию. 
# возможность учета сразу нескольких смен в расписании потребует ввод доп ограничений: график рабочих, межсменная задача, станки учет