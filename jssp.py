from pyomo.environ import *
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyomo.opt import ProblemFormat
import random
import numpy as np
import time
import pickle
from datetime import datetime, timedelta

def save_model(model, filename):
    with open(filename, 'wb') as file:
        pickle.dump(model, file)

def load_model(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

random.seed(12345)

workers_data = {
    1: ("Токарно-винторезная", 1, 50),
    2: ("Слесарная", 1, 50),
    3: ("Вертикально-сверлильная", 1, 50),
    4: ("Токарная с ЧПУ", 1, 50),
    5: ("Токарно-винторезная", 2, 55),
    6: ("Слесарная", 2, 55),
    7: ("Вертикально-сверлильная", 2, 55),
    8: ("Токарная с ЧПУ", 2, 55),
    9: ("Токарно-винторезная", 3, 60),
    10: ("Слесарная", 3, 60),
    11: ("Вертикально-сверлильная", 3, 60),
    12: ("Токарная с ЧПУ", 3, 60),
    13: ("Токарно-винторезная", 4, 65),
    14: ("Слесарная", 4, 65),
    15: ("Вертикально-сверлильная", 4, 65),
    16: ("Токарная с ЧПУ", 4, 65),
}

jobs_data = {
    15: ("Токарно-винторезная", 5, [], 1),
    25: ("Токарная с ЧПУ", 15, [15], 1),
    35: ("Токарная с ЧПУ", 20, [25], 2),
    45: ("Вертикально-сверлильная", 10, [35], 1),
    55: ("Слесарная", 50, [45], 3),
    100: ("Токарно-винторезная", 10, [], 2),
    110: ("Слесарная", 25, [100], 2),
    120: ("Токарно-винторезная", 35, [], 3),
    130: ("Слесарная", 30, [120], 4),
    140: ("Токарная с ЧПУ", 5, [130], 3),
    150: ("Вертикально-сверлильная", 10, [140], 3),
}

project_data = {
        1: ([15, 25, 35, 45, 55], 2 * 60),
        2: ([100, 110], 8 * 60),
        3: ([120, 130, 140, 150], 3 * 60)
    }



def gen_data():
    # Создаем случайный набор работников
    num_workers = 10
    specializations = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
    grades = list(range(1, 5))
    cost_rates = [5.0, 5.5, 6.0, 6.5]

    workers_data = {}
    for i in range(1, num_workers + 1):
        spec = random.choice(specializations)
        grade = random.choice(grades)
        rate = cost_rates[grade - 1]
        workers_data[i] = (spec, grade, rate)

    # Генерация проектов
    num_projects = 10
    max_tasks_per_project = 5
    project_data = {}

    jobs_data = {}
    job_id = 1

    workers_pool = list(workers_data.keys())

    for p in range(1, num_projects + 1):
        project_data[p] = []
        num_tasks = random.randint(1, max_tasks_per_project)
        for _ in range(num_tasks):
            chosen_worker = random.choice(workers_pool)
            workers_pool.remove(chosen_worker)
            
            spec, grade, _ = workers_data[chosen_worker]
            duration = random.randint(5, 50)  # Продолжительность задачи в минутах
            dependencies = [job_id - 1] if job_id - 1 in jobs_data else []
            
            jobs_data[job_id] = (spec, duration, dependencies, grade)
            project_data[p].append(job_id)
            
            job_id += 1
            
            if not workers_pool:
                workers_pool = list(workers_data.keys())

    print("Generated workers_data:", workers_data)
    print("\nGenerated jobs_data:", jobs_data)
    print("\nGenerated project_data:", project_data)
    return workers_data, jobs_data, project_data

# workers_data, jobs_data, project_data = gen_data()


# # Счетчик для специализаций среди рабочих
# worker_specializations_count = {spec: 0 for spec in specializations}
# for specialization in workers_data.values():
#     worker_specializations_count[specialization] += 1

# # Счетчик для требуемых специализаций среди задач
# job_specializations_count = {spec: 0 for spec in specializations}
# for specialization, _, _ in jobs_data.values():
#     job_specializations_count[specialization] += 1

# print("Специализации рабочих:")
# for spec, count in worker_specializations_count.items():
#     print(f"{spec}: {count}")

# print("\nТребуемые специализации для задач:")
# for spec, count in job_specializations_count.items():
#     print(f"{spec}: {count}")




task_to_project = {j: p for p, (job_list, _) in project_data.items() for j in job_list}

for j in jobs_data.keys():
    if j not in task_to_project:
        print(f"Job {j} is not assigned to any project!")

def build_model(weight_balance, weight_makespan, weight_costs=1, hard_deadline=False):
    start_time = time.time()

    model = ConcreteModel()

    
    print(type(model))
    def are_unrelated(i, j):
        """Возвращает True, если задачи i и j относятся к разным проектам."""
        return model.task_to_project[i] != model.task_to_project[j]


    # Sets
    model.workers = Set(initialize=list(workers_data.keys()))
    model.jobs = Set(initialize=list(jobs_data.keys()))
    model.projects = Set(initialize=project_data.keys())

    # Parameters
    model.specialization = Param(model.workers, initialize={k: v[0] for k, v in workers_data.items()})
    model.job_duration = Param(model.jobs, initialize={k: v[1] for k, v in jobs_data.items()})
    # model.job_required_specialization = Param(model.jobs, initialize={k: v[0] for k, v in jobs_data.items()})
    model.job_required_specialization = Param(model.jobs, within=Any, initialize={k: v[0] for k, v in jobs_data.items()})
    model.predecessors = Param(model.jobs, within=Any, initialize={k: v[2] for k, v in jobs_data.items()})
    
    model.task_to_project = Param(model.jobs, initialize=task_to_project)
    model.worker_qualification = Param(model.workers, initialize={k: v[1] for k, v in workers_data.items()})
    model.job_required_qualification = Param(model.jobs, initialize={k: v[3] for k, v in jobs_data.items()})
    model.cost_rate = Param(model.workers, initialize={k: v[2] for k, v in workers_data.items()})


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
    model.worker_deviation = Var(model.workers, domain=NonNegativeReals)  # отклонение времени каждого рабочего от среднего значения
    model.average_work_time = Var(domain=NonNegativeReals)  # среднее рабочее время
    model.project_delay = Var(model.projects, within=NonNegativeReals)


    bigM = sum(model.job_duration.values())
    # bigM = 1000

    # Objective (You may need to specify the objective depending on your specific requirements)
    # model.obj = Objective(expr=model.makespan, sense=minimize)
    # model.obj = Objective(expr=weight_balance * (model.max_work_time - model.min_work_time) + 
    #                   weight_makespan * sum(model.end_time[j] for j in model.jobs), sense=minimize)
    
    # model.obj = Objective(expr=weight_balance * (model.max_work_time - model.min_work_time) + 
    #                   weight_makespan * sum(model.end_time[j] for j in model.jobs) + 
    #                   sum(model.worker_deviation[k] * model.worker_deviation[k] for k in model.workers), 
    #                   sense=minimize)
    # model.obj = Objective(expr=weight_balance * (model.max_work_time - model.min_work_time) + 
    #                   weight_makespan * sum(model.end_time[j] for j in model.jobs) + 
    #                   sum(model.worker_deviation[k] * model.worker_deviation[k] for k in model.workers) +
    #                   weight_costs * sum(model.worker_assigned[j, k] * model.job_duration[j] * model.cost_rate[k] for j in model.jobs for k in model.workers),
    #                   sense=minimize)
    weight_delay = 1  # это весовой коэффициент, который можно настроить

    model.obj = Objective(
        expr=weight_balance * (model.max_work_time - model.min_work_time) +
            weight_makespan * sum(model.end_time[j] for j in model.jobs) +
            sum(model.worker_deviation[k] * model.worker_deviation[k] for k in model.workers) +
            weight_costs * sum(model.worker_assigned[j, k] * model.job_duration[j] * model.cost_rate[k] for j in model.jobs for k in model.workers) +
            weight_delay * sum(model.project_delay[p] for p in model.projects),
        sense=minimize
    )





    # Constraints


    # Задача не может начаться до завершения всех ее предшественников
    def general_precedence_rule(model, i):
        return model.start_time[i] >= sum(model.end_time[j] for j in model.predecessors[i])
    model.general_precedence_constraint = Constraint(model.jobs, rule=general_precedence_rule)

    # если рабочий используется хотя бы для одной работы, то его переменная worker_used равна 1
    def worker_usage_rule(model, i, k):
        return model.worker_assigned[i, k] <= model.worker_used[k]

    model.worker_usage_constraint = Constraint(model.jobs, model.workers, rule=worker_usage_rule)

    # def qualification_rule(model, i, k):
    #     return model.worker_qualification[k] >= model.job_required_qualification[i]

    def worker_assignment_rule(model, i, k):
        specialization_match = model.specialization[k] == model.job_required_specialization[i]
        qualification_match = model.worker_qualification[k] >= model.job_required_qualification[i]
        
        if specialization_match and qualification_match:
            return model.worker_assigned[i, k] <= 1
        else:
            return model.worker_assigned[i, k] == 0

    model.worker_assignment_constraint = Constraint(model.jobs, model.workers, rule=worker_assignment_rule)

    # Определим среднее рабочее время
    def average_work_time_rule(model):
        return model.average_work_time == sum(sum(model.job_duration[j] * model.worker_assigned[j, k] for j in model.jobs) for k in model.workers) / len(model.workers)
    model.average_work_time_constraint = Constraint(rule=average_work_time_rule)

    # Определим отклонение для каждого рабочего от среднего значения
    def worker_deviation_rule(model, k):
        return model.worker_deviation[k] >= model.average_work_time - sum(model.job_duration[j] * model.worker_assigned[j, k] for j in model.jobs)
    model.worker_deviation_constraint = Constraint(model.workers, rule=worker_deviation_rule)


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

    # # задача может быть назначена рабочему только если его специализация соответствует требованиям задачи
    # def specialization_rule(model, i, k):
    #     if model.specialization[k] == model.job_required_specialization[i]:
    #         return model.worker_assigned[i, k] <= 1
    #     else:
    #         return model.worker_assigned[i, k] == 0
    # model.specialization_constraint = Constraint(model.jobs, model.workers, rule=specialization_rule)

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

    def project_delay_rule(model, p):
        last_task = project_data[p][0][-1]
        if hard_deadline:
            return model.end_time[last_task] <= project_data[p][1]
        else:
            return model.end_time[last_task] <= project_data[p][1] + model.project_delay[p]



    model.project_delay_constr = Constraint(model.projects, rule=project_delay_rule)


    model.write(filename='model.mps', format=ProblemFormat.mps)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Build execution time: {elapsed_time:.2f} seconds")
    
    return model

def solve_model(model, custom_data = False):
    # Solve the model
    if custom_data:
        for idx, i in enumerate(start_times, start=1):
            model.start_time[idx].set_value(i)
            model.start_time[idx].fix()

        for key, value in data_dict.items():
            model.worker_assigned[key].set_value(value)
            model.worker_assigned[key].fix()
    start_time = time.time()
    solver = SolverFactory('scip')
    # solver.options['threads'] = 6
    # solver.options['set/lp/initalgorithm'] = 'd'
    # solver.options['warmstart'] = True
    result = solver.solve(model, tee=True)
    print('Model Solved')
    print("Solver Status:", result.solver.status)
    print("Solver Termination Condition:", result.solver.termination_condition)
    end_time = time.time()
    elapsed_time = end_time - start_time



    if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
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
        start_time = datetime(year=2023, month=9, day=19, hour=8)
        def convert_to_datetime(minutes_since_start):
            return start_time + timedelta(minutes=minutes_since_start)

        print("\nProject Deadlines and End Times:")
        for p, job_list_and_deadline in project_data.items():
            job_list = job_list_and_deadline[0]
            deadline = job_list_and_deadline[1]
            project_end_time = max(model.end_time[j].value for j in job_list)

            formatted_deadline = convert_to_datetime(deadline).strftime('%H:%M')
            formatted_end_time = convert_to_datetime(project_end_time).strftime('%H:%M')
            
            print(f"Project {p} ends at: {formatted_end_time}. Deadline: {formatted_deadline}.")

        total_expense = 0  # Переменная для подсчета общих затрат

        print("\nWorker Performance and Costs:")
        for k in model.workers:
            assigned_jobs_count = sum(model.worker_assigned[j, k].value for j in model.jobs)
            total_minutes = sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            worker_cost = total_minutes * model.cost_rate[k]  # Рассчитываем затраты для рабочего
            total_expense += worker_cost  # Добавляем затраты рабочего к общим затратам
            print(f"Worker {k} ({workers_data[k]}) worked for total time: {hours}h {minutes}m, has {int(assigned_jobs_count)} tasks assigned and costs: {worker_cost:.2f} RUB.")


        for j in model.jobs:
            for k in model.workers:
                if model.worker_assigned[j, k].value == 1:  # Если рабочий k назначен на задачу j
                    print(f"Рабочий {k}, Специализация: {workers_data[k][0]}, Задача: {j}, Требуемый разряд: {jobs_data[j][3]}, Разряд рабочего: {workers_data[k][1]}")

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
        print('')
        print(f'Среднее время работы {average_work_time:.2f}min')
        print(f"\nСтандартное отклонение времени работы рабочего: {std_hours}h {std_minutes}m")
        print(f"\nTotal expenses for all workers: {total_expense:.2f} RUB.") 
        final_end_time = max(model.end_time[j].value for j in model.jobs)
        final_time = start_time + timedelta(minutes=final_end_time)

        print(f"\nFinal End Time of Last Job: {final_time.strftime('%Y-%m-%d %H:%M')}")

        print(f"Solve execution time: {elapsed_time:.2f} seconds")
        objective_value = model.obj.expr()
        print(f"Value of the objective function: {objective_value}")

        # If you wish to see the complete status and log of the solver
        # print(solver.solve(model, tee=True))
    else:
        print("No optimal solution found!")
    return result.solver.status

def generate_output(model):
    start_time = datetime(year=2023, month=9, day=19, hour=8)
    
    def convert_to_datetime(minutes_since_start):
        return start_time + timedelta(minutes=minutes_since_start)
    
    output_data = {}

    # Project Deadlines and End Times
    project_end_times = []
    for p, job_list_and_deadline in project_data.items():
        job_list = job_list_and_deadline[0]
        deadline = job_list_and_deadline[1]
        project_end_time = max(model.end_time[j].value for j in job_list)

        formatted_deadline = convert_to_datetime(deadline).strftime('%H:%M')
        formatted_end_time = convert_to_datetime(project_end_time).strftime('%H:%M')
        
        project_end_times.append({'project': p, 'end_time': formatted_end_time, 'deadline': formatted_deadline})

    output_data['projects'] = project_end_times

    # Worker Performance and Costs
    worker_details = []
    total_expense = 0
    for k in model.workers:
        assigned_jobs_count = sum(model.worker_assigned[j, k].value for j in model.jobs)
        total_minutes = sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        worker_cost = total_minutes * model.cost_rate[k]
        total_expense += worker_cost

        worker_details.append({
            'worker_id': k,
            'specialization': workers_data[k][0],
            'total_time': f"{hours}h {minutes}m",
            'tasks_assigned': int(assigned_jobs_count),
            'cost': f"{worker_cost:.2f} RUB"
        })

    output_data['workers'] = worker_details

    # Additional Info
    worker_times = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    average_work_time = sum(worker_times) / len(model.workers)
    variance = sum((time - average_work_time) ** 2 for time in worker_times) / len(model.workers)
    std_deviation = variance ** 0.5
    std_hours = int(std_deviation // 60)
    std_minutes = int(std_deviation % 60)

    final_end_time = max(model.end_time[j].value for j in model.jobs)
    final_time = start_time + timedelta(minutes=final_end_time)
    objective_value = model.obj.expr()

    output_data['additional_info'] = {
        'average_work_time': f"{average_work_time:.2f}min",
        'std_deviation': f"{std_hours}h {std_minutes}m",
        'total_expense': f"{total_expense:.2f} RUB",
        'final_end_time': final_time.strftime('%Y-%m-%d %H:%M'),
        'objective_value': f"{objective_value}"
    }

    return output_data



def plot_schedule(model, show=True):

    if show:
        pass
    else:
        # Если мы сохраняем график как изображение (веб-версия)
        matplotlib.use('agg')
    tasks = []
    starts = []
    ends = []
    title = 'Base Schedule'
    colors = plt.cm.Paired(np.linspace(0, 1, len(project_data)))

    for j in model.jobs:
        for k in model.workers:
            if model.worker_assigned[j, k].value > 0.5:
                tasks.append(f"Job {j} by Worker {k}")
                starts.append(model.start_time[j].value)
                ends.append(model.start_time[j].value + jobs_data[j][1])

    fig, ax = plt.subplots(figsize=(16, len(model.workers) * 0.6))  # уменьшим высоту каждого рабочего для лучшего масштабирования

    for idx, k in enumerate(model.workers):
        assigned_jobs = [(j, model.start_time[j].value, model.start_time[j].value + jobs_data[j][1]) for j in model.jobs if model.worker_assigned[j, k].value > 0.5]
        sorted_jobs = sorted(assigned_jobs, key=lambda x: x[1])
        for job in sorted_jobs:
            project_id = task_to_project[job[0]]
            ax.broken_barh([(job[1], job[2] - job[1])], (idx*0.6, 0.5), facecolors=(colors[project_id % len(colors)]))
            duration = jobs_data[job[0]][1]
            job_name = jobs_data[job[0]][0]
            ax.text((2*job[1] + duration) / 2, idx*0.6 + 0.25, f"{job_name} ({duration}m)", ha='center', va='center', color='black', fontsize=12)

    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel('Workers', fontsize=14)
    ax.set_yticks([idx*0.6 + 0.25 for idx in range(len(model.workers))])
    ax.set_yticklabels([f"Worker {k}" for k in model.workers], fontsize=12)
    ax.grid(True)

    legend_elements = [Patch(facecolor=colors[i % len(colors)], edgecolor='gray', label=f'Project {i}') for i in project_data.keys()]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))

    ax.set_title(title, fontsize=16)
    # plt.tight_layout()
    if show:
        plt.show()
    else:
        plt.tight_layout()
        fig.savefig("static/schedule_plot.png")
        plt.close()






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
    fig, ax1 = plt.subplots(figsize=(16, 6))  # Увеличиваем размер фигуры
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



def plot_worker_utilization(model, show=True):
    if show:
        pass
    else:
        # Если мы сохраняем график как изображение (веб-версия)
        matplotlib.use('agg')
    title = "Worker Utilization and Assigned Jobs"
    worker_names = [f"Worker {k}" for k in model.workers]
    total_minutes = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    assigned_jobs_counts = [sum(model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    max_time = 480  # 8 hours in minutes
    utilization_percentage = [(time_spent/max_time)*100 for time_spent in total_minutes]

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Bar plot for total working time
    bars = ax1.bar(worker_names, total_minutes, color='blue', label='Total Working Time (min)', alpha=0.6)
    ax1.set_ylabel('Total Working Time (min)', color='blue', fontsize=14)
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
    ax2.set_ylabel('Number of Assigned Jobs', color='green', fontsize=14)
    for i, txt in enumerate(assigned_jobs_counts):
        ax2.annotate(txt, (worker_names[i], assigned_jobs_counts[i] + 0.5), color='green', ha='center')

    # Legends and titles
    fig.tight_layout()
    fig.legend(loc="upper left", bbox_to_anchor=(0.05, 1))
    ax1.set_title(title, fontsize=16)
    if show:
        plt.show()
    else:
        plt.tight_layout()
        fig.savefig("static/utilization_plot.png")
        plt.close()



def calculate_obj_value(weight_balance,weight_makespan, model):
    return weight_balance * (model.max_work_time.value - model.min_work_time.value) + weight_makespan * sum(model.end_time[j].value for j in model.jobs)


start_times = [0.0, 31.0, 82.0, 0.0, 
               57.0, 120, 0.0, 24.0, 
               83.0, 111.0, 0.0, 22.0, 
               0.0, 32.0, 47.0, 75.0, 
               105, 0.0, 32.0, 53.0]

data_dict = {
    (1, 1): 0.0, (1, 2): 0.0, (1, 3): 0.0, (1, 4): 0.0, (1, 5): 1.0,
    (1, 6): 0.0, (1, 7): 0.0, (1, 8): 0.0, (1, 9): 0.0, (1, 10): 0.0,
    (2, 1): 0.0, (2, 2): 0.0, (2, 3): 0.0, (2, 4): 0.0, (2, 5): 1.0,
    (2, 6): 0.0, (2, 7): 0.0, (2, 8): 0.0, (2, 9): 0.0, (2, 10): 0.0,
    (3, 1): 1.0, (3, 2): 0.0, (3, 3): 0.0, (3, 4): 0.0, (3, 5): 0.0,
    (3, 6): 0.0, (3, 7): 0.0, (3, 8): 0.0, (3, 9): 0.0, (3, 10): 0.0,
    (4, 1): 0.9999999999999996, (4, 2): 0.0, (4, 3): 0.0, (4, 4): 0.0, (4, 5): 0.0,
    (4, 6): 0.0, (4, 7): 0.0, (4, 8): 0.0, (4, 9): 0.0, (4, 10): 0.0,
    (5, 1): 0.0, (5, 2): 0.0, (5, 3): 0.0, (5, 4): 0.0, (5, 5): 0.0,
    (5, 6): 0.0, (5, 7): 0.0, (5, 8): 0.0, (5, 9): 1.0, (5, 10): 0.0,
    (6, 1): 0.0, (6, 2): 0.0, (6, 3): 0.0, (6, 4): 0.0, (6, 5): 0.0,
    (6, 6): 0.0, (6, 7): 0.0, (6, 8): 0.0, (6, 9): 0.0, (6, 10): 1.0,
    (7, 1): 0.0, (7, 2): 1.0, (7, 3): 0.0, (7, 4): 0.0, (7, 5): 0.0,
    (7, 6): 0.0, (7, 7): 0.0, (7, 8): 0.0, (7, 9): 0.0, (7, 10): 0.0,
    (8, 1): 0.0, (8, 2): 0.0, (8, 3): 0.0, (8, 4): 0.0, (8, 5): 0.0,
    (8, 6): 1.0, (8, 7): 0.0, (8, 8): 0.0, (8, 9): 0.0, (8, 10): 0.0,
    (9, 1): 0.0, (9, 2): 1.0, (9, 3): 0.0, (9, 4): 0.0, (9, 5): 0.0,
    (9, 6): 0.0, (9, 7): 0.0, (9, 8): 0.0, (9, 9): 0.0, (9, 10): 0.0,
    (10, 1): 0.0, (10, 2): 1.0, (10, 3): 0.0, (10, 4): 0.0, (10, 5): 0.0,
    (10, 6): 0.0, (10, 7): 0.0, (10, 8): 0.0, (10, 9): 0.0, (10, 10): 0.0,
    (11, 1): 0.0, (11, 2): 0.0, (11, 3): 0.0, (11, 4): 0.0, (11, 5): 0.0,
    (11, 6): 0.0, (11, 7): 1.0, (11, 8): 0.0, (11, 9): 0.0, (11, 10): 0.0,
    (12, 1): 0.0, (12, 2): 0.0, (12, 3): 0.0, (12, 4): 0.0, (12, 5): 0.0,
    (12, 6): 0.0, (12, 7): 1.0, (12, 8): 0.0, (12, 9): 0.0, (12, 10): 0.0,
    (13, 1): 0.0, (13, 2): 0.0, (13, 3): 1.0, (13, 4): 0.0, (13, 5): 0.0,
    (13, 6): 0.0, (13, 7): 0.0, (13, 8): 0.0, (13, 9): 0.0, (13, 10): 0.0,
    (14, 1): 0.0, (14, 2): 0.0, (14, 3): 1.0, (14, 4): 0.0, (14, 5): 0.0,
    (14, 6): 0.0, (14, 7): 0.0, (14, 8): 0.0, (14, 9): 0.0, (14, 10): 0.0,
    (15, 1): 0.0, (15, 2): 0.0, (15, 3): 1.0, (15, 4): 0.0, (15, 5): 0.0,
    (15, 6): 0.0, (15, 7): 0.0, (15, 8): 0.0, (15, 9): 0.0, (15, 10): 0.0,
    (16, 1): 0.0, (16, 2): 0.0, (16, 3): 0.0, (16, 4): 1.0, (16, 5): 0.0,
    (16, 6): 0.0, (16, 7): 0.0, (16, 8): 0.0, (16, 9): 0.0, (16, 10): 0.0,
    (17, 1): 0.0, (17, 2): 0.0, (17, 3): 0.0, (17, 4): 1.0, (17, 5): 0.0,
    (17, 6): 0.0, (17, 7): 0.0, (17, 8): 0.0, (17, 9): 0.0, (17, 10): 0.0,
    (18, 1): 0.0, (18, 2): 0.0, (18, 3): 0.0, (18, 4): 0.0, (18, 5): 0.0,
    (18, 6): 0.0, (18, 7): 0.0, (18, 8): 1.0, (18, 9): 0.0, (18, 10): 0.0,
    (19, 1): 0.0, (19, 2): 0.0, (19, 3): 0.0, (19, 4): 0.0, (19, 5): 0.0,
    (19, 6): 0.0, (19, 7): 0.0, (19, 8): 1.0, (19, 9): 0.0, (19, 10): 0.0,
    (20, 1): 0.0, (20, 2): 0.0, (20, 3): 0.0, (20, 4): 0.0, (20, 5): 0.0,
    (20, 6): 0.0, (20, 7): 0.0, (20, 8): 1.0, (20, 9): 0.0, (20, 10): 0.0
}

def get_assignment():
    assignment_dict = {}
    for (job, worker), assigned in data_dict.items():
        if assigned == 1.0:
            assignment_dict[job] = (worker, jobs_data[job][0])

    print(assignment_dict)  

def solution_to_file(model):
    with open("solution_output.txt", "w") as file:

        # Запись значений переменных
        for v in model.component_objects(Var, active=True):
            file.write(f"Variable {v}\n")
            varobject = getattr(model, str(v))
            for index in varobject:
                file.write(f"   {index} {varobject[index].value}\n")
            file.write("\n")

        # Запись значения целевой функции
        for o in model.component_objects(Objective, active=True):
            file.write(f"Objective {o} value: {pyomo.environ.value(o)}\n")
    print('Done')


def exclude_solution(model):
    current_solution = [(j, k) for j in model.jobs for k in model.workers if model.worker_assigned[j, k].value > 0.5]
    
    num_constraints = sum(1 for _ in model.component_objects(Constraint, active=True))
    model.add_component(
        f"exclude_solution_{num_constraints + 1}", 
        Constraint(expr=sum(model.worker_assigned[j, k] for j, k in current_solution) <= len(current_solution) - 1))

def do_n_solutions(n, model):
    num_solutions = n
    for i in range(num_solutions):
        solve_model(model)
        print("Solution", i+1)
        
        exclude_solution(model)


# TODO разряды рабочих и влияние на временной норматив операции. 
# график зависимости норматива от разряда линейный, сменный план по умолчанию. 
# возможность учета сразу нескольких смен в расписании потребует ввод доп ограничений: график рабочих, межсменная задача, станки учет