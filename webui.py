from flask import Flask, render_template, request, redirect, url_for, flash
from jssp import build_model, solve_model, generate_output, plot_schedule, plot_worker_utilization
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
        param3 = int(request.form.get('param3'))
        hard_deadline = bool(request.form.get('hard_deadline'))
        
        # Создаем и решаем модель
        model = build_model(param1, param2, param3, hard_deadline=hard_deadline)
        model.start_time[120].set_value(60)
        model.start_time[120].fix()  
        result = solve_model(model)
        
        if not result:
            flash('Could not find an optimal solution.', 'danger')
            return redirect(url_for('index'))

        # Генерируем вывод
        output_data = generate_output(model)  

        # Генерируем и сохраняем графики
        plot_schedule(model, show=False)
        plot_worker_utilization(model, show=False)

        return render_template('results.html', projects=output_data['projects'], workers=output_data['workers'], additional_info=output_data['additional_info'])

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
