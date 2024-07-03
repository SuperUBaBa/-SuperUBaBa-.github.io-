import json
import pyodbc
import requests
from flask import Flask, jsonify, render_template
from datetime import datetime
#期末報告影片連結 = https://fjuedu.sharepoint.com/:v:/s/msteams_9250f8/ERBGVCUmAExGiiAYy4UxkbkBo3H0bdopl0IH2Cx4-5oXMg?e=c0xdcn&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJTdHJlYW1XZWJBcHAiLCJyZWZlcnJhbFZpZXciOiJTaGFyZURpYWxvZy1MaW5rIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXcifX0%3D
# 定義 JSON 文件 URL
JSON_FILE_URL = 'https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Forecast/F-A0012-001.json'

def fetch_weather_data(url):
    try:
        response = requests.get(url)
        data = response.json()
        weather_data = []

        if 'cwaopendata' not in data or 'dataset' not in data['cwaopendata']:
            print("No 'cwaopendata' or 'dataset' key in JSON data")
            return []

        locations = data['cwaopendata']['dataset']['location']

        for location in locations:
            location_name = location['locationName']
            elements = location['weatherElement']
            for element in elements:
                element_name = element['elementName']
                for time_data in element['time']:
                    start_time_str = time_data['startTime']
                    end_time_str = time_data['endTime']
                    parameter_name_str = time_data['parameter']['parameterName']
                    parameter_value_str = time_data['parameter'].get('parameterValue', '0')
                    parameter_unit = time_data['parameter'].get('parameterUnit', '')

                    start_time = datetime.strptime(start_time_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                    end_time = datetime.strptime(end_time_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')

                    try:
                        parameter_value = float(parameter_value_str)
                    except ValueError:
                        print(f"Invalid parameter_value value: {parameter_value_str}, setting to 0.0")
                        parameter_value = 0.0

                    if element_name == 'Wx':
                        weather_data.append((location_name, start_time, end_time, element_name, parameter_name_str, ''))
                    else:
                        weather_data.append((location_name, start_time, end_time, element_name, parameter_value, parameter_unit))

        return weather_data
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return []

def get_db_connection():
    try:
        conn = pyodbc.connect('Driver={ODBC Driver 17 for SQL Server};'
                    'Server=LAPTOP-QV5BBV9V\SQLEXPRESS;'
                    'Database=comebuy;'
                    'Trusted_Connection=yes;')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_table():
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()

    cursor.execute('''
    IF OBJECT_ID('WeatherForecast', 'U') IS NOT NULL
        DROP TABLE WeatherForecast
    ''')

    cursor.execute('''
    CREATE TABLE WeatherForecast (
        id INT PRIMARY KEY IDENTITY(1,1),
        location_name NVARCHAR(50),
        start_time DATETIME,
        end_time DATETIME,
        element_name NVARCHAR(10),
        parameter_name NVARCHAR(50),
        parameter_unit NVARCHAR(10)
    )
    ''')

    conn.commit()
    conn.close()

def insert_weather_data(weather_data):
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()

    for data in weather_data:
        try:
            cursor.execute('''
            INSERT INTO WeatherForecast (location_name, start_time, end_time, element_name, parameter_name, parameter_unit)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', data)
        except Exception as e:
            print(f"Error inserting weather data: {e}, Data: {data}")

    conn.commit()
    conn.close()

weather_data = fetch_weather_data(JSON_FILE_URL)
create_table()
insert_weather_data(weather_data)

app = Flask(__name__)

def get_weather_data():
    try:
        conn = get_db_connection()
        if conn is None:
            return []

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM WeatherForecast')
        rows = cursor.fetchall()
        weather_data = []
        for row in rows:
            weather_data.append({
                'location_name': row[1],
                'start_time': row[2].strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': row[3].strftime('%Y-%m-%d %H:%M:%S'),
                'element_name': row[4],
                'parameter_name': row[5],
                'parameter_unit': row[6]
            })
        conn.close()
        return weather_data
    except Exception as e:
        print(f"Error retrieving weather data: {e}")
        return []

@app.route('/weather')
def weather():
    data = get_weather_data()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=False)
