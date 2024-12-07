from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Course, Assignment, Notification, Enrollment

# Flask App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

# Initialize Flask extensions
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/dashboard')
@login_required
def dashboard():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('dashboard.html', user=current_user, notifications=notifications)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        # Notify admin of a new registration
        admin_users = User.query.filter_by(role='admin').all()
        for admin in admin_users:
            notification = Notification(user_id=admin.id, message=f"New user registered: {username}.")
            db.session.add(notification)

        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'instructor':
        flash("Only instructors can create courses!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        new_course = Course(name=course_name, instructor_id=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        flash("Course created successfully.")
        return redirect(url_for('create_course'))

    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    return render_template('create_course.html', courses=courses)

@app.route('/view_courses')
@login_required
def view_courses():
    if current_user.role == 'student':
        courses = Course.query.join(Enrollment).filter(Enrollment.student_id == current_user.id).all()
    elif current_user.role == 'instructor':
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
    else:
        courses = []
    return render_template('view_courses.html', courses=courses)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash("Only students can enroll in courses!")
        return redirect(url_for('dashboard'))

    enrollment = Enrollment(course_id=course_id, student_id=current_user.id)
    db.session.add(enrollment)
    db.session.commit()
    flash("Enrolled successfully.")
    return redirect(url_for('view_courses'))

@app.route('/submit_assignment/<int:course_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(course_id):
    if current_user.role != 'student':
        flash("Only students can submit assignments!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        content = request.form.get('content')
        new_assignment = Assignment(course_id=course_id, student_id=current_user.id, content=content)
        db.session.add(new_assignment)

        # Notify instructor
        course = Course.query.get(course_id)
        if course:
            notification = Notification(
                user_id=course.instructor_id,
                message=f"New assignment submitted by {current_user.username} for course {course.name}."
            )
            db.session.add(notification)

        db.session.commit()
        flash("Assignment submitted successfully.")
        return redirect(url_for('view_courses'))

    course = Course.query.get(course_id)
    return render_template('submit_assignment.html', course=course)

@app.route('/grading_history')
@login_required
def grading_history():
    if current_user.role != 'instructor':
        flash("Only instructors can view grading history!")
        return redirect(url_for('dashboard'))

    graded_assignments = Assignment.query.filter(
        Assignment.grade.isnot(None),
        Assignment.course_id.in_([course.id for course in Course.query.filter_by(instructor_id=current_user.id)])
    ).all()
    return render_template('grading_history.html', graded_assignments=graded_assignments)

@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash("Only admins can manage users!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        user = User.query.get(user_id)

        if action == 'delete' and user:
            db.session.delete(user)
            db.session.commit()
            flash("User deleted successfully.")
        elif action == 'update' and user:
            new_role = request.form.get('role')
            user.role = new_role
            db.session.commit()
            flash("User role updated successfully.")

    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'admin':
        flash("Only admins can manage courses!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        action = request.form.get('action')
        course = Course.query.get(course_id)

        if action == 'delete' and course:
            db.session.delete(course)
            db.session.commit()
            flash("Course deleted successfully.")

    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses)


@app.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '')
    if current_user.role == 'student':
        results = Course.query.filter(Course.name.contains(query)).all()
    elif current_user.role == 'instructor':
        results = Assignment.query.filter(Assignment.content.contains(query)).all()
    elif current_user.role == 'admin':
        results = User.query.filter(User.username.contains(query)).all()
    else:
        results = []
    return render_template('search_results.html', results=results, query=query)

if __name__ == "__main__":
    app.run(debug=True)
