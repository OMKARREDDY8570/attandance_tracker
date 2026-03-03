from flask import Flask, request, render_template_string
import ast
import re
import requests

app = Flask(__name__)

HTML = '''
<h2>Attendance Portal</h2>
<form method="post">
  Roll No: <input type="text" name="roll"><br>
  Password: <input type="password" name="password"><br>
  <input type="submit" value="Get Report">
</form>
<pre>{{ report }}</pre>
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
