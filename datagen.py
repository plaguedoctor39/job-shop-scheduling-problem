import itertools
import random

random.seed(12345)

# Настройки для генерации данных
num_workers = 20  # Вот новый параметр для общего количества рабочих
num_jobs = 100  # Общее количество работ
num_projects = 20  # Количество проектов
base_salary = 50
salary_increment = 5
base_duration = 5
duration_increment = 5

# Определения работ
job_types = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
worker_types = ["Токарь", "Слесарь", "Сверловщик", "Токарь с ЧПУ"]

# Генерация данных о работниках
workers_data = {}
max_grade_per_type = num_workers // len(worker_types)
grade_counter = {worker_type: 1 for worker_type in worker_types}

for worker_id in range(1, num_workers + 1):
    worker_type_index = (worker_id - 1) % len(worker_types)
    worker_type = worker_types[worker_type_index]
    job_type = job_types[worker_type_index]
    
    # Проверяем, какой разряд должен быть у рабочего
    grade = grade_counter[worker_type]
    salary = base_salary + (grade - 1) * salary_increment
    
    workers_data[worker_id] = (job_type, worker_type, grade, salary, None)
    
    # Обновляем счетчик разряда для следующего рабочего того же типа
    grade_counter[worker_type] += 1
    if grade_counter[worker_type] > max_grade_per_type:
        grade_counter[worker_type] = 1 
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
    project_data[project_id][0].extend(project_jobs[project_id])

# Обновляем дедлайны проектов до максимального значения, если требуется
for project_id in project_data:
    if project_data[project_id][1] > 480:
        project_data[project_id] = (project_data[project_id][0], 480)
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
