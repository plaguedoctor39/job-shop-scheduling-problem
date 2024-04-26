import time
import pulp as op
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json


solver_list = op.listSolvers(onlyAvailable=True)
print(solver_list)

with open('data_from_df2023-12-14.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

workers_data = {int(k): v for k, v in data['Machines'].items()}
jobs_data = {int(k): v for k, v in data['Operations'].items()}
project_data = {int(k): v for k, v in data['Jobs'].items()}

# Функция для классификации по типам
def classify_by_type(names):
    types_count = defaultdict(int)
    for name in names:
        match = re.match(r"(\w+)_.*", name)
        if match:
            type_name = match.group(1)  # Берем первую часть имени как тип
            types_count[type_name] += 1
        else:
            types_count["unknown"] += 1
    return dict(types_count)

start = time.time()
var1, prob = op.LpProblem.fromMPS("simplified_model.mps")

allConstraintsQ = len(prob.constraints)

print(f"constraints quantity = {allConstraintsQ}")
print(f"variables quantity =  {len(prob.variables())}")
# solver = op.HiGHS(msg=False)
# solver = op.PULP_CBC_CMD(msg=False)
solver = op.apis.SCIP_CMD(msg=False)
# solver = op.getSolver('HiGHS_CMD')
status = prob.solve(solver)
print("Status --- \n", op.LpStatus[status])            
if op.LpStatus[status] =='Optimal':
    print("Objective --- \n" , " = ", op.value(prob.objective))

num_binary_vars = sum(1 for var in prob.variables() if var.lowBound == 0 and var.upBound == 1)
num_integer_vars = sum(1 for var in prob.variables() if (var.cat == op.LpInteger or (isinstance(var.lowBound, (int, float)) and isinstance(var.upBound, (int, float)) and var.lowBound % 1 == 0 and var.upBound % 1 == 0)) and not (var.lowBound == 0 and var.upBound == 1))

print(f"Количество целочисленных переменных в модели (исключая бинарные): {num_integer_vars}")
print(f"Количество булевых переменных в модели: {num_binary_vars}")

# Классификация переменных
variable_names = [var.name for var in prob.variables()]
variable_types_count = classify_by_type(variable_names)

# Классификация ограничений
constraint_names = list(prob.constraints.keys())
constraint_types_count = classify_by_type(constraint_names)

# Вывод результатов
print("Количество переменных по типам:")
for var_type, count in variable_types_count.items():
    print(f" {var_type}: {count}")

print("\nКоличество ограничений по типам:")
for const_type, count in constraint_types_count.items():
    print(f" {const_type}: {count}")


# Вывод значений переменных start_time end_time
print("\nЗначения переменных start_time и end_time:")
start_times = {}
end_times = {}
# Преобразование данных о проектах для обратного отображения от операций к проектам
operation_to_project = {}
for project_id, details in project_data.items():
    for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
        operation_to_project[operation_id] = project_id  # Связываем операцию с проектом

# Структура для хранения времен начала и окончания задач
task_times = {}

# Структура для хранения информации о назначении работников
task_workers = {}

# Обход переменных модели для извлечения данных
for var in prob.variables():
    if "start_time" in var.name:
        operation_id = int(re.match(r"start_time\((\d+)\)", var.name).group(1))
        start_time = var.varValue
        task_times[operation_id] = task_times.get(operation_id, {})
        task_times[operation_id]['start'] = start_time
        task_times[operation_id]['end'] = start_time + jobs_data[operation_id][1]
    elif var.name.startswith("end_time"):
        operation_id = int(re.match(r"end_time\((\d+)\)", var.name).group(1))
        end_time = var.varValue
        task_times[operation_id] = task_times.get(operation_id, {})
        task_times[operation_id]['end'] = end_time
    elif "assignment" in var.name:
        # print(f"Processing variable: {var.name} with value {var.varValue}")
        if var.varValue > 0:
            match = re.match(r"assignment\((\d+)_(\d+)\)", var.name)
            if match:
                operation_id, worker_id = int(match.group(1)), int(match.group(2))
                task_workers[operation_id] = worker_id
                # print(f"Assigned worker {worker_id} to operation {operation_id}")
        #     else:
        #         # print(f"No match found for {var.name}")
        # else:
        #     # print(f"Variable {var.name} is below the threshold")
    # print(var.name)
# Подготовка данных для графика Ганта
gantt_data = []
# print(task_workers)
# print(project_data[1227737])
for operation_id, times in task_times.items():
    if operation_id in operation_to_project:
        project_id = operation_to_project[operation_id]
        project_name = project_data[project_id][2]  # Используем строковый ключ для доступа к данным проекта
        worker_id = task_workers.get(operation_id, "Неизвестный")
        gantt_data.append({
            "Task": f"Операция {operation_id}",
            "Start": times['start'],
            "Finish": times['end'],
            "Worker": f"Работник {worker_id}",
            "Resource": project_name,
            "Color": "blue"  # Цвет можно адаптировать в соответствии с проектом или другими критериями
        })
        
# Вывод информации по каждой операции в файл
output_lines = ["Информация по операциям:\n"]
for operation_id, times in task_times.items():
    project_name = "Неизвестный проект"
    if operation_id in operation_to_project:
        project_id = operation_to_project[operation_id]
        project_name = project_data[project_id][2]  # Получение названия проекта
    worker_id = task_workers.get(operation_id, "Неизвестный")
    line = (f"Операция {operation_id}: Начало - {times['start']}, Конец - {times['end']}, "
            f"Работник - {worker_id}, Проект - {project_name}\n")
    output_lines.append(line)

# Путь к файлу для записи
output_file_path = 'operations_info.txt'
with open(output_file_path, 'w', encoding='utf-8') as file:
    file.writelines(output_lines)

print(f"Информация по операциям была записана в файл: {output_file_path}")



# Создание графика Ганта
def plot_gantt_chart(data, title='График Ганта'):
    fig, ax = plt.subplots(figsize=(10, 6))

    # Генерация уникальных цветов для каждого проекта
    unique_projects = set(task['Resource'] for task in data)
    colors = plt.cm.jet(np.linspace(0, 1, len(unique_projects)))
    project_to_color = {project: color for project, color in zip(unique_projects, colors)}

    # Размещение задач на графике с уникальными цветами для каждого проекта
    for task in data:
        start = task['Start']
        finish = task['Finish']
        worker = task['Worker']
        resource = task['Resource']
        color = project_to_color[resource]
        ax.barh(worker, finish - start, left=start, color=color, edgecolor='black', label=resource)

    # Установка легенды без дубликатов
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    # Настройка осей
    ax.set_xlabel('Время')
    ax.set_ylabel('Исполнитель')
    ax.set_title(title)
    plt.tight_layout()
    plt.show()

plot_gantt_chart(gantt_data)


# for var in prob.variables():
#     if var.name.startswith("end_time"):
#         identifier = int(re.match(r"end_time\((\d+)\)", var.name).group(1))
#         end_times[identifier] = var.value()

# # Вывод информации по каждой операции
# print("\nИнформация по операциям:")
# for operation_id, times in task_times.items():
#     project_name = "Неизвестный проект"
#     if operation_id in operation_to_project:
#         project_id = operation_to_project[operation_id]
#         project_name = project_data[project_id][2]  # Получение названия проекта
#     worker_id = task_workers.get(operation_id, "Неизвестный")
#     print(f"Операция {operation_id}: Начало - {times['start']}, Конец - {times['end']}, "
#           f"Работник - {worker_id}, Проект - {project_name}")



# Загрузка данных из CSV
# model_results_df = pd.read_csv('model_results.csv')

# Сравнение значений
# print("Сравнение времени начала и окончания задач:")
# for identifier in start_times.keys():
#     # Получение соответствующих значений из Pyomo
#     pyomo_start_time = model_results_df.loc[model_results_df['Task'] == f'Задача {identifier}', 'Start_Time_Pyomo'].values[0]
#     pyomo_end_time = model_results_df.loc[model_results_df['Task'] == f'Задача {identifier}', 'End_Time_Pyomo'].values[0]

#     # Получение значений из PuLP
#     pulp_start_time = start_times[identifier]
#     pulp_end_time = end_times[identifier]

#     # Вывод результатов
#     print(f"\nЗадача {identifier}:")
#     print(f" Start Time - Pyomo: {pyomo_start_time}, PuLP: {pulp_start_time}")
#     print(f" End Time - Pyomo: {pyomo_end_time}, PuLP: {pulp_end_time}")

#     # Вычисление разницы
#     start_time_diff = abs(pyomo_start_time - pulp_start_time)
#     end_time_diff = abs(pyomo_end_time - pulp_end_time)
#     print(f" Разница во времени начала: {start_time_diff}")
#     print(f" Разница во времени окончания: {end_time_diff}")



end = time.time()
print(f"Elapsed time: {end - start}")
