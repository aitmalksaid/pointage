from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import re

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
REPORT_FOLDER = 'reports'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORT_FOLDER'] = REPORT_FOLDER
app.config['SECRET_KEY'] = 'votre-cle-secrete-super-secrete-2024'  # Change this in production

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "Aucun fichier sélectionné", 400

    file = request.files['file']
    if file.filename == '':
        return "Nom de fichier vide", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
    except Exception as e:
        return f"Erreur lors de la sauvegarde du fichier : {e}", 500

    # Determine file format and engine
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Correct engine selection
    if file_extension == '.xlsx':
        engine = 'openpyxl'
    elif file_extension == '.xls':
        engine = 'xlrd'  # Fixed: was 'pyxlsb'
    else:
        return "Format de fichier non supporté. Utilisez .xls ou .xlsx", 400

    # Process the file and parse data
    try:
        employees = parse_attendance_data(filepath, engine)
        
        # Calculate statistics for each employee
        employees_with_stats = []
        for emp in employees:
            stats = calculate_statistics(emp)
            emp_data = {
                'person_id': emp['person_id'],
                'name': emp['name'],
                'department': emp['department'],
                'position': emp['position'],
                'joining_date': emp['joining_date'],
                'stats': stats,
                'dates': emp['dates'][:10] if len(emp['dates']) > 10 else emp['dates'],  # Limit for display
                'check_ins': emp['check_ins'][:10] if len(emp['check_ins']) > 10 else emp['check_ins'],
                'check_outs': emp['check_outs'][:10] if len(emp['check_outs']) > 10 else emp['check_outs'],
                'statuses': emp['statuses'][:10] if len(emp['statuses']) > 10 else emp['statuses'],
            }
            employees_with_stats.append(emp_data)
        
        # Store in session
        session['employees_data'] = employees
        session['filepath'] = filepath
        session['engine'] = engine
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Erreur lors du traitement du fichier : {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    """Display the dashboard with data visualization"""
    if 'employees_data' not in session:
        return redirect(url_for('index'))
    
    employees = session.get('employees_data', [])
    
    # Calculate statistics for display
    employees_with_stats = []
    for emp in employees:
        stats = calculate_statistics(emp)
        emp_data = {
            'person_id': emp['person_id'],
            'name': emp['name'],
            'department': emp['department'],
            'position': emp['position'],
            'joining_date': emp['joining_date'],
            'stats': stats
        }
        employees_with_stats.append(emp_data)
    
    # Calculate global statistics
    total_employees = len(employees)
    total_hours_all = sum([calculate_statistics(emp)['total_hours'] for emp in employees])
    total_days_worked = sum([calculate_statistics(emp)['total_days_worked'] for emp in employees])
    total_days_absent = sum([calculate_statistics(emp)['total_days_absent'] for emp in employees])
    
    global_stats = {
        'total_employees': total_employees,
        'total_hours': round(total_hours_all, 2),
        'avg_hours_per_employee': round(total_hours_all / total_employees, 2) if total_employees > 0 else 0,
        'total_days_worked': total_days_worked,
        'total_days_absent': total_days_absent,
        'attendance_rate': round((total_days_worked / (total_days_worked + total_days_absent) * 100), 2) if (total_days_worked + total_days_absent) > 0 else 0
    }
    
    return render_template('dashboard.html', employees=employees_with_stats, global_stats=global_stats)

@app.route('/api/data')
def get_data():
    """Return employee data as JSON for charts"""
    if 'employees_data' not in session:
        return jsonify({'error': 'No data available'}), 404
    
    employees = session.get('employees_data', [])
    
    # Prepare data for charts
    chart_data = {
        'employees': [],
        'hours': [],
        'departments': {},
        'status_summary': {
            'worked': 0,
            'absent': 0,
            'weekend': 0
        }
    }
    
    for emp in employees:
        stats = calculate_statistics(emp)
        chart_data['employees'].append(emp['name'])
        chart_data['hours'].append(stats['total_hours'])
        
        # Group by department
        dept = emp['department']
        if dept not in chart_data['departments']:
            chart_data['departments'][dept] = {
                'total_hours': 0,
                'employee_count': 0
            }
        chart_data['departments'][dept]['total_hours'] += stats['total_hours']
        chart_data['departments'][dept]['employee_count'] += 1
        
        # Status summary
        chart_data['status_summary']['worked'] += stats['total_days_worked']
        chart_data['status_summary']['absent'] += stats['total_days_absent']
        chart_data['status_summary']['weekend'] += stats['total_weekends']
    
    return jsonify(chart_data)

@app.route('/generate-pdf')
def generate_pdf():
    """Generate and download PDF report"""
    if 'employees_data' not in session or 'filepath' not in session:
        return redirect(url_for('index'))
    
    try:
        filepath = session.get('filepath')
        engine = session.get('engine')
        
        pdf_path = process_and_generate_pdf(filepath, engine)
        return send_file(pdf_path, as_attachment=True, download_name=f"rapport_assiduité_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    except Exception as e:
        return f"Erreur lors de la génération du PDF : {str(e)}", 500


def parse_attendance_data(filepath, engine):
    """Parse the attendance Excel file and extract employee data"""
    
    # Read the entire file without headers
    df = pd.read_excel(filepath, engine=engine, header=None)
    
    employees = []
    current_employee = None
    
    for idx, row in df.iterrows():
        # Check if this row contains "Person ID"
        if pd.notna(row[0]) and str(row[0]).strip() == "Person ID":
            # If we have a previous employee, save it
            if current_employee is not None:
                employees.append(current_employee)
            
            # Start a new employee
            current_employee = {
                'person_id': row[1] if pd.notna(row[1]) else 'N/A',
                'name': 'N/A',
                'department': 'N/A',
                'joining_date': 'N/A',
                'position': 'N/A',
                'dates': [],
                'check_ins': [],
                'check_outs': [],
                'attended_minutes': [],
                'statuses': [],
                'summary': ''
            }
            
            # Extract employee name, department, etc. from the same row
            for i in range(len(row)):
                if pd.notna(row[i]):
                    if str(row[i]).strip() == "Employee Name" and i+3 < len(row):
                        current_employee['name'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Department" and i+3 < len(row):
                        current_employee['department'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Joining Date" and i+3 < len(row):
                        current_employee['joining_date'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Position" and i+3 < len(row):
                        current_employee['position'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
        
        # Check if this row contains "Date" (the dates row)
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Date":
            current_employee['dates'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Check-in1"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Check-in1":
            current_employee['check_ins'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Check-out1"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Check-out1":
            current_employee['check_outs'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Attended"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Attended":
            current_employee['attended_minutes'] = [x if pd.notna(x) and str(x) != '-' else 0 for x in row[1:]]
        
        # Check if this row contains "Status"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Status":
            current_employee['statuses'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Summary"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Summary":
            current_employee['summary'] = str(row[1]) if pd.notna(row[1]) else ''
    
    # Don't forget the last employee
    if current_employee is not None:
        employees.append(current_employee)
    
    return employees

def calculate_statistics(employee):
    """Calculate statistics for an employee"""
    
    total_minutes = 0
    total_days_worked = 0
    total_days_absent = 0
    total_weekends = 0
    
    for i, status in enumerate(employee['statuses']):
        if i < len(employee['attended_minutes']):
            minutes = employee['attended_minutes'][i]
            
            # Convert to int if possible
            try:
                minutes = int(float(minutes))
            except:
                minutes = 0
            
            status_str = str(status).upper()
            
            if 'W' in status_str:  # Worked
                total_days_worked += 1
                total_minutes += minutes
            elif 'A' in status_str and 'A-#' not in status_str:  # Absent (not weekend)
                total_days_absent += 1
            
            # Count weekends from summary if available
    
    # Parse summary for more accurate data
    summary = employee.get('summary', '')
    if summary:
        # Extract values from summary
        normal_match = re.search(r'Normal Attendance:(\d+)', summary)
        weekend_match = re.search(r'Weekend:(\d+)', summary)
        absence_match = re.search(r'Absence:(\d+)', summary)
        
        if normal_match:
            total_days_worked = int(normal_match.group(1))
        if weekend_match:
            total_weekends = int(weekend_match.group(1))
        if absence_match:
            total_days_absent = int(absence_match.group(1))
    
    total_hours = total_minutes / 60
    
    return {
        'total_hours': round(total_hours, 2),
        'total_days_worked': total_days_worked,
        'total_days_absent': total_days_absent,
        'total_weekends': total_weekends,
        'average_hours_per_day': round(total_hours / total_days_worked, 2) if total_days_worked > 0 else 0
    }

def process_and_generate_pdf(filepath, engine):
    """Process Excel file and generate PDF report"""
    
    # Parse the attendance data
    employees = parse_attendance_data(filepath, engine)
    
    # Generate PDF
    pdf_filename = f"rapport_assiduité_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(app.config['REPORT_FOLDER'], pdf_filename)
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#283593'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Add title
    title = Paragraph("RAPPORT D'ASSIDUITÉ MENSUEL", title_style)
    elements.append(title)
    
    # Add date
    date_text = Paragraph(f"<b>Date de génération:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style)
    elements.append(date_text)
    elements.append(Spacer(1, 20))
    
    # Global statistics
    total_employees = len(employees)
    total_hours_all = sum([calculate_statistics(emp)['total_hours'] for emp in employees])
    
    summary_data = [
        ['STATISTIQUES GLOBALES', ''],
        ['Nombre total d\'employés', str(total_employees)],
        ['Total heures travaillées', f"{round(total_hours_all, 2)} heures"],
        ['Moyenne heures/employé', f"{round(total_hours_all/total_employees, 2) if total_employees > 0 else 0} heures"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Add employee details
    elements.append(Paragraph("DÉTAILS PAR EMPLOYÉ", heading_style))
    elements.append(Spacer(1, 12))
    
    for emp in employees:
        stats = calculate_statistics(emp)
        
        # Employee header
        emp_header = Paragraph(f"<b>{emp['name']}</b> (ID: {emp['person_id']})", heading_style)
        elements.append(emp_header)
        
        # Employee details table
        emp_data = [
            ['Département', emp['department']],
            ['Poste', emp['position']],
            ['Date d\'embauche', emp['joining_date']],
            ['Jours travaillés', str(stats['total_days_worked'])],
            ['Jours d\'absence', str(stats['total_days_absent'])],
            ['Weekends', str(stats['total_weekends'])],
            ['Total heures travaillées', f"{stats['total_hours']} heures"],
            ['Moyenne heures/jour', f"{stats['average_hours_per_day']} heures"],
        ]
        
        emp_table = Table(emp_data, colWidths=[2.5*inch, 3.5*inch])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(emp_table)
        elements.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path

if __name__ == '__main__':
    app.run(debug=True)
