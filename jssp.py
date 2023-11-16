from pyomo.environ import *
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyomo.opt import ProblemFormat
import logging
import random
import numpy as np
import time
import pickle
import cloudpickle
from datetime import datetime, timedelta
import json
import plotly
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots
from datagen import workers_data, jobs_data, project_data
from pyomo.util.infeasible import log_infeasible_constraints

random.seed(12345)

logging.getLogger('pyomo.util.infeasible').setLevel(logging.INFO)

# workers_data = {
#     # 1: ("Токарно-винторезная", "Токарь", 1, 50, None),
#     # 2: ("Слесарная", "Слесарь", 1, 50, None),
#     # 3: ("Вертикально-сверлильная", "Сверловщик", 1, 50, None),
#     # 4: ("Токарная с ЧПУ", "Токарь с ЧПУ", 1, 50, None),
#     # 5: ("Токарно-винторезная", "Токарь", 2, 55, None),
#     # 6: ("Слесарная", "Слесарь", 2, 55, None),
#     # 7: ("Вертикально-сверлильная", "Сверловщик", 2, 55, None),
#     # 8: ("Токарная с ЧПУ", "Токарь с ЧПУ", 2, 55, None),
#     9: ("Токарно-винторезная", "Токарь", 3, 60, (0,60)),
#     10: ("Слесарная", "Слесарь", 3, 60, None),
#     11: ("Вертикально-сверлильная", "Сверловщик", 3, 60, None),
#     12: ("Токарная с ЧПУ", "Токарь с ЧПУ", 3, 60, None),
#     13: ("Токарно-винторезная", "Токарь", 4, 65, None),
#     14: ("Слесарная", "Слесарь", 4, 65, None),
#     15: ("Вертикально-сверлильная", "Сверловщик", 4, 65, None),
#     16: ("Токарная с ЧПУ", "Токарь с ЧПУ", 4, 65, None),
#     17: ("Токарно-винторезная", "Токарь", 5, 70, None),
#     18: ("Слесарная", "Слесарь", 5, 70, None),
#     19: ("Вертикально-сверлильная", "Сверловщик", 5, 70, None),
#     20: ("Токарная с ЧПУ", "Токарь с ЧПУ", 5, 1000, None),
# }

# jobs_data = {
#     15: ("Токарно-винторезная", 5, [], 1),
#     25: ("Токарная с ЧПУ", 15, [15], 1),
#     35: ("Токарная с ЧПУ", 20, [25], 2),
#     45: ("Вертикально-сверлильная", 10, [35], 1),
#     55: ("Слесарная", 50, [45], 3),
#     65: ("Токарно-винторезная", 15, [], 2),
#     75: ("Токарная с ЧПУ", 20, [65], 2),
#     85: ("Токарная с ЧПУ", 25, [75], 3),
#     95: ("Вертикально-сверлильная", 15, [85], 1),
#     105: ("Слесарная", 55, [95], 3),
#     115: ("Токарно-винторезная", 20, [], 2),
#     125: ("Токарная с ЧПУ", 25, [115], 3),
#     135: ("Токарная с ЧПУ", 30, [125], 4),
#     145: ("Вертикально-сверлильная", 20, [135], 2),
#     155: ("Слесарная", 60, [145], 4),
#     165: ("Токарно-винторезная", 25, [], 3),
#     175: ("Токарная с ЧПУ", 30, [165], 4),
#     185: ("Токарная с ЧПУ", 35, [175], 5),
#     195: ("Вертикально-сверлильная", 25, [185], 3),
#     205: ("Слесарная", 65, [195], 5),
#     215: ("Токарно-винторезная", 30, [], 4),
#     225: ("Токарная с ЧПУ", 35, [215], 5),
#     235: ("Токарная с ЧПУ", 40, [225], 1),
#     245: ("Вертикально-сверлильная", 30, [235], 4),
#     255: ("Слесарная", 70, [245], 2),
#     265: ("Токарно-винторезная", 35, [], 5),
#     275: ("Токарная с ЧПУ", 40, [265], 1),
#     285: ("Токарная с ЧПУ", 45, [275], 2),
#     295: ("Вертикально-сверлильная", 35, [285], 5),
#     305: ("Слесарная", 75, [295], 2),
# }

# project_data = {
#     1: ([15, 25, 35, 45, 55], 120, 'ring'),
#     2: ([65, 75, 85, 95, 105], 480, 'ring2'),
#     3: ([115, 125, 135, 145, 155], 3 * 60, 'ring3'),
#     4: ([165, 175, 185, 195, 205], 4 * 60, 'ring4'),
#     5: ([215, 225, 235, 245, 255], 5 * 60, 'ring5'),
#     6: ([265, 275, 285, 295, 305], 6 * 60, 'ring6')
# }


with open('data.json', 'w', encoding='utf-8') as file:
    json.dump({
        'workers_data': workers_data,
        'jobs_data': jobs_data,
        'project_data': project_data
    }, file, ensure_ascii=False, indent=4)

with open('data.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

workers_data = {int(k): v for k, v in data['workers_data'].items()}
jobs_data = {int(k): v for k, v in data['jobs_data'].items()}
project_data = {int(k): v for k, v in data['project_data'].items()}

# Создание проекта недоступности
is_unavailability_present = any(worker_info[4] is not None for worker_info in workers_data.values())
unavailability_jobs = {}
job_id = max(jobs_data.keys()) + 1  # Начинаем с ID, следующего за последним в jobs_data

if is_unavailability_present:
    project_data[0] = ([], 480, 'unavailability')

    for worker_id, worker_info in workers_data.items():
        unavailability = worker_info[4]
        if unavailability:
            unavailability_jobs[job_id] = (worker_info[0], unavailability[1] - unavailability[0], [], 1, worker_id)  # Разряд 1 для всех задач недоступности
            project_data[0][0].append(job_id)  # Добавляем задачу в проект недоступности
            job_id += 1

    # Объединяем jobs_data с задачами недоступности
    jobs_data.update(unavailability_jobs)

print(project_data)
# print(jobs_data)

task_to_project = {j: p for p, (job_list, _, n) in project_data.items() for j in job_list}

for j in jobs_data.keys():
    if j not in task_to_project:
        print(f"Job {j} is not assigned to any project!")

def build_model(weight_makespan, weight_costs=1, hard_deadline=False):
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
    model.worker_qualification = Param(model.workers, initialize={k: v[2] for k, v in workers_data.items()})
    model.job_required_qualification = Param(model.jobs, initialize={k: v[3] for k, v in jobs_data.items()})
    model.cost_rate = Param(model.workers, initialize={k: v[3] for k, v in workers_data.items()})
    model.worker_unavailability = Param(model.workers, initialize={k: v[4] for k, v in workers_data.items()})
    unavailability_task_flags = {job_id: 1 if job_id in unavailability_jobs else 0 for job_id in model.jobs}
    model.is_unavailability_task = Param(model.jobs, within=Binary, initialize=unavailability_task_flags)

    

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

    weight_delay = 1  # это весовой коэффициент, который можно настроить

    # model.obj = Objective(
    #     expr=weight_balance * (model.max_work_time - model.min_work_time) +
    #         weight_makespan * sum(model.end_time[j] for j in model.jobs if not model.is_unavailability_task[j]) +
    #         weight_costs * sum(model.worker_assigned[j, k] * model.job_duration[j] * model.cost_rate[k] 
    #                         for j in model.jobs for k in model.workers if not model.is_unavailability_task[j]) +
    #         weight_delay * sum(model.project_delay[p] for p in model.projects) - 
    #         weight_workers * sum(model.worker_used[k] for k in model.workers),
    #     sense=minimize
    # )
    weight_idle = 1
    model.obj = Objective(
        expr=weight_makespan * model.makespan + # сделать время окончания последней операции
            weight_costs * 0.002 * sum(model.worker_assigned[j, k] * model.job_duration[j] * model.cost_rate[k] 
                            for j in model.jobs for k in model.workers if not model.is_unavailability_task[j]) +
                            # sum(model.end_time[j] for j in model.jobs if not model.is_unavailability_task[j]) +
                            weight_idle * sum(model.idle_time[k] for k in model.workers) +
            weight_delay * sum(model.project_delay[p] for p in model.projects),sense=minimize
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
        if not model.is_unavailability_task[i]:
            return model.end_time[i] <= model.makespan
        else:
            return Constraint.Skip
    model.makespan_constraint = Constraint(model.jobs, rule=makespan_rule)

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
    # model.write("model.nl")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Build execution time: {elapsed_time:.2f} seconds")
    
    return model

def remove_conflicting_assignments(model):
    changes = False
    for worker in model.workers:
        if model.worker_unavailability[worker]:
            start_unavail, end_unavail = model.worker_unavailability[worker]
            for job in model.jobs:
                    if model.worker_assigned[job, worker].value == 1:  # Если задача назначена рабочему
                        start_time = model.start_time[job].value
                        end_time = start_time + model.job_duration[job]
                        print(f'Рабочему {worker} назначена задача {job} в период {start_time}-{end_time}, он недоступен в период с {start_unavail}-{end_unavail}')

                        # Проверяем пересечение с периодом недоступности
                        if start_time <= end_unavail and end_time >= start_unavail:
                            # Если пересечение есть, добавляем задачу в список для переназначения
                            # Снимаем задачу с рабочего
                            print(f'Задача {job} снята с рабочего {worker}')
                            model.worker_assigned[job, worker].set_value(0)
                            model.worker_assigned[job, worker].fix()
                            changes = True
    
    return model, changes

def solve_model(model, custom_data = False):
    # Solve the model
    # Фиксируем задачи недоступности за рабочими
    for job_id, job_info in unavailability_jobs.items():
        worker_id = job_info[4]  # Получаем ID рабочего из задачи недоступности

        # Фиксируем время начала и окончания задачи недоступности
        start_unavail, end_unavail = workers_data[worker_id][4]
        model.start_time[job_id].set_value(start_unavail)
        # model.end_time[job_id].set_value(end_unavail)
        model.start_time[job_id].fix()
        # model.end_time[job_id].fix()

        # Назначаем задачу недоступности соответствующему рабочему
        for k in model.workers:
            if k == worker_id:
                model.worker_assigned[job_id, k].set_value(1)
                model.worker_assigned[job_id, k].fix()
            else:
                model.worker_assigned[job_id, k].set_value(0)
                model.worker_assigned[job_id, k].fix()
    if custom_data:
        for idx, i in enumerate(start_times, start=1):
            model.start_time[idx].set_value(i)
            model.start_time[idx].fix()

        for key, value in data_dict.items():
            model.worker_assigned[key].set_value(value)
            model.worker_assigned[key].fix()
    start_time = time.time()
    solver = SolverFactory('scip')
    # solver.options['threads'] = 1024
    # solver.options['set/lp/initalgorithm'] = 'd'
    # solver.options['warmstart'] = True
    result = solver.solve(model, tee=True)
    print('Model Solved')
    print("Solver Status:", result.solver.status)
    print("Solver Termination Condition:", result.solver.termination_condition)
    end_time = time.time()
    elapsed_time = end_time - start_time
    if result.solver.status == SolverStatus.warning and result.solver.termination_condition == TerminationCondition.infeasible:
        # Log infeasible constraints
        log_infeasible_constraints(model)


    if ((result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal)) or (result.solver.termination_condition == TerminationCondition.feasible):
        # Print the solution
        print("\nWorker Assignments with Order:")
        for k in model.workers:
            assigned_jobs = [(j, model.start_time[j].value) for j in model.jobs if model.worker_assigned[j, k].value > 0.5 and not model.is_unavailability_task[j]]
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
            if p != 0:  # Пропускаем проект недоступности
                job_list = job_list_and_deadline[0]
                deadline = job_list_and_deadline[1]
                name = job_list_and_deadline[2]
                project_end_time = max(model.end_time[j].value for j in job_list if not model.is_unavailability_task[j])

                formatted_deadline = convert_to_datetime(deadline).strftime('%H:%M')
                formatted_end_time = convert_to_datetime(project_end_time).strftime('%H:%M')
                
                print(f"Project name {name} id {p} ends at: {formatted_end_time}. Deadline: {formatted_deadline}.")

        total_expense = 0  # Переменная для подсчета общих затрат

        print("\nWorker Performance and Costs:")
        for k in model.workers:
            assigned_jobs_count = sum(model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j])
            total_minutes = sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j])
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
        worker_times = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j]) for k in model.workers]
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

        print(f'weight balance - {model.max_work_time.value - model.min_work_time.value}')
        print(f'end time {sum(model.end_time[j].value for j in model.jobs if not model.is_unavailability_task[j]) * 0.1}')
        print(f'cost rate {sum(model.worker_assigned[j, k].value * model.job_duration[j] * model.cost_rate[k] for j in model.jobs for k in model.workers if not model.is_unavailability_task[j]) * 0.002}')
        print(f'makespan {model.makespan.value}')
        print(f'delay {sum(model.project_delay[p].value for p in model.projects)}') 
        print(f'workers used {sum(model.worker_used[k].value for k in model.workers) * 15}')

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
        if p != 0:  # Пропускаем проект недоступности
            job_list = job_list_and_deadline[0]
            deadline = job_list_and_deadline[1]
            name = job_list_and_deadline[2]
            project_end_time = max(model.end_time[j].value for j in job_list if not model.is_unavailability_task[j])

            formatted_deadline = convert_to_datetime(deadline).strftime('%H:%M')
            formatted_end_time = convert_to_datetime(project_end_time).strftime('%H:%M')
            
            project_end_times.append({'project': p, 'end_time': formatted_end_time, 'deadline': formatted_deadline, 'name': name})

    output_data['projects'] = project_end_times

    # Worker Performance and Costs
    worker_details = []
    total_expense = 0
    for k in model.workers:
        assigned_jobs_count = sum(model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j])
        total_minutes = sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j])
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
    worker_times = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs if not model.is_unavailability_task[j]) for k in model.workers]
    average_work_time = sum(worker_times) / len(model.workers)
    variance = sum((time - average_work_time) ** 2 for time in worker_times) / len(model.workers)
    std_deviation = variance ** 0.5
    std_hours = int(std_deviation // 60)
    std_minutes = int(std_deviation % 60)

    final_end_time = max(model.end_time[j].value for j in model.jobs if not model.is_unavailability_task[j])
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

def time_label(t):
    """Convert time in minutes since 8am to a HH:MM format."""
    h, m = divmod(t + 8*60, 60)  # Add 8 hours (since the day starts at 8am)
    return f"{int(h) % 24:02}:{int(m):02}"  # % 24 is used to wrap around hours greater than 24

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




def save_model_to_file(model, filename="model.pkl"):
    """Сохраняет экземпляр модели в файл с использованием cloudpickle."""
    with open(filename, mode='wb') as file:
        cloudpickle.dump(model, file)

def load_model_from_file(filename="model.pkl"):
    """Загружает экземпляр модели из файла с использованием cloudpickle."""
    with open(filename, mode='rb') as file:
        model = cloudpickle.load(file)
    return model
    


def convert_color(color):
    """Конвертировать цвет из формата matplotlib в строку для plotly."""
    r, g, b, a = color
    return f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {a})"

def time_to_datetime_str(base_time, minutes):
    # Преобразование минут в соответствующую дату и время
    new_time = base_time + timedelta(minutes=minutes)
    return new_time.strftime('%Y-%m-%d %H:%M:%S')

base_time = datetime(2023, 10, 1, 8, 0, 0) 

# Размер шрифтов
font_size = 20

def plot_gantt_schedule(model, show=True, ):
    gantt_data = []

    project_colors = [convert_color(c) for c in plt.cm.Paired(np.linspace(0, 1, len(project_data)))]
     # График по рабочим
    grouping_column = 'Worker'
    fig_title = "Schedule by Workers"
    for idx, k in enumerate(model.workers):
        unavailability = model.worker_unavailability[k]
        if unavailability is not None:
            task_data = dict(
                    Worker=f'Worker {k}: {workers_data[k][1]} (Разряд {model.worker_qualification[k]})',
                    Task=f"Worker {k}: is unavailable",
                    Start=time_to_datetime_str(base_time, unavailability[0]),
                    Finish=time_to_datetime_str(base_time, unavailability[1]),
                    Resource=f"Worker unavailability",
                    Color="grey"
            )
            gantt_data.append(task_data)
        for j in model.jobs:
            if model.worker_assigned[j, k].value > 0.5:
                start = time_to_datetime_str(base_time, model.start_time[j].value)
                finish = time_to_datetime_str(base_time, model.start_time[j].value + model.job_duration[j])
                project_id = model.task_to_project[j]
                    
                task_data = dict(
                        Worker=f'Worker {k}: {workers_data[k][1]} (Разряд {model.worker_qualification[k]})',
                        Task=f"Worker {k}:  job {j} {jobs_data[j][0]} (Разряд {model.job_required_qualification[j]})",
                        Start=start,
                        Finish=finish,
                        Resource=f"Project {project_data[project_id][2]}",
                        Color=project_colors[project_id % len(project_colors)]
                )
                    
                gantt_data.append(task_data)
    df = pd.DataFrame(gantt_data)
    order = sorted(df['Worker'].unique(), key=lambda x: int(x.split(" ")[1].replace(':', '')))
    return create_gantt_chart(df, grouping_column, fig_title, order, model, show)

def plot_gantt_schedule_projects(model, show=True):
    gantt_data = []

    project_colors = [convert_color(c) for c in plt.cm.Paired(np.linspace(0, 1, len(project_data)))]
    # График по проектам
    fig_title = "Schedule by Projects"
    grouping_column = 'Project'

    for idx, p in enumerate(project_data.keys()):
        for j in [j for j, proj in task_to_project.items() if proj == p]:
            start = time_to_datetime_str(base_time, model.start_time[j].value)
            finish = time_to_datetime_str(base_time, model.start_time[j].value + model.job_duration[j])

            for k in model.workers:
                if model.worker_assigned[j, k].value > 0.5:
                    task_data = dict(
                            Project=f"{project_data[p][2]}",
                            Task=f"Project {p}: {jobs_data[j][0]}",
                            Start=start,
                            Finish=finish,
                            Resource=f"Worker {k}",
                    )
                        
                    gantt_data.append(task_data)
    df = pd.DataFrame(gantt_data)
    order = [project_data[p][2] for p in sorted(project_data.keys())]
    return create_gantt_chart(df, grouping_column, fig_title, order, model, show)
 

    
def create_gantt_chart(df, grouping_column, fig_title, order, model, show):
    fig = px.timeline(df, 
                  x_start="Start", 
                  x_end="Finish", 
                  y=grouping_column, 
                  color="Resource", 
                  title=fig_title,
                  category_orders={grouping_column: order},
                  hover_data=["Task"])

    num_of_workers = len(model.workers)
    min_start = min(model.start_time[j].value for j in model.jobs)
    max_end = max(model.start_time[j].value + model.job_duration[j] for j in model.jobs)
    duration_in_minutes = max_end - min_start

    fig.update_layout(
        height=num_of_workers * 100, 
        width=duration_in_minutes * 10,
        title_font=dict(size=font_size + 2),
        legend_font=dict(size=font_size),
        hoverlabel=dict(font=dict(size=font_size))
    )

    fig.update_xaxes(tickfont=dict(size=font_size))
    fig.update_yaxes(tickfont=dict(size=font_size), title_font=dict(size=font_size + 2))

    # fig.update_yaxes(categoryorder="total descending")  # Опционально: для сортировки задач
    if show:
        fig.show()
    else:
        fig_json = plotly.io.to_json(fig)
        return fig_json
        


def plot_worker_utilization_interactive(model, show=True):

    worker_names = [f"Worker {k}" for k in model.workers]
    num_of_workers = len(model.workers)
    total_minutes = [sum(model.job_duration[j] * model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    assigned_jobs_counts = [sum(model.worker_assigned[j, k].value for j in model.jobs) for k in model.workers]
    max_time = 480
    utilization_percentage = [(time_spent/max_time)*100 for time_spent in total_minutes]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=worker_names, y=total_minutes, name='Total Working Time (min)', text=[f"{util:.2f}%" for util in utilization_percentage], textposition='outside', marker_color='blue'),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(x=worker_names, y=assigned_jobs_counts, name='Assigned Jobs Count', mode='lines+markers+text', text=assigned_jobs_counts, textposition='top center', marker=dict(color='green')),
        secondary_y=True
    )

    fig.update_layout(title_text="Worker Utilization and Assigned Jobs", width= num_of_workers * 100 , height=40 * len(worker_names) + 200,shapes=[
        dict(
            type="line",
            x0=worker_names[0],
            x1=worker_names[-1], 
            y0=max_time,
            y1=max_time,
            line=dict(color="red", width=1.5, dash="dot")
        )
    ])
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode='lines', line=dict(color="red", width=1.5, dash="dot"), name='8 hours - End of Shift')
    )   

    fig.update_layout(title_text="Worker Utilization and Assigned Jobs", title_font=dict(size=font_size + 2))

    fig.update_xaxes(tickfont=dict(size=font_size))
    fig.update_yaxes(tickfont=dict(size=font_size), title_font=dict(size=font_size + 2), secondary_y=False)
    fig.update_yaxes(tickfont=dict(size=font_size), title_font=dict(size=font_size + 2), secondary_y=True)

    fig.update_layout(legend_font=dict(size=font_size), hoverlabel=dict(font=dict(size=font_size)))

    # Подписи
    fig.update_traces(textfont=dict(size=font_size))

    fig.update_yaxes(title_text="Total Working Time (min)", secondary_y=False, range=[0, max_time + 50])
    fig.update_yaxes(title_text="Number of Assigned Jobs", secondary_y=True)

    if show:
        fig.show()
    else:
        fig_json = plotly.io.to_json(fig)
        return fig_json



# TODO разряды рабочих и влияние на временной норматив операции. 
# график зависимости норматива от разряда линейный, сменный план по умолчанию. 
# возможность учета сразу нескольких смен в расписании потребует ввод доп ограничений: график рабочих, межсменная задача, станки учет