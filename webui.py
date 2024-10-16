from flask import Flask, render_template, request, redirect, url_for, flash
# from jssp import build_model, plot_gantt_schedule, plot_gantt_schedule_projects, plot_worker_utilization_interactive, solve_model, generate_output, solution_from_file
from jssp_ortools import create_model, model_solve, plot_gantt_schedule, plot_gantt_schedule_projects, plot_worker_utilization, generate_output
import io
import base64
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)
app.secret_key = 'some_secret_key'

data_file = 'data30_10_100.json'

# Загрузка данных
with open(data_file, 'r', encoding='utf-8') as file:
    data = json.load(file)
workers_data = {int(k): v for k, v in data['Machines'].items()}
jobs_data = {int(k): v for k, v in data['Operations'].items()}
project_data = {int(k): v for k, v in data['Jobs'].items()}

def get_operation_to_project(project_data):
    operation_to_project = {}
    for project_id, details in project_data.items():
        for operation_id in details[0]:  # details[0] содержит список идентификаторов операций
            operation_to_project[operation_id] = project_id
    return operation_to_project

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Получаем параметры из формы
        alpha = float(request.form.get('param1'))
        beta = float(request.form.get('param2'))
        time_to_solve = int(request.form.get('param3'))
        # param4 = int(request.form.get('param4'))
        # hard_deadline = bool(request.form.get('hard_deadline'))
        
        # Создаем и решаем модель
        model, start_time, assignment, makespan, duration, workers, total_cost = create_model(
            jobs_data, workers_data, project_data, alpha=alpha, beta=beta
        )
        solver, operation_to_worker = model_solve(
            model, start_time, assignment, jobs_data.keys(), workers_data.keys(), duration, total_cost, time_to_solve
        )

        operation_to_project = get_operation_to_project(project_data)
        
        # if not result:
        #     flash('Could not find an optimal solution.', 'danger')
        #     return redirect(url_for('index'))

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
    app.run(debug=True)
