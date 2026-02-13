from flask import Flask, request, render_template
import math
import json
import base64
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = 'attendance_data.json'


def load_data():
    """Load saved attendance data from file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_data(data):
    """Save attendance data to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def encode_data(total, attended):
    """Encode attendance data to base64 for URL sharing"""
    data = {'t': total, 'a': attended}
    json_str = json.dumps(data)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return encoded


def decode_data(encoded_str):
    """Decode attendance data from base64 URL"""
    try:
        decoded = base64.urlsafe_b64decode(encoded_str.encode()).decode()
        data = json.loads(decoded)
        return data.get('t', 0), data.get('a', 0)
    except:
        return 0, 0


def calculate(total, attended):
    if total == 0:
        return None
    
    percentage = (attended / total) * 100
    absent = total - attended
    
    if percentage >= 80:
        needed = 0
    else:
        needed = math.ceil((0.8 * total - attended) / 0.2)
        needed = max(0, needed)
    
    if percentage < 80:
        bunk = 0
    else:
        bunk = math.floor((attended - 0.8 * total) / 0.8)
        bunk = max(0, bunk)
    
    if percentage >= 80:
        color, css = '#28a745', 'excellent'
    elif percentage >= 60:
        color, css = '#17a2b8', 'good'
    elif percentage >= 40:
        color, css = '#ffc107', 'warning'
    else:
        color, css = '#dc3545', 'critical'
    
    return {
        'percentage': round(percentage, 1),
        'total': total,
        'attended': attended,
        'absent': absent,
        'classes_needed': needed,
        'bunk_allowed': bunk,
        'color': color,
        'css_class': css
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    saved_data = load_data()
    total = saved_data.get('total', '')
    attended = saved_data.get('attended', '')
    result = error = share_link = None
    
    if request.method == 'POST':
        action = request.form.get('action', 'calculate')
        
        try:
            total = int(request.form.get('total', 0) or 0)
            attended = int(request.form.get('attended', 0) or 0)
            
            if total < 0 or attended < 0:
                error = 'Enter positive numbers'
            elif attended > total:
                error = 'Attended cannot exceed total'
            else:
                result = calculate(total, attended)
                
                save_data({
                    'total': total,
                    'attended': attended,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                if action == 'generate_link':
                    encoded = encode_data(total, attended)
                    share_link = request.host_url + 'check/' + encoded
        except:
            error = 'Enter valid numbers'
    elif total and attended:
        try:
            total = int(total)
            attended = int(attended)
            if attended <= total:
                result = calculate(total, attended)
        except:
            pass
    
    return render_template('index.html', 
                           total=total, 
                           attended=attended, 
                           result=result, 
                           error=error,
                           share_link=share_link,
                           last_updated=saved_data.get('last_updated', ''))


@app.route('/check/<encoded>')
def check_attendance(encoded):
    total, attended = decode_data(encoded)
    
    if total == 0:
        return render_template('check.html', error='Invalid link')
    
    result = calculate(total, attended)
    
    return render_template('check.html', 
                           result=result,
                           total=total,
                           attended=attended)


@app.route('/clear', methods=['POST'])
def clear_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return render_template('index.html', total='', attended='', result=None, error=None, share_link=None, last_updated='')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
