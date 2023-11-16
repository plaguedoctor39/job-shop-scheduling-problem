import itertools
import random
import json

random.seed(12345)

# Настройки для генерации данных
num_workers = 20  # Вот новый параметр для общего количества рабочих
num_jobs = 50  # Общее количество работ
num_projects = 10  # Количество проектов
base_salary = 50
salary_increment = 5
base_duration = 5
duration_increment = 5

# Определения работ
job_types = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
worker_types = ["Токарь", "Слесарь", "Сверловщик", "Токарь с ЧПУ"]

# Генерация данных о работниках
workers_data = {}
for worker_type in worker_types:
    # Генерируем равномерное распределение разрядов от 1 до 5 для каждого типа рабочего
    grades = itertools.cycle(range(1, 6))
    for _ in range(num_workers // len(worker_types)):
        grade = next(grades)
        salary = base_salary + (grade - 1) * salary_increment
        worker_id = len(workers_data) + 1
        job_type = job_types[worker_types.index(worker_type)]
        workers_data[worker_id] = (job_type, worker_type, grade, salary, None)
# Генерация данных о работах и проектах
jobs_data = {}
project_data = {i: ([], random.randint(base_duration * 60, 480)) for i in range(1, num_projects + 1)}  # здесь изменен способ определения дедлайна



# Распределение работ по проектам
jobs_data = {}
project_data = {i: ([], (i - 1) * 60 + base_duration * 60) for i in range(1, num_projects + 1)}

# Распределение работ по проектам
project_ids = list(project_data.keys())
project_jobs = {k: [] for k in project_ids}

for i in range(1, num_jobs + 1):
    job_id = i * 10 + 5
    
    # Генерация случайной длительности работы от 5 до 50 минут
    duration = random.randint(5, 50)
    
    priority = random.randint(1, 5)
    project_id = project_ids[(i - 1) % len(project_ids)]
    
    # Определение предшественников
    dependencies = project_jobs[project_id][-1:] if project_jobs[project_id] else []
    
    # Добавляем работу в данные о работах и в проект
    project_jobs[project_id].append(job_id)
    jobs_data[job_id] = (job_types[(i - 1) % len(job_types)], duration, dependencies, priority)

# Обновление данных проекта с учетом распределенных работ
for project_id in project_ids:
    project_jobs_list = project_jobs[project_id]
    # Установка дедлайна с учетом максимального ограничения
    deadline = min((project_id - 1) * 60 + base_duration * 60, 480)
    # Формирование имени проекта
    project_name = f'ring{project_id}'
    project_data[project_id] = (project_jobs_list, deadline, project_name)

workers_data_str = "\n".join(f"    {k}: {v}," for k, v in workers_data.items())
jobs_data_str = "\n".join(f"    {k}: {v}," for k, v in jobs_data.items())
project_data_str = "\n".join(f"    {k}: {v}," for k, v in project_data.items())

# Формирование итоговой строки
data_str = f"workers_data = {{\n{workers_data_str}\n}}\n\n" \
           f"jobs_data = {{\n{jobs_data_str}\n}}\n\n" \
           f"project_data = {{\n{project_data_str}\n}}"

# Сохранение данных в текстовом файле
with open('generated_data.txt', 'w', encoding='utf-8') as file:
    file.write(data_str)
# Вывод сгенерированных данных
print("Workers Data:")
for k, v in workers_data.items():
    print(f"{k}: {v}")

print("\nJobs Data:")
for k, v in jobs_data.items():
    print(f"{k}: {v}")

print("\nProject Data:")
for k, v in project_data.items():
    print(f"{k}: {v}")
