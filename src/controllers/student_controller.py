# student_controller.py
from flask import Blueprint

student_bp = Blueprint('student_bp', __name__)

@student_bp.route('/student/dashboard')
def student_dashboard():
    return "Student Dashboard"
