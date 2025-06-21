from flask import Flask, render_template, request, redirect, url_for, flash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/csv')
def csv_page():
    return render_template('csv.html')

@app.route('/upload', methods=['POST'])
def upload_csv():
    file = request.files.get('csvfile')
    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        flash('CSV file uploaded successfully!', 'success')
        return redirect(url_for('csv_page'))
    else:
        flash('Please upload a valid .csv file.', 'error')
        return redirect(url_for('csv_page'))

@app.route('/phone_settings')
def phone_settings():
    return render_template('phone_settings.html')

@app.route('/phone_list')
def phone_list():
    return render_template('phone_list.html')

@app.route('/shortlist')
def shortlist():
    return render_template('shortlist.html')

if __name__ == '__main__':
    app.run(debug=True)
