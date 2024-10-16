from ortools.sat.python import cp_model
import json
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

data_from = '2023-03-24'   

def extract_number(s):
    match = re.search(r'\d+$', s)  # ищем одну или более цифр в конце строки
    return str(match.group()) if match else None

with open('controlers.txt', 'r') as file:
    # Читаем каждую строку файла, удаляем символы перевода строки
    # и сохраняем строки в список
    controlers = [line.strip() for line in file]


# Загрузка данных
# with open(f'data_from_df{data_from}.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)

with open(f'data30_10_100.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

workers_data = {int(k): v for k, v in data['Machines'].items()}
jobs_data = {int(k): v for k, v in data['Operations'].items()}
project_data = {int(k): v for k, v in data['Jobs'].items()}

operation_to_project = {}
for project_id, details in project_data.items():
    for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
        operation_to_project[operation_id] = project_id


from ortools.sat.python import cp_model

class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Callback для вывода промежуточных решений."""
    def __init__(self, operations, workers, start_time, assignment):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._operations = operations
        self._workers = workers
        self._start_time = start_time
        self._assignment = assignment
        self._solution_count = 0

    def OnSolutionCallback(self):
        self._solution_count += 1
        print('Решение %i' % self._solution_count)
        for o in self._operations:
            for w in self._workers:
                if self.Value(self._assignment[(o, w)]):
                    print('Операция %i назначена на работника %i, начиная с времени %i' % (o, w, self.Value(self._start_time[o])))

    def SolutionCount(self):
        return self._solution_count


def create_model(jobs_data, workers_data, project_data, alpha=0.5, beta=0.5):
    # Инициализация модели
    print('Инициализация модели')
    model = cp_model.CpModel()

    #  данные 
    print('данные')
    operations = jobs_data.keys() 
    workers = workers_data.keys() 
    projects = project_data.keys() 

    duration = {k: v[1] for k, v in jobs_data.items()}  # Продолжительность операций
    worker_skill = {k: v[0] for k, v in workers_data.items()}  # Навыки работников
    job_required_skill = {k: v[0] for k, v in jobs_data.items()}  # Требуемые навыки для операций
    predecessors = {k: v[2] for k, v in jobs_data.items()}  
    worker_rate = {k: v[3] for k, v in workers_data.items()}
    available_operations_for_worker = {worker_id: [] for worker_id in workers_data}
    # print(workers_data)
    # Перебор всех операций и проверка, может ли рабочий их выполнить
    for job_id, (job_type, _, _, job_grade, _) in jobs_data.items():
        for worker_id, (worker_type, _, worker_grade, _, _) in workers_data.items():
            # Проверяем, соответствует ли специальность и достаточен ли разряд рабочего
            if job_type in worker_type and worker_grade >= job_grade:
                available_operations_for_worker[worker_id].append(job_id)

    # Переменные
    print('Переменные')
    start_time = {o: model.NewIntVar(0, sum(duration.values()), 'start_time_%i' % o) for o in operations}
    assignment = {(o, w): model.NewBoolVar('assignment_o%iw%i' % (o, w)) for o in operations for w in workers}
    makespan = model.NewIntVar(0, sum(duration.values()), 'makespan')
    total_cost = model.NewIntVar(0, sum(duration[o] * max(worker_rate.values()) for o in operations), 'total_cost')

    # Ограничения

    print('Ограничения')
    print('Предшественники')
    for o, ops in predecessors.items():
        for pred in ops:  # Для каждого предшественника пред
            model.Add(start_time[o] >= start_time[pred] + duration[pred])
    print('Операции')
    for o in operations:
        model.Add(sum(assignment[(o, w)] for w in workers) == 1)  # Каждая операция назначена хотя бы одному работнику
        if job_required_skill[o] in worker_skill:  # Если требуемый навык есть у работника
            for w in workers:
                model.Add(assignment[(o, w)] == 0).OnlyEnforceIf(worker_skill[w].NotContains(job_required_skill[o]))

    print('Стоимость')
    # Рассчитываем общую стоимость выполнения операций
    operation_costs = []
    for o in operations:
        for w in workers:
            # Стоимость выполнения операции o работником w = длительность операции * ставка работника * назначение (1 если назначен)
            cost_var = model.NewIntVar(0, duration[o] * worker_rate[w], f'cost_o{0}_w{w}')
            model.Add(cost_var == duration[o] * worker_rate[w] * assignment[(o, w)])
            operation_costs.append(cost_var)

    # Ограничение на общую стоимость выполнения всех операций
    model.Add(total_cost == sum(operation_costs))

    print('Машины')
    for w in workers:
        for o1 in operations:
            for o2 in operations:
                if o1 < o2:  # Чтобы не сравнивать пары дважды и не сравнивать операцию с самой собой
                    # Создаём условия, что либо операция o1 заканчивается до начала o2,
                    # либо операция o2 заканчивается до начала o1
                    # print(f'current worker {w} {o1} vs {o2}')
                    end_before_start = model.NewBoolVar('end_before_start_o%io%i_w%i' % (o1, o2, w))
                    start_before_end = model.NewBoolVar('start_before_end_o%io%i_w%i' % (o1, o2, w))

                    # Ограничение, что o1 заканчивается до начала o2
                    model.Add(start_time[o2] >= start_time[o1] + duration[o1]).OnlyEnforceIf(end_before_start)
                    # Ограничение, что o2 заканчивается до начала o1
                    model.Add(start_time[o1] >= start_time[o2] + duration[o2]).OnlyEnforceIf(start_before_end)
                    
                    # Добавляем условие, что если обе операции назначены рабочему w, то одно из ограничений выше должно выполняться
                    model.AddBoolOr([end_before_start, start_before_end]).OnlyEnforceIf([assignment[(o1, w)], assignment[(o2, w)]])

    print('Целевая функция')
    # Целевая функция
    for o in operations:
        model.Add(makespan >= start_time[o] + duration[o])
    # model.Minimize(makespan)
    model.Minimize(alpha * makespan + beta * total_cost)

    return model, start_time, assignment, makespan, duration, workers, total_cost

def model_solve(model, start_time, assignment, operations, workers, duration, total_cost, time_to_solve):
    # Решение модели
    print('Решение модели')
    solver = cp_model.CpSolver()
    # solver.SetNumThreads(8)
    # solver.parameters.log_search_progress = True
    solver.parameters.num_search_workers = 10
    solver.parameters.max_time_in_seconds = time_to_solve

    solution_printer = SolutionPrinter(operations, workers, start_time, assignment)
    # status = solver.Solve(model, solution_printer)
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for o in operations:
            for w in workers:
                if solver.Value(assignment[(o, w)]) == 1:
                    start_time_value = solver.Value(start_time[o])
                    print(f'Операция {o} назначена на работника {w}, начиная с времени {start_time_value}')
        print('Минимальный makespan:', solver.ObjectiveValue())
        total_cost_value = solver.Value(total_cost)
        print('Минимальная стоимость выполнения (total cost):', total_cost_value)
        # print('Количество решений:', solution_printer.SolutionCount())
        print(f'Решение было найдено за {solver.WallTime()} секунд')
        operation_to_worker = {o: w for o in operations for w in workers if solver.Value(assignment[(o, w)])}
        if check_all_constraints(solver, model, status):
            print("Все ограничения модели соблюдены.")
            if check_projects_no_overlap(solver, start_time, duration, operation_to_project):
                print("Задачи в рамках одного проекта не пересекаются.")
            if check_workers_no_overlap(solver, start_time, duration, assignment, operations, workers):
                print("Задачи, назначенные одному рабочему, не пересекаются.")
        return solver, operation_to_worker
    else:
        print('Решение не найдено.')
        return None, None

def plot_gantt_schedule(solver, start_time, duration, operation_to_worker, operation_to_project, show=False):
    tasks_data = []
    base_date = datetime.strptime(data_from, '%Y-%m-%d')
    base_date = base_date.replace(hour=8, minute=0, second=0, microsecond=0)
    
    for operation, worker in operation_to_worker.items():
        project = operation_to_project[operation]
        start = base_date + timedelta(minutes=solver.Value(start_time[operation]))
        end = start + timedelta(minutes=duration[operation])
        tasks_data.append({
            "Worker": f"Worker {worker}",
            "Start": start,
            "Finish": end,
            "Description": f"Operation {operation}",
            "Project": f"Project {project}"
        })

    df = pd.DataFrame(tasks_data)
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Worker", color="Project", text="Description",
                      labels={"Worker": "Worker"}, title="Schedule by Worker")
    fig.update_traces(textposition='inside')
    fig.update_layout(xaxis_title='Time', yaxis_title='Worker')
    
    if show:
        fig.show()
    else:
        return fig.to_json()



def plot_gantt_schedule_projects(solver, start_time, duration, operation_to_project, operation_to_worker, show=False):
    tasks_data = []
    base_date = datetime.strptime(data_from, '%Y-%m-%d')
    base_date = base_date.replace(hour=8, minute=0, second=0, microsecond=0)

    for operation, project in operation_to_project.items():
        worker = operation_to_worker[operation]
        start = base_date + timedelta(minutes=solver.Value(start_time[operation]))
        end = start + timedelta(minutes=duration[operation])
        tasks_data.append({
            "Project": f"Project {project}",
            "Start": start,
            "Finish": end,
            "Description": f"Operation {operation}, Worker {worker}",
            "Worker": f"Worker {worker}"
        })

    df = pd.DataFrame(tasks_data)
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Project", color="Worker", text="Description",
                      labels={"Project": "Project"}, title="Schedule by Project")
    fig.update_traces(textposition='inside')
    fig.update_layout(xaxis_title='Time', yaxis_title='Project')
    
    if show:
        fig.show()
    else:
        return fig.to_json()


def plot_worker_utilization(solver, start_time, duration, workers, operation_to_worker, show=False):
    worker_utilization = {worker: 0 for worker in workers}
    total_time = 0
    
    for operation in duration.keys():
        worker = operation_to_worker[operation]
        op_duration = duration[operation]
        worker_utilization[worker] += op_duration
        total_time = max(total_time, solver.Value(start_time[operation]) + op_duration)

    utilization_data = [{"Worker": f"Worker {worker}", "Utilization": (util / total_time) * 100} for worker, util in worker_utilization.items()]
    df = pd.DataFrame(utilization_data)

    fig = px.bar(df, x='Worker', y='Utilization', text='Utilization')
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', xaxis_title="Worker", yaxis_title="Utilization (%)", title="Worker Utilization")
    
    if show:
        fig.show()
    else:
        return fig.to_json()




def check_overlap(task1, task2):
    # Возвращает True, если задачи пересекаются по времени
    start1, end1 = task1
    start2, end2 = task2
    return max(start1, start2) < min(end1, end2)


def check_projects_no_overlap(solver, start_time, duration, operation_to_project):
    project_tasks = {}
    # Группировка задач по проектам
    for operation in operation_to_project:
        project_id = operation_to_project[operation]
        if project_id not in project_tasks:
            project_tasks[project_id] = []
        start = solver.Value(start_time[operation])
        end = start + duration[operation]
        project_tasks[project_id].append((start, end))
    
    # Проверка на пересечение задач внутри каждого проекта
    for project_id, tasks in project_tasks.items():
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                if check_overlap(tasks[i], tasks[j]):
                    print(f"Задачи проекта {project_id} пересекаются: {tasks[i]} и {tasks[j]}")
                    return False
    return True

def check_workers_no_overlap(solver, start_time, duration, assignment, operations, workers):
    worker_tasks = {w: [] for w in workers}
    # Группировка задач по рабочим
    for o in operations:
        for w in workers:
            if solver.Value(assignment[(o, w)]) == 1:
                start = solver.Value(start_time[o])
                end = start + duration[o]
                worker_tasks[w].append((start, end))
    
    # Проверка на пересечение задач для каждого рабочего
    for w, tasks in worker_tasks.items():
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                if check_overlap(tasks[i], tasks[j]):
                    print(f"Задачи рабочего {w} пересекаются: {tasks[i]} и {tasks[j]}")
                    return False
    return True

def check_all_constraints(solver, model, status):
    # Возвращает True, если все ограничения модели соблюдены
    return solver.StatusName(status) in ["OPTIMAL", "FEASIBLE"]

def generate_output(solver, start_time, duration, assignment, total_cost, makespan, workers_data, project_data, operation_to_worker, operation_to_project):
    base_start_time = datetime(year=2023, month=9, day=19, hour=8)

    def convert_to_datetime(minutes_since_start):
        return base_start_time + timedelta(minutes=minutes_since_start)

    output_data = {}

    # Project Deadlines and End Times
    project_end_times = []
    for p, job_list_and_deadline in project_data.items():
        job_list = job_list_and_deadline[0]
        deadline = job_list_and_deadline[1]
        name = job_list_and_deadline[2]
        project_end_time = max(solver.Value(start_time[j]) + duration[j] for j in job_list)
        
        formatted_deadline = convert_to_datetime(deadline).strftime('%H:%M')
        formatted_end_time = convert_to_datetime(project_end_time).strftime('%H:%M')
        
        project_end_times.append({
            'project': p,
            'end_time': formatted_end_time,
            'deadline': formatted_deadline,
            'name': name
        })

    output_data['projects'] = project_end_times

    # Worker Performance and Costs
    worker_details = []
    total_expense = 0
    for worker_id in workers_data.keys():
        assigned_jobs_count = sum(1 for j in duration.keys() if solver.Value(assignment[(j, worker_id)]) == 1)
        total_minutes = sum(duration[j] for j in duration.keys() if solver.Value(assignment[(j, worker_id)]) == 1)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        worker_rate = workers_data[worker_id][3]  # Ставка работника
        worker_cost = total_minutes * worker_rate
        total_expense += worker_cost

        worker_details.append({
            'worker_id': worker_id,
            'specialization': workers_data[worker_id][0],
            'total_time': f"{round(hours)}ч {round(minutes)}мин",
            'tasks_assigned': assigned_jobs_count,
            'cost': f"{round(worker_cost)} руб."
        })

    output_data['workers'] = worker_details

    # Additional Info
    worker_times = [sum(duration[j] for j in duration.keys() if solver.Value(assignment[(j, worker_id)]) == 1) for worker_id in workers_data.keys()]
    average_work_time = sum(worker_times) / len(workers_data)
    variance = sum((time - average_work_time) ** 2 for time in worker_times) / len(workers_data)
    std_deviation = variance ** 0.5
    std_hours = int(std_deviation // 60)
    std_minutes = int(std_deviation % 60)

    final_end_time = max(solver.Value(start_time[j]) + duration[j] for j in duration.keys())
    final_time = convert_to_datetime(final_end_time)
    objective_value = solver.ObjectiveValue()

    output_data['additional_info'] = {
        'average_work_time': f"{average_work_time:.2f} мин",
        'std_deviation': f"{round(std_hours)}ч {round(std_minutes)}мин",
        'total_expense': f"{round(total_expense)} руб.",
        'final_end_time': final_time.strftime('%Y-%m-%d %H:%M'),
        'objective_value': f"{objective_value}"
    }

    return output_data

# Создание модели
# model, start_time, assignment, makespan, duration, workers, total_cost = create_model(jobs_data, workers_data, project_data, alpha=1, beta=0)

# # Решение модели
# solver, operation_to_worker = model_solve(model, start_time, assignment, jobs_data.keys(), workers_data.keys(), duration, total_cost)

operation_to_project = {}
for project_id, details in project_data.items():
    for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
        operation_to_project[operation_id] = project_id


# plot_gantt_schedule(solver, start_time, duration, operation_to_worker, operation_to_project)
# plot_gantt_schedule_projects(solver, start_time, duration, operation_to_project, operation_to_worker)
# plot_worker_utilization(solver, start_time, duration, workers)