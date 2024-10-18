from flask import Flask, render_template, request, redirect, url_for, flash
# from jssp import build_model, plot_gantt_schedule, plot_gantt_schedule_projects, plot_worker_utilization_interactive, solve_model, generate_output, solution_from_file
from jssp_ortools import create_model, model_solve, plot_gantt_schedule, plot_gantt_schedule_projects, plot_worker_utilization, generate_output
import io
import base64
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'some_secret_key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Проверяем, что файл имеет допустимое расширение
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Функция для обработки загрузки файла
def process_uploaded_file(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Получаем параметры из формы
        alpha = float(request.form.get('param1'))
        beta = float(request.form.get('param2'))
        time_to_solve = int(request.form.get('param3'))
        # param4 = int(request.form.get('param4'))
        # hard_deadline = bool(request.form.get('hard_deadline'))

        # Проверяем, был ли загружен файл
        if 'datafile' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['datafile']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Обрабатываем загруженный файл
            data = process_uploaded_file(file)

            # Разбираем данные из файла
            workers_data = {int(k): v for k, v in data['Machines'].items()}
            jobs_data = {int(k): v for k, v in data['Operations'].items()}
            project_data = {int(k): v for k, v in data['Jobs'].items()}
        
        # Создаем и решаем модель
        model, start_time, assignment, makespan, duration, workers, total_cost = create_model(
            jobs_data, workers_data, project_data, alpha=alpha, beta=beta
        )

        operation_to_project = {}
        for project_id, details in project_data.items():
            for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
                operation_to_project[operation_id] = project_id

        solver, operation_to_worker = model_solve(
            model, start_time, assignment, jobs_data.keys(), workers_data.keys(), duration, total_cost, time_to_solve, operation_to_project
        )

        if solver is None or operation_to_worker is None:
            flash('Could not find an optimal solution.', 'danger')
            return redirect(url_for('index'))

        # Генерируем вывод
        output_data = generate_output(
            solver, start_time, duration, assignment, total_cost, makespan, workers_data, project_data, operation_to_worker, operation_to_project
        ) 

        # Генерируем графики в JSON формате для отображения в шаблоне
        schedule_fig_json = plot_gantt_schedule(solver, start_time, duration, operation_to_worker, operation_to_project, show=False)
        projects_fig_json = plot_gantt_schedule_projects(solver, start_time, duration, operation_to_project, operation_to_worker, show=False)
        worker_util_fig_json = plot_worker_utilization(solver, start_time, duration, workers, operation_to_worker, show=False)

        # plot_worker_utilization(model, show=False)

        return render_template('results.html', projects=output_data['projects'], workers=output_data['workers'], additional_info=output_data['additional_info'], schedule_fig=schedule_fig_json, projects_fig=projects_fig_json, worker_util_fig=worker_util_fig_json)

    return render_template('index.html')

if __name__ == '__main__':
    # Создаем папку для загрузки файлов, если она не существует
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
