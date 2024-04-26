import itertools
import random
import json

random.seed(12345)

# Настройки для генерации данных
num_workers = 48
num_jobs = 500
num_projects = 50
base_salary = 100
salary_increment = 300
base_duration = 5

# Определения работ
job_types = ["Токарно-винторезная", "Слесарная", "Вертикально-сверлильная", "Токарная с ЧПУ"]
worker_types = ["Токарь", "Слесарь", "Сверловщик", "Токарь с ЧПУ"]

print('generate workers_data')
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

max_grades_by_job_type = {job_type: 0 for job_type in job_types}
for worker_id, worker_data in workers_data.items():
    job_type, _, grade, _, _ = worker_data
    if grade > max_grades_by_job_type[job_type]:
        max_grades_by_job_type[job_type] = grade

print('generate jobs_data')
# Генерация данных о работах
jobs_data = {}
for i in range(1, num_jobs + 1):
    job_type = job_types[(i - 1) % len(job_types)]
    duration = random.randint(5, 50)
    max_grade = max_grades_by_job_type[job_type]
    grade = random.randint(1, max_grade)  # Генерация грейда в пределах от 1 до максимального для данного типа работы
    jobs_data[i] = [job_type, duration, [], grade, i]

print('Распределение работ по проектам')
# Распределение работ по проектам
remaining_jobs = list(jobs_data.keys())
random.shuffle(remaining_jobs)

project_data = {}

for project_id in range(1, num_projects + 1):
    project_jobs = []
    prev_job = None
    for _ in range(3):
        if remaining_jobs:
            job_id = remaining_jobs.pop()
            if prev_job is not None:
                jobs_data[job_id][2].append(prev_job)   # Добавление предшественника к задаче
            project_jobs.append(job_id)
            prev_job = job_id  # Обновление предшественника для следующей задачи
    deadline = (project_id - 1) + base_duration * 60
    project_name = f'ring{project_id}'
    project_data[project_id] = (project_jobs, deadline, project_name)

print('Распределение оставшихся задач случайным образом')
print(remaining_jobs)
# Распределение оставшихся задач случайным образом
def can_add_more_jobs():
    return any(len(project_data[project_id][0]) < 11 for project_id in range(1, num_projects + 1))

# Распределение оставшихся задач случайным образом
while remaining_jobs and can_add_more_jobs():
    project_id = random.randint(1, num_projects)
    if len(project_data[project_id][0]) < 11:
        job_id = remaining_jobs.pop()
        last_job_in_project = project_data[project_id][0][-1]
        if last_job_in_project is not None:
            jobs_data[job_id][2].append(last_job_in_project)  # Добавление предшественника
        project_data[project_id][0].append(job_id)


# Вывод сгенерированных данных
# print("Workers Data:", workers_data)
# print("\nJobs Data:", jobs_data)
# print("\nProject Data:", project_data)

print('Вывод сгенерированных данных')
workers_data_str = "\n".join(f"    {k}: {v}," for k, v in workers_data.items())
jobs_data_str = "\n".join(f"    {k}: {v}," for k, v in jobs_data.items())
project_data_str = "\n".join(f"    {k}: {v}," for k, v in project_data.items())

# Формирование итоговой строки
# data_str = f"workers_data = {{\n{workers_data_str}\n}}\n\n" \
#            f"jobs_data = {{\n{jobs_data_str}\n}}\n\n" \
#            f"project_data = {{\n{project_data_str}\n}}"

print('запись в файл')
with open(f'data{num_workers}_{num_projects}_{num_jobs}.json', 'w', encoding='utf-8') as file:
    json.dump({
        'Machines': workers_data,
        'Operations': jobs_data,
        'Jobs': project_data
    }, file, ensure_ascii=False, indent=4)

# # Сохранение данных в текстовом файле
# with open('generated_data.txt', 'w', encoding='utf-8') as file:
#     file.write(data_str)
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
