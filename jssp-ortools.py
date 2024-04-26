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
with open(f'data_from_df{data_from}.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# with open(f'data30_10_100.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)

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
# for o in operations:
#     model.Add(sum(assignment[(o, w)] for w in workers) == 1)  # Каждая операция назначена хотя бы одному работнику
    
#     # Получаем требуемую специальность и разряд для операции
#     required_skill = jobs_data[o][0]
#     required_grade = jobs_data[o][3]
    
#     for w in workers:
#         # Получаем специальность и разряд рабочего
#         worker_skill = workers_data[w][0]
#         worker_grade = workers_data[w][2]
        
#         # Проверяем, соответствует ли специальность и разряд рабочего требованиям операции
#         if not (required_skill == worker_skill and worker_grade >= required_grade):
#             # Если специальность не соответствует или разряд рабочего ниже требуемого,
#             # добавляем ограничение, что данная операция не может быть назначена этому работнику
#             model.Add(assignment[(o, w)] == 0)


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

# print(available_operations_for_worker)
# for worker_id, ops in available_operations_for_worker.items():
#     for o1 in ops:
#         for o2 in ops:
#             if o1 < o2:
#                 print(f'current worker {worker_id} {o1} vs {o2}')
#                 end_before_start = model.NewBoolVar('end_before_start_o%io%i_w%i' % (o1, o2, worker_id))
#                 start_before_end = model.NewBoolVar('start_before_end_o%io%i_w%i' % (o1, o2, worker_id))

#                 # Ограничение, что o1 заканчивается до начала o2
#                 model.Add(start_time[o2] >= start_time[o1] + duration[o1]).OnlyEnforceIf(end_before_start)
#                 # Ограничение, что o2 заканчивается до начала o1
#                 model.Add(start_time[o1] >= start_time[o2] + duration[o2]).OnlyEnforceIf(start_before_end)
                    
#                 # Добавляем условие, что если обе операции назначены рабочему w, то одно из ограничений выше должно выполняться
#                 model.AddBoolOr([end_before_start, start_before_end]).OnlyEnforceIf([assignment[(o1, worker_id)], assignment[(o2, worker_id)]])



# Для каждого работника и операции не из его проекта добавляем ограничения по времени
# for o in operations:
#     for w in workers:
#         for o2 in operations:
#             if operation_to_project[o] != operation_to_project[o2]:
#                 model.Add(start_time[o2] >= start_time[o] + duration[o]).OnlyEnforceIf(assignment[(o, w)])
#                 model.Add(start_time[o] >= start_time[o2] + duration[o2]).OnlyEnforceIf(assignment[(o2, w)])

print('Целевая функция')
# Целевая функция
for o in operations:
    model.Add(makespan >= start_time[o] + duration[o])
model.Minimize(makespan)

# Решение модели
print('Решение модели')
solver = cp_model.CpSolver()
# solver.SetNumThreads(8)
solver.parameters.log_search_progress = True
solver.parameters.num_search_workers = 10
# solver.parameters.max_time_in_seconds = 10

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
    # print('Количество решений:', solution_printer.SolutionCount())
    print(f'Решение было найдено за {solver.WallTime() / 1000} секунд')
else:
    print('Решение не найдено.')

def plot_gantt_schedule(solution, start_time, duration, operation_to_worker, operation_to_project):
    tasks_data = []
    base_date = datetime.strptime(data_from, '%Y-%m-%d')
    base_date = base_date.replace(hour=8, minute=0, second=0, microsecond=0)
    for operation, worker in operation_to_worker.items():
        project = operation_to_project[operation]  # Получаем ID проекта для операции
        start = base_date + timedelta(minutes=solution.Value(start_time[operation]))
        end = start + timedelta(minutes=duration[operation])
        # Добавляем информацию о проекте в описание каждой задачи
        tasks_data.append({
            "Worker": f"Worker {worker}",
            "Start": start,
            "Finish": end,
            "Description": f"Operation {operation}",
            "Project": f"Project {project}"  # Используем ID проекта для раскраски
        })

    df = pd.DataFrame(tasks_data)
    
    # Создание диаграммы Ганта с группировкой по работникам и раскраской по проектам
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Worker", color="Project", text="Description",
                      labels={"Worker": "Worker"}, title="Schedule by Worker")
    fig.update_traces(textposition='inside')
    fig.update_layout(xaxis_title='Time', yaxis_title='Worker')
    fig.show()


def plot_gantt_schedule_projects(solution, start_time, duration, operation_to_project, operation_to_worker):
    tasks_data = []
    base_date = datetime.now()
    # Изменение: Формирование базовой даты из переменной 'data_from'
    base_date = datetime.strptime(data_from, '%Y-%m-%d')
    base_date = base_date.replace(hour=8, minute=0, second=0, microsecond=0)

    for operation, project in operation_to_project.items():
        # Предполагается, что `operation_to_worker` уже определён и содержит соответствие операции и работника
        worker = operation_to_worker[operation]  # Получение работника для операции
        start = base_date + timedelta(minutes=solution.Value(start_time[operation]))
        end = start + timedelta(minutes=duration[operation])
        # Изменение: Добавление работника в описание и использование его для раскраски
        tasks_data.append({
            "Project": f"Project {project}",
            "Start": start,
            "Finish": end,
            "Description": f"Operation {operation}, Worker {worker}",
            "Worker": f"Worker {worker}"  # Используется для раскраски
        })

    df = pd.DataFrame(tasks_data)
    
    # Изменение: Раскраска по работникам, группировка по проектам
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Project", color="Worker", text="Description",
                      labels={"Project": "Project"}, title="Schedule by Project")
    fig.update_traces(textposition='inside')
    fig.update_layout(xaxis_title='Time', yaxis_title='Project')
    fig.show()


def plot_worker_utilization(solution, start_time, duration, workers):
    worker_utilization = {worker: 0 for worker in workers}
    total_time = 0
    
    for operation in duration.keys():
        worker = operation_to_worker[operation]  # Используйте ваш маппинг операция-работник
        op_duration = duration[operation]
        worker_utilization[worker] += op_duration
        total_time = max(total_time, solution.Value(start_time[operation]) + op_duration)

    utilization_data = [{"Worker": f"Worker {worker}", "Utilization": (util / total_time) * 100} for worker, util in worker_utilization.items()]
    df = pd.DataFrame(utilization_data)

    fig = px.bar(df, x='Worker', y='Utilization', text='Utilization')
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', xaxis_title="Worker", yaxis_title="Utilization (%)", title="Worker Utilization")
    fig.show()

operation_to_worker = {o: w for o in operations for w in workers if solver.Value(assignment[(o, w)])}
operation_to_project = {}
for project_id, details in project_data.items():
    for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
        operation_to_project[operation_id] = project_id


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

def check_all_constraints(solver, model):
    # Возвращает True, если все ограничения модели соблюдены
    return solver.StatusName(status) in ["OPTIMAL", "FEASIBLE"]

if check_all_constraints(solver, model):
    print("Все ограничения модели соблюдены.")
    if check_projects_no_overlap(solver, start_time, duration, operation_to_project):
        print("Задачи в рамках одного проекта не пересекаются.")
    if check_workers_no_overlap(solver, start_time, duration, assignment, operations, workers):
        print("Задачи, назначенные одному рабочему, не пересекаются.")


plot_gantt_schedule(solver, start_time, duration, operation_to_worker, operation_to_project)
plot_gantt_schedule_projects(solver, start_time, duration, operation_to_project, operation_to_worker)
plot_worker_utilization(solver, start_time, duration, workers)