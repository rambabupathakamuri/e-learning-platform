from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, Enrollment, Course
from app import db, bcrypt
from functools import wraps

main = Blueprint('main', __name__)  # Declare the Blueprint

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            email = session.get('email')
            user = User.query.filter_by(email=email).first()
            if user and user.role == role:
                return f(*args, **kwargs)
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.login'))  # Use 'main' for Blueprint
        return decorated_function
    return decorator

@main.route('/')
def index():
    """Render the home page."""
    email = session.get('email')
    user = User.query.filter_by(email=email).first() if email else None
    return render_template('index.html', logged_in=bool(user), username=user.username if user else None)

@main.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        role = request.form.get('role').strip()
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for('main.login'))  # Ensure this matches your blueprint

        new_user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('main.login'))

    return render_template('register.html')  # Ensure this points to the correct template


@main.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['email'] = user.email
            session['role'] = user.role
            flash("Login successful!", "success")

            if user.role == "student":
                return redirect(url_for('main.student_home'))
            elif user.role == "instructor":
                return redirect(url_for('main.instructor_dashboard'))
            elif user.role == "admin":
                return redirect(url_for('main.admin_dashboard'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('main.login.html')

@main.route('/student_home')
@role_required('student')
def student_home():
    """Render the student dashboard."""
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    enrolled_courses = Enrollment.query.filter_by(user_id=user.id).all()
    return render_template('main.student_home.html', username=user.username, enrolled_courses=enrolled_courses)

@main.route('/enroll', methods=['GET', 'POST'])
@role_required('student')
def enroll():
    """Allow students to enroll in courses."""
    available_courses = Course.query.all()
    email = session.get('email')
    user = User.query.filter_by(email=email).first()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        if course_id and not Enrollment.query.filter_by(user_id=user.id, course_id=course_id).first():
            enrollment = Enrollment(course_id=course_id, user_id=user.id)
            db.session.add(enrollment)
            db.session.commit()
            flash("Successfully enrolled in the course!", "success")
        else:
            flash("You are already enrolled or invalid course.", "warning")

    enrolled_courses = Enrollment.query.filter_by(user_id=user.id).all()
    return render_template('enroll.html', available_courses=available_courses, enrolled_courses=enrolled_courses)

@main.route('/create_course', methods=['GET', 'POST'])
@role_required('instructor')
def create_course():
    """Allow instructors to create new courses."""
    if request.method == 'POST':
        name = request.form.get('name').strip()
        description = request.form.get('description').strip()
        email = session.get('email')
        instructor = User.query.filter_by(email=email).first()

        new_course = Course(name=name, description=description, instructor_id=instructor.id)
        db.session.add(new_course)
        db.session.commit()
        flash("Course created successfully!", "success")
        return redirect(url_for('main.instructor_dashboard'))

    return render_template('main.create_course.html')

@main.route('/instructor_dashboard')
@role_required('instructor')
def instructor_dashboard():
    """Render the instructor dashboard."""
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    courses = Course.query.filter_by(instructor_id=user.id).all()
    return render_template('main.instructor_dashboard.html', username=user.username, courses=courses)

@main.route('/admin_dashboard')
@role_required('admin')
def admin_dashboard():
    """Render the admin dashboard."""
    email = session.get('email')
    user = User.query.filter_by(email=email).first()
    return render_template('main.admin_dashboard.html', username=user.username)

@main.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('email', None)
    session.pop('role', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('main.index'))
