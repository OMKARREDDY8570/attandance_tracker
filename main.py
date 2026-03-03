from flask import Flask, request, render_template_string
import ast
import re
import requests

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MITS Realtime Attendance Tracker</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
body {
    min-height: 100vh;
    background: linear-gradient(135deg, #4e54c8, #8f94fb);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    transition: background 0.5s;
}
.login-card {
    background: #fff;
    border-radius: 20px;
    padding: 40px 50px;
    width: 400px;
    max-width: 90%;
    box-shadow: 0 20px 50px rgba(0,0,0,0.2);
    text-align: center;
    transition: opacity 0.5s;
}
.login-card h1 {
    font-size: 1.8em;
    margin-bottom: 30px;
    color: #4e54c8;
    font-weight: bold;
    letter-spacing: 1px;
}
.login-card input[type="text"], .login-card input[type="password"] {
    width: 100%;
    padding: 15px 20px;
    margin: 10px 0 20px 0;
    border: none;
    border-radius: 10px;
    background: #f0f0f5;
    font-size: 1em;
}
.login-card input:focus {
    outline: none;
    background: #e0e0ff;
    box-shadow: 0 0 5px #4e54c8;
}
.login-card button {
    width: 100%;
    padding: 15px;
    background: linear-gradient(90deg, #4e54c8, #8f94fb);
    color: #fff;
    font-size: 1em;
    font-weight: bold;
    border: none;
    border-radius: 10px;
    cursor: pointer;
}
.login-card button:hover {
    background: linear-gradient(90deg, #8f94fb, #4e54c8);
    box-shadow: 0 5px 20px rgba(0,0,0,0.3);
}
#report-container {
    max-width: 90%;
    padding: 20px;
    background: #ffffff;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    border-radius: 15px;
    overflow-x: auto;
    margin-top: 20px;
}
#desktop-warning {
    text-align: center;
    margin-bottom: 20px;
    font-weight: bold;
    color: #e74c3c;
}
pre {
    font-size: 1.05em;
    white-space: pre-wrap;
    word-wrap: break-word;
    color: #333;
}
</style>
</head>
<body>
<div class="login-card" id="loginCard">
    <h1>MITS REALTIME ATTENDANCE TRACKER</h1>
    <form method="post" onsubmit="hideLogin()">
        <input type="text" name="roll" placeholder="Enter Roll No" required><br>
        <input type="password" name="password" placeholder="Enter Password" required><br>
        <button type="submit">Get Report</button>
    </form>
    <p>Secure & Realtime Data</p>
</div>

<div id="report-container">
    <div id="desktop-warning">⚠️ Best viewed in desktop mode ⚠️</div>
    <pre>{{ report }}</pre>
</div>

<script>
// Only hide login box on submit for better clarity
function hideLogin() {
    var card = document.getElementById('loginCard');
    if(card) {
        card.style.display = 'none';
    }
    document.body.style.background = '#ffffff';
}
</script>
</body>
</html>
'''

def attandance(username,password):
    cleaned_attendance =calculate(username,password)
    return attendance_analysis_emoji(cleaned_attendance)
    

def calculate(username,password):
    session = requests.Session()
    login_url = "http://mitsims.in/studentAppLogin/studentLogin.action"

    login_params = {
        "actionType": "studentAppLogin",
        "personType": "student",
        "userId": username,
        "password": password
    }

    login_response = session.get(login_url, params=login_params)
    print(login_response.text)
    login_data = ast.literal_eval(login_response.text)

    #login_data = login_response.json()


    if login_data["status"] == "success":
        student_id = login_data["studentLoginDetails"][0]["id"]
        token = login_data["studentLoginDetails"][0]["authToken"]
        print("Login Success")
    else:
        print("Login Failed")

    print("✅ Login Successful")
    print("Student ID:", student_id)
    print("Token:",token)
    print("STUDENT_ID:",student_id)


    #get attendance
    attendance_url = "http://mitsims.in/studentApp/getAttendanceDetails.action"

    attendance_params = {
        "tkn": token,
        "stdnt.id": student_id,
        "studentId": student_id,
        "actionType": "attendanceDetails",
        "studentType": "student"
    }

    attendance_response = session.get(attendance_url, params=attendance_params)


    js_text = attendance_response.text

    # Step 1: Extract each subject block using regex
    subject_blocks = re.findall(r'\{(.*?)\}', js_text, re.DOTALL)

    cleaned_attendance = {}

    # Step 2: For each block, extract the required fields
    for block in subject_blocks:
        try:
            subject = re.search(r"subjectName\s*:\s*'([^']+)'", block).group(1).strip()
            attended = int(re.search(r"attended\s*:\s*'([^']+)'", block).group(1).strip())
            total = int(re.search(r"conducted\s*:\s*'([^']+)'", block).group(1).strip())
            percentage = float(re.search(r"percentage\s*:\s*'([^']+)'", block).group(1).strip())
            cleaned_attendance[subject] = {
                'attended': attended,
                'total_classes': total,
                'percentage': percentage
            }
        except AttributeError:
            # skip blocks that don't match (like outer dictionary)
            continue
    return cleaned_attendance


def attendance_analysis_emoji(data, threshold=75):
    """
    Emoji-based Attendance Report & Analysis for chat clients
    """
    report_lines = []
    report_lines.append(f"📊  Attendance Report & Analysis:  📊")
    report_lines.append("=" * 80)
    report_lines.append(f"{'Subject':40} | {'Attended':>7} | {'Total':>5} | {'%':>6} | Progress | Action")
    report_lines.append("-" * 80)

    overall_attended = 0
    overall_total = 0

    for subject, details in data.items():
        attended = details['attended']
        total = details['total_classes']
        percent = details['percentage']

        overall_attended += attended
        overall_total += total

        # Emoji progress bar
        bar_length = 20
        filled_length = int(bar_length * percent / 100)
        empty_length = bar_length - filled_length
        bar = "🟩" * filled_length + "⬜" * empty_length

        # Warning emoji for subjects below threshold
        warning = "⚠️ " if percent < threshold else ""

        # Classes to skip or attend (correct formula)
        if percent >= threshold:
            max_classes = int(attended / (threshold/100) - total)
            action = f"Can skip {max_classes} class(es)" if max_classes > 0 else "No skip"
        else:
            need_classes = int(((threshold/100)*total - attended)/(1 - threshold/100) + 0.9999)
            action = f"Need to attend {need_classes} class(es)"

        report_lines.append(f"{warning}{subject[:40]:40} | {attended:7} | {total:5} | {percent:6.2f} | {bar} | {action}")

    # Overall calculation
    overall_percent = overall_attended / overall_total * 100
    if overall_percent >= threshold:
        max_overall_skip = int(overall_attended / (threshold/100) - overall_total)
        overall_action = f"Overall: Can skip {max_overall_skip} class(es)" if max_overall_skip > 0 else "Overall: No skip"
    else:
        need_overall = int(((threshold/100)*overall_total - overall_attended)/(1 - threshold/100) + 0.9999)
        overall_action = f"Overall: Need to attend {need_overall} class(es)"

    report_lines.append("=" * 80)
    report_lines.append(f"Overall Attendance: {overall_attended} / {overall_total} -> {overall_percent:.2f}%")
    report_lines.append(overall_action)

    return "\n".join(report_lines)


# Usage




# Usage
#print(attendance_report_fancy(cleaned_attendance))

@app.route("/", methods=["GET", "POST"])
def home():
    report = ""
    if request.method == "POST":
        roll = request.form.get("roll")
        password = request.form.get("password")
        report = attandance(roll, password)
    return render_template_string(HTML, report=report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)





