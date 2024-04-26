from flask import Flask, render_template

app = Flask(__name__)

# Словарь с понятными названиями сценариев
scenario_names = {
    '89_original': '89 операций: Исходные данные',
    '89_our1': '89 операций: Сценарий 1',
    '89_our2': '89 операций: Сценарий 2',
    '234_original': '234 операции: Исходные данные',
    '234_our1': '234 операции: Сценарий 1',
    '234_our2': '234 операции: Сценарий 2'
}

@app.route('/')
def index():
    return render_template('demolist.html', scenarios=scenario_names.keys(), names=scenario_names)

@app.route('/scenario/<name>')
def scenario(name):
    images = [f'scenarios/{name}/newplot (51).png', f'scenarios/{name}/newplot (52).png', f'scenarios/{name}/newplot (53).png']
    return render_template('scenario.html', scenario_name=scenario_names[name], images=images)

if __name__ == '__main__':
    app.run(debug=True)
