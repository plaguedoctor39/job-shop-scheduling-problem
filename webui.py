from flask import Flask, render_template, request, redirect, url_for, flash
from jssp import build_model, plot_gantt_schedule, plot_gantt_schedule_projects, plot_worker_utilization_interactive, solve_model, generate_output
import io
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)
app.secret_key = 'some_secret_key'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Получаем параметры из формы
        param1 = int(request.form.get('param1'))
        param2 = int(request.form.get('param2'))
        # param3 = int(request.form.get('param3'))
        # param4 = int(request.form.get('param4'))
        hard_deadline = bool(request.form.get('hard_deadline'))
        
        # Создаем и решаем модель
        model = build_model(param1, param2, hard_deadline=hard_deadline)
        # model.start_time[120].set_value(60)
        # model.start_time[120].fix()  
        model = solution_from_file(model)
        # model.worker_assigned[255, 6].set_value(0)
        # model.worker_assigned[255, 6].fix()
        # # model.start_time[105].set_value(100)
        # # model.start_time[105].fix()
        # model.worker_assigned[255, 10].set_value(1)
        # model.worker_assigned[255, 10].fix()
        result = solve_model(model)
        # result, changes = remove_conflicting_assignments(model)
        # if changes:
        #     result = solve_model(result)
        
        if not result:
            flash('Could not find an optimal solution.', 'danger')
            return redirect(url_for('index'))

        # Генерируем вывод
        output_data = generate_output(model)  

        # Генерируем и сохраняем графики
        # plot_schedule(model, show=False, mode='workers')
        schedule_fig = plot_gantt_schedule(model, show=False)
        projects_fig = plot_gantt_schedule_projects(model, show=False)
        worker_util_fig = plot_worker_utilization_interactive(model, show=False)
        # plot_worker_utilization(model, show=False)

        return render_template('results.html', projects=output_data['projects'], workers=output_data['workers'], additional_info=output_data['additional_info'], schedule_fig=schedule_fig, projects_fig=projects_fig, worker_util_fig=worker_util_fig)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
