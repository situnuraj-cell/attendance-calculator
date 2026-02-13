from flask import Flask, request, render_template, redirect
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


def calculate(total, attended, target_percentage=80):
    if total == 0:
        return None
    
    percentage = (attended / total) * 100
    absent = total - attended
    target_decimal = target_percentage / 100
    
    # Classes needed for target percentage
    if percentage >= target_percentage:
        needed = 0
    else:
        needed = math.ceil((target_decimal * total - attended) / (1 - target_decimal))
        needed = max(0, needed)
    
    # Bunk allowed while maintaining target percentage
    if percentage < target_percentage:
        bunk = 0
    else:
        bunk = math.floor((attended - target_decimal * total) / target_decimal)
        bunk = max(0, bunk)
    
    # Color and CSS class based on target
    if percentage >= target_percentage:
        color, css = '#28a745', 'excellent'
    elif percentage >= target_percentage - 20:
        color, css = '#17a2b8', 'good'
    elif percentage >= target_percentage - 40:
        color, css = '#ffc107', 'warning'
    else:
        color, css = '#dc3545', 'critical'
    
    return {
        'percentage': round(percentage, 1),
        'total': total,
        'attended': attended,
        'absent': absent,
        'target_percentage': target_percentage,
        'target_data': {
            'classes_needed': needed,
            'bunk_allowed': bunk
        },
        'color': color,
        'css_class': css
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    # Load saved data
    saved_data = load_data()
    display_total = saved_data.get('total', '')
    display_attended = saved_data.get('attended', '')
    target_percentage = saved_data.get('target_percentage', 80)
    result = error = share_link = None
    
    if request.method == 'POST':
        action = request.form.get('action', 'calculate')
        
        try:
            form_total = int(request.form.get('total', 0) or 0)
            form_attended = int(request.form.get('attended', 0) or 0)
            form_target = int(request.form.get('target_percentage', 80) or 80)
            
            if form_total < 0 or form_attended < 0:
                error = 'Enter positive numbers'
            elif form_attended > form_total:
                error = 'Attended cannot exceed total'
            else:
                result = calculate(form_total, form_attended, form_target)
                
                # Auto-save to file
                save_data({
                    'total': form_total,
                    'attended': form_attended,
                    'target_percentage': form_target,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Update display values
                display_total = form_total
                display_attended = form_attended
                target_percentage = form_target
                
                if action == 'generate_link':
                    # Generate shareable link
                    encoded = encode_data(form_total, form_attended)
                    share_link = request.host_url + 'check/' + encoded
        except:
            error = 'Enter valid numbers'
    elif display_total and display_attended:
        # Auto-calculate on page load if data exists
        try:
            total_int = int(display_total)
            attended_int = int(display_attended)
            target_int = int(target_percentage) if target_percentage else 80
            if attended_int <= total_int:
                result = calculate(total_int, attended_int, target_int)
        except:
            pass
    
    return render_template('index.html', 
                           total=display_total, 
                           attended=display_attended,
                           target_percentage=target_percentage,
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
    """Clear saved attendance data"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    # Redirect to home page instead of rendering template directly
    return redirect('/')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
