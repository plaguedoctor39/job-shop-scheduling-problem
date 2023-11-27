import itertools
import random
import json

random.seed(12345)

# Настройки для генерации данных
num_workers = 40
num_jobs = 200
base_salary = 100
salary_increment = 300
base_duration = 5

# Определения работ
job_types = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
worker_types = ["Токарь", "Слесарь", "Сверловщик", "Токарь с ЧПУ"]

# Генерация данных о работниках
workers_data = {}
for worker_type in worker_types:
    grades = itertools.cycle(range(1, 6))
    for _ in range(num_workers // len(worker_types)):
        grade = next(grades)
        salary = base_salary + (grade - 1) * salary_increment
        worker_id = len(workers_data) + 1
        job_type = job_types[worker_types.index(worker_type)]
        workers_data[worker_id] = (job_type, worker_type, grade, salary, None)

# Генерация данных о работах
jobs_data = {}
for i in range(1, num_jobs + 1):
    duration = random.randint(5, 50)
    priority = random.randint(1, 5)
    jobs_data[i] = [job_types[(i - 1) % len(job_types)], duration, [], priority]

# Распределение работ по проектам
remaining_jobs = list(jobs_data.keys())
random.shuffle(remaining_jobs)

project_data = {}
project_id = 1
while remaining_jobs:
    num_jobs_available = len(remaining_jobs)
    num_jobs_in_project = random.randint(3, 10) if num_jobs_available >= 3 else num_jobs_available
    project_jobs = []

    for _ in range(num_jobs_in_project):
        # Проверка на наличие задач в списке
        if remaining_jobs:
            job_id = remaining_jobs.pop()
            if project_jobs:
                # Установка предшественника - последней задачи в списке проекта
                jobs_data[job_id][2] = [project_jobs[-1]]
            project_jobs.append(job_id)

    deadline = (project_id - 1) + base_duration * 60 # не настроено
    project_name = f'ring{project_id}'
    project_data[project_id] = (project_jobs, deadline, project_name)
    project_id += 1

# Вывод сгенерированных данных
# print("Workers Data:", workers_data)
# print("\nJobs Data:", jobs_data)
# print("\nProject Data:", project_data)


workers_data_str = "\n".join(f"    {k}: {v}," for k, v in workers_data.items())
jobs_data_str = "\n".join(f"    {k}: {v}," for k, v in jobs_data.items())
project_data_str = "\n".join(f"    {k}: {v}," for k, v in project_data.items())

# Формирование итоговой строки
data_str = f"workers_data = {{\n{workers_data_str}\n}}\n\n" \
           f"jobs_data = {{\n{jobs_data_str}\n}}\n\n" \
           f"project_data = {{\n{project_data_str}\n}}"

with open('data.json', 'w', encoding='utf-8') as file:
    json.dump({
        "workers_data": workers_data,
        "jobs_data": jobs_data,
        "project_data": project_data
    }, file, ensure_ascii=False, indent=4)

# Сохранение данных в текстовом файле
with open('generated_data.txt', 'w', encoding='utf-8') as file:
    file.write(data_str)
# Вывод сгенерированных данных
# print("Workers Data:")
# for k, v in workers_data.items():
#     print(f"{k}: {v}")

# print("\nJobs Data:")
# for k, v in jobs_data.items():
#     print(f"{k}: {v}")

# print("\nProject Data:")
# for k, v in project_data.items():
#     print(f"{k}: {v}")
