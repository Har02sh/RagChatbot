from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import json
from werkzeug.utils import secure_filename
import numpy as np
import google.generativeai as genai

# --- Configure Gemini API ---
genai.configure(api_key='YOUR_GEMINI_API_KEY')  # Replace with your actual Gemini API key

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}

dataframe = None
data_summary = None

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global dataframe, data_summary

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            data = process_excel(filepath)
            dataframe = pd.read_excel(file)
            preview = dataframe.head().to_string()

            prompt = f"""
            You are a data analyst. Summarize the following data and be ready to answer questions about it.
            Data Preview:
            {preview}
            """

            model = genai.GenerativeModel('gemini-pro')
            chat = model.start_chat()
            gemini_response = chat.send_message(prompt)

            data_summary = gemini_response.text

            return jsonify({"data": data, "summary": data_summary})
        except Exception as e:
            return jsonify({'error': str(e)})

    return jsonify({'error': 'File type not allowed'})

def process_excel(filepath):
    xls = pd.ExcelFile(filepath)
    result = {}

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        sheet_data = {
            'columns': df.columns.tolist(),
            'numeric_columns': df.select_dtypes(include=['number']).columns.tolist(),
            'categorical_columns': df.select_dtypes(include=['object']).columns.tolist(),
            'datetime_columns': df.select_dtypes(include=['datetime']).columns.tolist(),
            'row_count': len(df),
            'summary': {}
        }

        for col in sheet_data['numeric_columns']:
            if len(df) > 0:
                sheet_data['summary'][col] = {
                    'min': float(df[col].min()) if not pd.isna(df[col].min()) else 0,
                    'max': float(df[col].max()) if not pd.isna(df[col].max()) else 0,
                    'mean': float(df[col].mean()) if not pd.isna(df[col].mean()) else 0,
                    'median': float(df[col].median()) if not pd.isna(df[col].median()) else 0,
                    'data': df[col].tolist()
                }
                try:
                    hist_values, hist_bins = np.histogram(df[col].dropna(), bins=10)
                    sheet_data['summary'][col]['histogram'] = {
                        'values': hist_values.tolist(),
                        'bins': hist_bins.tolist()
                    }
                except:
                    sheet_data['summary'][col]['histogram'] = {
                        'values': [],
                        'bins': []
                    }

        for col in sheet_data['categorical_columns']:
            if len(df) > 0:
                value_counts = df[col].value_counts().nlargest(10).to_dict()
                sheet_data['summary'][col] = {
                    'categories': list(value_counts.keys()),
                    'counts': list(value_counts.values())
                }

        for col in sheet_data['datetime_columns']:
            if len(df) > 0:
                try:
                    sheet_data['summary'][col] = {
                        'dates': df[col].dt.strftime('%Y-%m-%d').tolist(),
                        'min_date': df[col].min().strftime('%Y-%m-%d'),
                        'max_date': df[col].max().strftime('%Y-%m-%d')
                    }
                except:
                    sheet_data['summary'][col] = {
                        'dates': [],
                        'min_date': '',
                        'max_date': ''
                    }

        if len(df) > 0:
            paired_data = []
            for i, row in df.iterrows():
                row_data = {}
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        row_data[col] = float(row[col]) if not pd.isna(row[col]) else 0
                    elif pd.api.types.is_datetime64_dtype(df[col]):
                        row_data[col] = row[col].strftime('%Y-%m-%d') if not pd.isna(row[col]) else ''
                    else:
                        row_data[col] = str(row[col]) if not pd.isna(row[col]) else ''
                paired_data.append(row_data)

            sheet_data['paired_data'] = paired_data
            sheet_data['suggestions'] = generate_visualization_suggestions(df, sheet_data)

        result[sheet_name] = sheet_data

    return result

def generate_visualization_suggestions(df, sheet_data):
    suggestions = []

    for col in sheet_data['numeric_columns']:
        suggestions.append({
            'type': 'bar',
            'title': f'Bar Chart: {col}',
            'description': f'Displays the distribution of values for {col}',
            'column': col,
            'icon': 'bar-chart'
        })
        suggestions.append({
            'type': 'line',
            'title': f'Line Chart: {col}',
            'description': f'Shows trends in {col} values',
            'column': col,
            'icon': 'line-chart'
        })
        suggestions.append({
            'type': 'histogram',
            'title': f'Histogram: {col}',
            'description': f'Shows the distribution of {col} values in bins',
            'column': col,
            'icon': 'histogram'
        })

    for col in sheet_data['categorical_columns']:
        if len(df[col].unique()) <= 15:
            suggestions.append({
                'type': 'pie',
                'title': f'Pie Chart: {col}',
                'description': f'Shows the proportion of each category in {col}',
                'column': col,
                'icon': 'pie-chart'
            })

    if len(sheet_data['numeric_columns']) >= 2:
        for i, col1 in enumerate(sheet_data['numeric_columns']):
            for col2 in sheet_data['numeric_columns'][i + 1:]:
                suggestions.append({
                    'type': 'scatter',
                    'title': f'Scatter Plot: {col1} vs {col2}',
                    'description': f'Explores relationship between {col1} and {col2}',
                    'x_column': col1,
                    'y_column': col2,
                    'icon': 'scatter-plot'
                })

    for date_col in sheet_data['datetime_columns']:
        for value_col in sheet_data['numeric_columns']:
            suggestions.append({
                'type': 'timeseries',
                'title': f'Time Series: {value_col} over {date_col}',
                'description': f'Tracks changes in {value_col} over time',
                'date_column': date_col,
                'value_column': value_col,
                'icon': 'time-series'
            })

    if sheet_data['categorical_columns'] and sheet_data['numeric_columns']:
        for cat_col in sheet_data['categorical_columns']:
            if len(df[cat_col].unique()) <= 10:
                for num_col in sheet_data['numeric_columns']:
                    suggestions.append({
                        'type': 'boxplot',
                        'title': f'Box Plot: {num_col} by {cat_col}',
                        'description': f'Compare {num_col} distribution across {cat_col} categories',
                        'value_column': num_col,
                        'group_column': cat_col,
                        'icon': 'box-plot'
                    })

    return suggestions

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided', 'response': 'Please enter a question first.'}), 400

    try:
        system_prompt = (
            "You are a helpful and knowledgeable data scientist with expertise in data analysis, statistics, "
            "and artificial intelligence. You answer questions clearly, concisely, and in an easy-to-understand way. "
            "Do not include any code in your responses. Focus on explaining concepts, methods, and best practices."
        )

        model = genai.GenerativeModel('gemini-pro')
        chat = model.start_chat()
        gemini_response = chat.send_message(f"{system_prompt}\n\nUser: {user_message}")

        return jsonify({'response': gemini_response.text})

    except Exception as e:
        return jsonify({'error': str(e), 'response': 'Sorry, something went wrong! Please try again later.'}), 500

if __name__ == '__main__':
    app.run(debug=True)