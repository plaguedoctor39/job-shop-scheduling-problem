# Постановка задачи
# Задача поиска оптимального расписания
# на вход подается список доступных рабочих на смену, пул текущих задач с приоритетами и требованиями к специальностям, пул доступных машин, длина смены
# Ограничения:
# Задача выполняется только одним рабочим на одной машине,
# один рабочий не может выполнять больше одной задачи в одно время,
# Задачи должны быть выбраны решателем таким образом, чтобы уместились в смену
# Ограничение предшествования задач (задача не может начаться пока не завершен ее предшественник)
# Назначение задач с учетом специальностей и разрядов
# задачи назначаются на выполнение с учетом приоритетов 
# Задачи могут быть перенесены на след день
# Доступность машин и рабочих
# Ожидаемое поведение решателя:
# Выбор из пула задач оптимальное расписание на смену с учетом всех ограничений,
#  минимизация по времени т.е. выполнение наибольшего кол-ва задач за отведенное время
# Возможна оптимизация также по критерию стоимости, задачи не попавшие в пул на текущую смену переносятся на след день в пул задач и их приоритет соответственно повышается
from pyomo.environ import *
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.colors as mcolors
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.figure_factory as ff
import re

data_from = '2023-12-14'    
def solution_from_file(model):
    
    with open('scheduleRSC_234_1_result.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Load the ID to index mapping file
    # with open(f'id_to_workers_{data_from}.json', 'r', encoding='utf-8') as file:
    #     id_to_index = json.load(file)
    
    # Reverse the mapping to get index to ID mapping
    # index_to_id = {index: int(executor_id) for executor_id, index in id_to_index.items()}
    
    for operation_id in model.operations:
        for executor_id in model.workers:
            model.assignment[operation_id, executor_id].fix(0)
            
    # Fixing the model variables based on the solution
    for machine_index, machine_operations in data.items():
        executor_id = int(machine_index)
        for operation_details in machine_operations:
            operation_index = operation_details[0] - 1  # Adjust index if necessary
            start_time = operation_details[2]
            
            # Assuming 'operations' is a list of operation IDs in the model that matches the solution's order
            operation_id = operation_details[1]
            # Fixing assignment and start times
            model.assignment[operation_id, executor_id].fix(1)  # Fix assignment to 1 for specified worker and operation
            model.start_time[operation_id].fix(start_time)  # Fix start timex
            
            # Optionally fix end time if your model uses end time variables

    print("Solution loaded and variables fixed based on the provided solution.")
    return model

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

workers_data = {int(k): v for k, v in data['Machines'].items()}
jobs_data = {int(k): v for k, v in data['Operations'].items()}
project_data = {int(k): v for k, v in data['Jobs'].items()}

operation_to_project = {}
for project_id, details in project_data.items():
    for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
        operation_to_project[operation_id] = project_id

# Создание модели
model = ConcreteModel()

# Множества
model.operations = Set(initialize=jobs_data.keys())
model.workers = Set(initialize=workers_data.keys())
model.projects = Set(initialize=project_data.keys())

# Параметры
model.duration = Param(model.operations, initialize={k: v[1] for k, v in jobs_data.items()})
model.worker_skill = Param(model.workers, initialize={k: v[0] for k, v in workers_data.items()})
model.job_required_skill = Param(model.operations, initialize={k: v[0] for k, v in jobs_data.items()})
model.predecessors = Param(model.operations, within=Any, initialize={k: v[2] for k, v in jobs_data.items()})
# model.cost_rate = Param(model.workers, initialize={k: v[3] for k, v in workers_data.items()})
model.project_duration = Param(model.projects, initialize={project: sum(model.duration[o] for o in model.operations if operation_to_project[o] == project) for project in model.projects})


# Переменные
model.start_time = Var(model.operations, domain=NonNegativeReals, name='start_time')
# Дополнительные переменные для назначения работников на операции
model.assignment = Var(model.operations, model.workers, domain=Binary, name='assignment')
# Переменная для максимального времени завершения (makespan)
model.makespan = Var(domain=NonNegativeReals, name='makespan')
model.y = Var(model.operations, model.operations, model.workers, within=Binary, name="y")



# Ограничения
# Находим идентификатор самого длительного проекта
max_duration_project = max(model.projects, key=lambda p: sum(model.duration[o] for o in model.operations if operation_to_project[o] == p))

# M = 10000
M = sum(model.duration.values())
# M = 100

def non_overlap_rule_1(model, i, j, k):
        if i != j and operation_to_project[i] != operation_to_project[j]:
            return model.start_time[j] >= model.start_time[i] + model.duration[i] - M * (1 - model.assignment[i, k]) - M * (1 - model.y[i, j, k])
        return Constraint.Skip

def non_overlap_rule_2(model, i, j, k):
        if i != j and operation_to_project[i] != operation_to_project[j]:
            return model.start_time[i] >= model.start_time[j] + model.duration[j] - M * (1 - model.assignment[j, k]) - M * model.y[i, j, k]
        return Constraint.Skip

model.non_overlap_constraint_1 = Constraint(model.operations, model.operations, model.workers, rule=non_overlap_rule_1, name="non_overlap_constraint_1")
model.non_overlap_constraint_2 = Constraint(model.operations, model.operations, model.workers, rule=non_overlap_rule_2, name="non_overlap_constraint_2")

# def non_overlap_rule_3(model, i, j, k):
#     if i != j and operation_to_project[i] != operation_to_project[j]:
#         project_i_duration = model.project_duration[operation_to_project[i]]
#         project_j_duration = model.project_duration[operation_to_project[j]]
#         # Если проект i длится дольше, то предпочесть операцию i, иначе наоборот
#         if project_i_duration >= project_j_duration:
#             return model.start_time[j] >= model.start_time[i] + model.duration[i] - M * (1 - model.assignment[i, k]) - M * (1 - model.y[i, j, k])
#         else:
#             return Constraint.Skip
#     return Constraint.Skip

# def non_overlap_rule_4(model, i, j, k):
#     if i != j and operation_to_project[i] != operation_to_project[j]:
#         project_i_duration = model.project_duration[operation_to_project[i]]
#         project_j_duration = model.project_duration[operation_to_project[j]]
#         # Если проект j длится дольше, то предпочесть операцию j, иначе наоборот
#         if project_j_duration > project_i_duration:
#             return model.start_time[i] >= model.start_time[j] + model.duration[j] - M * (1 - model.assignment[j, k]) - M * model.y[i, j, k]
#         else:
#             return Constraint.Skip
#     return Constraint.Skip

# model.non_overlap_constraint_3 = Constraint(model.operations, model.operations, model.workers, rule=non_overlap_rule_3, name="non_overlap_constraint_3")
# model.non_overlap_constraint_4 = Constraint(model.operations, model.operations, model.workers, rule=non_overlap_rule_4, name="non_overlap_constraint_4")

# def non_overlap_rule_3(model, i, j, k):
#     if i != j:
#         if operation_to_project[i] == max_duration_project and operation_to_project[j] != max_duration_project:
#             # Операция i имеет приоритет перед j
#             return model.start_time[j] >= model.start_time[i] + model.duration[i] - M * (1 - model.assignment[i, k]) - M * (1 - model.y[i, j, k])
#         elif operation_to_project[j] == max_duration_project and operation_to_project[i] != max_duration_project:
#             # Операция j имеет приоритет перед i (для симметрии)
#             return model.start_time[i] >= model.start_time[j] + model.duration[j] - M * (1 - model.assignment[j, k]) - M * (1 - model.y[i, j, k])
#         else:
#             # Если обе операции принадлежат одинаковым проектам или ни одна не принадлежит самому длительному проекту, ограничение не применяется
#             return Constraint.Skip
#     else:
#         return Constraint.Skip

# model.non_overlap_constraint_3 = Constraint(model.operations, model.operations, model.workers, rule=non_overlap_rule_3, name="non_overlap_constraint_3")


# Ограничение, что работник назначается на операцию только если он имеет нужную квалификацию
def worker_skill_match_rule(model, o, w):
    # Check if the required skill for the operation is in the worker's skill list
    # This assumes model.worker_skill[w] is a list and model.job_required_skill[o] is an element that could be in the list
    # Return 1 (True) if the skill matches, otherwise 0 (False)
    return model.assignment[o, w] <= int(model.job_required_skill[o] in model.worker_skill[w])

model.worker_skill_match_constraint = Constraint(model.operations, model.workers, rule=worker_skill_match_rule, name='worker_skill_match_constraint')


# Ограничение, что каждая операция должна быть назначена как минимум одному работнику
def operation_assignment_rule(model, o):
    return sum(model.assignment[o, w] for w in model.workers) == 1

model.operation_assignment_constraint = Constraint(model.operations, rule=operation_assignment_rule, name='operation_assignment_constraint')

def general_precedence_rule(model, o):
        return model.start_time[o] >= sum(model.start_time[prev_op] + model.duration[prev_op] for prev_op in model.predecessors[o])
model.general_precedence_constraint = Constraint(model.operations, rule=general_precedence_rule, name='general_precedence_constraint')

# Целевая функция минимизирует makespan
def objective_rule(model):
    # Весовой коэффициент для суммы времен начала операций
    alpha = 0.0001
    
    # Минимизация makespan
    makespan_component = model.makespan
    
    # Минимизация суммы времен начала операций, умноженных на весовой коэффициент
    start_time_component = sum(model.start_time[o] for o in model.operations)
    
    # Комбинированная целевая функция
    return makespan_component
    #  + alpha * start_time_component

model.objective = Objective(rule=objective_rule, sense=minimize)


# Добавляем ограничение, что makespan больше или равен времени завершения каждой операции
def makespan_rule(model, o):
    return model.makespan >= model.start_time[o] + model.duration[o]
model.makespan_constraint = Constraint(model.operations, rule=makespan_rule, name='makespan_constraint')

model.write(filename=f'simplified_model{data_from}.mps', io_options={"symbolic_solver_labels": True})

# model = solution_from_file(model)
# Решение модели
solver = SolverFactory('scip')
solver.solve(model, tee=True)

# optimal_makespan = model.makespan.value

# # Добавление ограничения для фиксации makespan на найденном оптимальном значении
# def makespan_fixed_rule(model):
#     return model.makespan == optimal_makespan
# model.makespan_fixed_constraint = Constraint(rule=makespan_fixed_rule)

# # Модификация целевой функции для минимизации суммы времён начала операций
# def objective_rule_sum_start_times(model):
#     return sum(model.start_time[o] for o in model.operations)
# model.objective = Objective(rule=objective_rule_sum_start_times, sense=minimize)

# # Решение модифицированной модели
# solver.solve(model, tee=True)

# Организация вывода результатов по проектам
results_by_project = {}
for o in model.operations:
    assigned_worker = None
    for w in model.workers:
        if model.assignment[o, w].value == 1:
            assigned_worker = w
            break
    project_id = operation_to_project[o]
    start_time = model.start_time[o].value
    end_time = start_time + model.duration[o]
    
    # Добавляем результат в структуру данных
    if project_id not in results_by_project:
        results_by_project[project_id] = []
    results_by_project[project_id].append({
        'operation_id': o,
        'start_time': start_time,
        'end_time': end_time,
        'worker_id': assigned_worker
    })

# Вывод результатов по проектам
for project_id, operations in results_by_project.items():
    project_name = project_data[int(project_id)][2]  # Преобразование project_id обратно в int, если он был строкой
    print(f"Проект {project_id} ({project_name}):")
    for op in sorted(operations, key=lambda x: x['start_time']):
        print(f"  Операция {op['operation_id']}: Начало - {op['start_time']}, Конец - {op['end_time']}, Рабочий - {op['worker_id']}")
    print()  # Добавляем пустую строку для разделения проектов
print(f'makespan {model.makespan.value}')
print(f'start_time {sum(model.start_time[j].value for j in model.operations)}')

def time_to_datetime_str(base_time, minutes):
    # Преобразование минут в соответствующую дату и время
    new_time = base_time + timedelta(minutes=minutes)
    return new_time.strftime('%Y-%m-%d %H:%M:%S')



def convert_color(color):
    """Конвертировать цвет из формата matplotlib в строку для plotly."""
    # Добавляем альфа-канал, если он отсутствует
    if len(color) == 3:
        color = (*color, 1.0)  # Предполагаем полную непрозрачность для RGB цвета
    r, g, b, a = color
    return f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {a})"

base_date = datetime.strptime(data_from, '%Y-%m-%d')
# Установка времени начала в 8:00 утра
base_time = base_date.replace(hour=8, minute=0, second=0, microsecond=0)

def unique_colors(num_colors):
    """Генерация уникальных цветов."""
    colors = []

    for i in np.linspace(0, 1, num_colors):
        # Преобразование HSV цвета в RGB и добавление альфа-канала
        colors.append(mcolors.hsv_to_rgb((i, 1, 1)) + (1,))

    return colors
# for o in model.operations:
#     for w in model.workers:
#         if model.assignment[o, w].value == 1:
#             print(f"Операция {o} назначена исполнителю {w}")

# Размер шрифтов
font_size = 40
# диаграмма гантта 
def plot_gantt_schedule(model, show=True, ):
    gantt_data = []

    project_colors = [convert_color(c) for c in unique_colors(len(project_data))]

     # График по рабочим
    grouping_column = 'Worker'
    fig_title = "Расписание по Рабочим"
    for idx, k in enumerate(model.workers):
        # unavailability = model.worker_unavailability[k]
        # if unavailability is not None:
        #     task_data = dict(
        #             Worker=f'Worker {k}: {workers_data[k][1]} (Разряд {model.worker_qualification[k]})',
        #             Task=f"Worker {k}: is unavailable",
        #             Start=time_to_datetime_str(base_time, unavailability[0]),
        #             Finish=time_to_datetime_str(base_time, unavailability[1]),
        #             Resource=f"Worker unavailability",
        #             Color="grey"
        #     )
        #     gantt_data.append(task_data)
        for j in model.operations:
            if model.assignment[j, k].value > 0.5:
                start = time_to_datetime_str(base_time, model.start_time[j].value)
                finish = time_to_datetime_str(base_time, model.start_time[j].value + model.duration[j])
                project_id = operation_to_project[j]
                    
                task_data = dict(
                        Worker=f'Рабочий {k}:',
                        Task=f"Рабочий {k}: задача {j} тип{jobs_data[j][0]}",
                        Start=start,
                        Finish=finish,
                        Resource=f"ДСЕ {project_id}",
                        Color=project_colors[project_id % len(project_colors)]
                )
                # print(task_data)    
                gantt_data.append(task_data)
    df = pd.DataFrame(gantt_data)
    order = sorted(df['Worker'].unique(), key=lambda x: int(x.split(" ")[1].replace(':', '')))
    return create_gantt_chart(df, grouping_column, fig_title, order, model, show)

def plot_gantt_schedule_projects(model, show=True):
    gantt_data = []

    project_colors = [convert_color(c) for c in plt.cm.Paired(np.linspace(0, 1, len(project_data)))]
    # График по проектам
    fig_title = "Расписание по ДСЕ"
    grouping_column = 'Project'

    for idx, p in enumerate(project_data.keys()):
        for j in [j for j, proj in operation_to_project.items() if proj == p]:
            start = time_to_datetime_str(base_time, model.start_time[j].value)
            finish = time_to_datetime_str(base_time, model.start_time[j].value + model.duration[j])

            for k in model.workers:
                if model.assignment[j, k].value > 0.5:
                    task_data = dict(
                            Project=f"ДСЕ {p}",
                            Task=f"ДСЕ {p}: тип операции {jobs_data[j][0]}",
                            Start=start,
                            Finish=finish,
                            Resource=f"Рабочий {k}",
                    )
                        
                    gantt_data.append(task_data)
    df = pd.DataFrame(gantt_data)
    order = [f'ДСЕ {p}' for p in sorted(project_data.keys())]
    return create_gantt_chart(df, grouping_column, fig_title, order, model, show)
 

def create_gantt_chart(df, grouping_column, fig_title, order, model, show):
    df['Start'] = pd.to_datetime(df['Start'])
    df['Finish'] = pd.to_datetime(df['Finish'])

    shift_start_hour = 8
    shift_end_hour = 20

    # Настройка начала первой смены
    first_shift_start = df['Start'].min().replace(hour=8, minute=0, second=0, microsecond=0)
    if df['Start'].min() > first_shift_start:
        first_shift_start += timedelta(days=1)

    # Определение общего количества интервалов
    total_duration = (df['Finish'].max() - df['Start'].min()).total_seconds() / 3600
    number_of_intervals = int(ceil(total_duration / 12))

    tickvals = [first_shift_start]
    ticktext = [first_shift_start.strftime('8ч %d.%m')]  # Первая метка для первой смены
    current_date = first_shift_start + timedelta(hours=12)
    for i in range(1, number_of_intervals):
        end_of_shift = current_date.replace(hour=shift_end_hour)
        start_of_next_shift = (current_date + timedelta(days=1)).replace(hour=shift_start_hour)

        # Добавляем метки для каждой смены кроме первой
        tickvals += [end_of_shift, start_of_next_shift]
        ticktext += ['20ч ' + current_date.strftime('%d.%m') + '<br>8ч ' + (current_date + timedelta(days=1)).strftime('%d.%m')]

        current_date += timedelta(days=1)
        # print(ticktext)
    min_start = min(model.start_time[j].value for j in model.operations)
    max_end = max(model.start_time[j].value + model.duration[j] for j in model.operations)
    num_of_workers = len(model.workers)
    duration_in_minutes = max_end - min_start
    # время последней операции
    base_time = df['Start'].min()  # Время начала первой операции
    last_operation_end_time = df['Finish'].max()  # Время завершения последней операции
    end_time_in_minutes = (last_operation_end_time - base_time).total_seconds() / 60 

    fig = px.timeline(df, x_start="Start", x_end="Finish", y=grouping_column, color="Resource", title=fig_title, category_orders={grouping_column: order}, hover_data=["Task"])
    n = len(tickvals) - len(ticktext)
    if n > 0:
        tickvals = tickvals[:-n]

    # Добавление вертикальной линии для времени завершения последней операции
    fig.add_vline(x=last_operation_end_time, line_width=3, line_dash="dot", line_color="red")

    # Добавление аннотации с численным значением времени завершения
    fig.add_annotation(x=last_operation_end_time, y=-0.5, text=f"{int(end_time_in_minutes)} мин", showarrow=False, bgcolor="red", font=dict(color="white",  size=font_size))

    # Добавляем вертикальные линии и метки для каждой смены
    for val in tickvals:
        fig.add_vline(x=val, line_width=2, line_dash="dash", line_color="black")

    fig.update_xaxes(tickvals=tickvals, ticktext=ticktext, tickangle=-45, tickfont=dict(size=font_size),
        title_font=dict(size=font_size))
    fig.update_yaxes(
        tickfont=dict(size=font_size),
        title_font=dict(size=font_size)
    )

    fig.update_layout(title=fig_title, xaxis_title="Дата и время", yaxis_title="Ресурс", height=num_of_workers * 200, width=duration_in_minutes, showlegend=True,title_font=dict(size=font_size),
        legend_title_font=dict(size=font_size),
        legend_font=dict(size=font_size),
        hoverlabel=dict(font_size=font_size))

    if show:
        fig.show()


def plot_worker_utilization_interactive(model, show=True):

    worker_names = [
        f"Рабочий {k}" 
        for k in model.workers 
        if any(model.assignment[j, k].value > 0.5 for j in model.operations)
    ]
    num_of_workers = len(model.workers)
    total_minutes = {k:sum(model.duration[j] * model.assignment[j, k].value for j in model.operations) for k in model.workers}
    assigned_jobs_counts = [round(sum(model.assignment[j, k].value for j in model.operations)) for k in model.workers if total_minutes[k] > 0]
    max_time = max(model.start_time[j].value + model.duration[j] for j in model.operations)
    print(total_minutes)
    print(max_time)
    utilization_percentage = [(time_spent/max_time)*100 for time_spent in total_minutes.values() if time_spent > 0]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    has_added_work_time_legend = False
    has_added_controller_legend = False
    # print(total_minutes)

    for k, worker_name in enumerate(worker_names):
        is_controller = extract_number(worker_name) in controlers
        # print(extract_number(worker_name))
        # print(is_controller)
        color = 'orange' if is_controller else 'yellow'
        
        if not is_controller and not has_added_work_time_legend:
            show_legend = True
            has_added_work_time_legend = True
        # Проверяем, добавляли ли мы уже легенду для контролера
        elif is_controller and not has_added_controller_legend:
            show_legend = True
            has_added_controller_legend = True
            # print('added controler and orange')
        else:
            show_legend = False
        fig.add_trace(
            go.Bar(
                x=[worker_name],
                y=[total_minutes[int(extract_number(worker_name))]],
                name='Контролеры' if is_controller else 'Общее время работы (мин)',
                text=f"{total_minutes[int(extract_number(worker_name))]} мин<br>{utilization_percentage[k]:.2f}%",
                textposition='auto',
                marker_color=color,
                showlegend=show_legend
            ),
            secondary_y=False
        )

    fig.add_trace(
        go.Scatter(x=worker_names, y=assigned_jobs_counts, name='Количество назначенных операций', mode='lines+markers+text', text=assigned_jobs_counts, textposition='top center', marker=dict(color='green')),
        secondary_y=True
    )

    fig.add_hline(y=max_time, line_width=10, line_dash="dot", line_color="red")

    fig.add_annotation(
        y=max_time,  # Позиция на оси Y, соответствующая значению max_time
        xref="paper",
        x=0,  # Расположение аннотации у левого края области графика
        text=f"{max_time}",  # Текст аннотации
        showarrow=True,
        arrowhead=1,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="red",
        ax=-50,  # Смещение аннотации по оси X (отрицательное значение для смещения влево)
        ay=0,   # Смещение аннотации по оси Y
        bgcolor="white",
        font=dict(size=40, color="red")
    )
    fig.add_trace(
        go.Scatter(x=[None], y=[None], mode='lines', line=dict(color="red", width=10, dash="dot"), name=f'Время исполнения плана')
    )   

    fig.update_layout(title_text="Занятость Рабочих и Назначенные Операции", title_font=dict(size=font_size + 2))

    fig.update_xaxes(tickfont=dict(size=font_size))
    fig.update_yaxes(tickfont=dict(size=font_size), title_font=dict(size=font_size + 2), secondary_y=False)
    fig.update_yaxes(tickfont=dict(size=font_size), title_font=dict(size=font_size + 2), secondary_y=True)

    fig.update_layout(legend_font=dict(size=font_size), hoverlabel=dict(font=dict(size=font_size)))

    # Подписи
    fig.update_traces(textfont=dict(size=font_size))

    fig.update_yaxes(title_text="Общее Время Работы (мин)", secondary_y=False, range=[0, max_time + 50])
    fig.update_yaxes(title_text="Количество Назначенных Операций", secondary_y=True)

    if show:
        fig.show()
    


output_json = []

# Iterate over the workers to populate their details
for worker in model.workers:
    worker_data = {"OBJECT_ID": worker, "NAME": f"Worker {worker}", "ASSIGNMENTS": []}
    # Iterate over the operations to find those assigned to the current worker
    for operation in model.operations:
        if model.assignment[operation, worker].value == 1:  # Check if the operation is assigned to this worker
            start_time = model.start_time[operation].value
            duration = model.duration[operation]
            end_time = start_time + duration
            project_id = operation_to_project[operation]  # Assuming operation_to_project is available and correct
            
            # Construct the task data structure
            task_data = {
                "HOUSE": project_id,
                "END": end_time,
                "START": start_time,
                "TASK": {
                    "NAME": f"Operation {operation}",
                    "DURATION": duration
                }
            }
            
            # Append the task to the worker's assignments
            worker_data["ASSIGNMENTS"].append(task_data)
    
    # Append the worker data to the output list if they have assignments
    if worker_data["ASSIGNMENTS"]:
        output_json.append(worker_data)
with open(f'converted_data_{data_from}', 'w') as json_file:
    json.dump(output_json, json_file, indent=4)
    

# plot_gantt_schedule(model)   
# plot_gantt_schedule_projects(model)
# plot_worker_utilization_interactive(model)