from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime

# Initialize the app and database
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///e_learning.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Roles: student, instructor, admin

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship('Course', backref='assignments')

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    grade = db.Column(db.String(10))  # Grade given by the instructor
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    assignment = db.relationship('Assignment', backref='submissions')
    student = db.relationship('User', backref='submissions')


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    student = db.relationship('User', backref='enrollments')
    course = db.relationship('Course', backref='enrollments')

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='discussions')

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='replies')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    courses = Course.query.all()
    return render_template('home.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully. Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'student':
        # Fetch enrolled courses
        enrolled_courses = [enrollment.course for enrollment in current_user.enrollments]

        # Fetch available courses (exclude already enrolled courses)
        discussions = Discussion.query.filter(Discussion.course_id.in_([course.id for course in enrolled_courses])).all()

        # Fetch available courses (exclude already enrolled courses)
        available_courses = Course.query.filter(~Course.id.in_([course.id for course in enrolled_courses])).all()

        return render_template(
            'student_dashboard.html',
            enrolled_courses=enrolled_courses,
            available_courses=available_courses,
            discussions=discussions
        )
    
    elif current_user.role == 'instructor':
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        return render_template('instructor_dashboard.html', courses=courses)
    
    elif current_user.role == 'admin':
        users = User.query.all()
        courses = Course.query.all()
        return render_template('admin_dashboard.html', users=users, courses=courses)
    
    flash('Invalid role.')
    return redirect(url_for('logout'))



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'instructor':
        flash('Only instructors can create courses.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_course = Course(title=title, description=description, instructor_id=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        flash('Course created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_course.html')

@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Only administrators can manage users.')
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role != 'admin':
        flash('Only administrators can manage courses.')
        return redirect(url_for('dashboard'))

    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses)

@app.route('/send_notification/<int:course_id>', methods=['GET', 'POST'])
@login_required
def send_notification(course_id):
    if current_user.role != 'instructor':
        flash('Only instructors can send notifications.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        message = request.form['message']
        notification = Notification(message=message, course_id=course_id, sender_id=current_user.id)
        db.session.add(notification)
        db.session.commit()
        flash('Notification sent!')
        return redirect(url_for('dashboard'))
    return render_template('send_notification.html', course_id=course_id)

from datetime import datetime  # Make sure to import datetime

@app.route('/create_assignment/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_assignment(course_id):
    if current_user.role != 'instructor':
        flash('Only instructors can create assignments.')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        # Convert due_date to a datetime object
        try:
            due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use the date picker provided.')
            return render_template('create_assignment.html', course=course)
        
        assignment = Assignment(title=title, description=description, due_date=due_date, course_id=course_id)
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment created successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('create_assignment.html', course=course)


@app.route('/submit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    if current_user.role != 'student':
        flash('Only students can submit assignments.')
        return redirect(url_for('dashboard'))

    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if the student is enrolled in the course
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=assignment.course_id).first()
    if not enrollment:
        flash('You are not enrolled in this course.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Create a submission for the assignment
        content = request.form['content']
        submission = Submission(content=content, assignment_id=assignment.id, student_id=current_user.id)
        db.session.add(submission)
        db.session.commit()
        flash('Assignment submitted successfully!')
        return redirect(url_for('dashboard'))

    return render_template('submit_assignment.html', assignment=assignment)


@app.route('/grade_submission/<int:submission_id>', methods=['POST'])
@login_required
def grade_submission(submission_id):
    if current_user.role != 'instructor':
        flash('Only instructors can grade submissions.')
        return redirect(url_for('dashboard'))

    submission = Submission.query.get_or_404(submission_id)

    # Check if the submission belongs to the instructor's course
    if submission.assignment.course.instructor_id != current_user.id:
        flash('You can only grade submissions for your own assignments.')
        return redirect(url_for('dashboard'))

    # Update the grade
    submission.grade = request.form['grade']
    db.session.commit()
    flash('Grade submitted successfully!')
    return redirect(url_for('view_submissions', assignment_id=submission.assignment_id))


@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash('Only students can enroll in courses.')
        return redirect(url_for('dashboard'))
    
    # Check if the student is already enrolled
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if enrollment:
        flash('You are already enrolled in this course.')
    else:
        # Create a new enrollment
        enrollment = Enrollment(student_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Successfully enrolled in the course!')
    
    return redirect(url_for('dashboard'))

@app.route('/view_submissions/<int:assignment_id>')
@login_required
def view_submissions(assignment_id):
    if current_user.role != 'instructor':
        flash('Only instructors can view submissions.')
        return redirect(url_for('dashboard'))

    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if the assignment belongs to an instructor's course
    if assignment.course.instructor_id != current_user.id:
        flash('You can only view submissions for your own assignments.')
        return redirect(url_for('dashboard'))

    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    return render_template('view_submissions.html', assignment=assignment, submissions=submissions)

@app.route('/discussion/<int:discussion_id>', methods=['GET', 'POST'])
@login_required
def reply(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)

    # Ensure the user is enrolled in the course
    if current_user.role == 'student':
        enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=discussion.course_id).first()
        if not enrollment:
            flash('You are not enrolled in this course.')
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        content = request.form['content']
        reply = Reply(content=content, discussion_id=discussion.id, user_id=current_user.id)
        db.session.add(reply)
        db.session.commit()
        flash('Reply posted successfully!')
        return redirect(url_for('reply', discussion_id=discussion_id))

    replies = Reply.query.filter_by(discussion_id=discussion_id).all()
    return render_template('discussion.html', discussion=discussion, replies=replies)


@app.route('/create_discussion/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_discussion(course_id):
    if request.method == 'POST':
        title = request.form['title']
        discussion = Discussion(title=title, course_id=course_id, user_id=current_user.id)
        db.session.add(discussion)
        db.session.commit()
        flash('Discussion created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_discussion.html', course_id=course_id)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Only admins can delete users.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    
    # Prevent deleting self
    if user.id == current_user.id:
        flash('You cannot delete yourself.')
        return redirect(url_for('dashboard'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'admin':
        flash('Only admins can delete courses.')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course.title}" deleted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Only admins can edit users.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        flash(f'User {user.username} updated successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_user.html', user=user)

@app.route('/discussion_reply/<int:discussion_id>', methods=['GET', 'POST'])
def discussion_reply(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)

    # Ensure the user is enrolled in the course
    if current_user.role == 'student':
        enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=discussion.course_id).first()
        if not enrollment:
            flash('You are not enrolled in this course.')
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        content = request.form['content']
        reply = Reply(content=content, discussion_id=discussion.id, user_id=current_user.id)
        db.session.add(reply)
        db.session.commit()
        flash('Reply posted successfully!')
        return redirect(url_for('discussion_reply', discussion_id=discussion_id))

    replies = Reply.query.filter_by(discussion_id=discussion_id).all()
    return render_template('discussion.html', discussion=discussion, replies=replies)


is_active = db.Column(db.Boolean, default=True)

@app.route('/notifications/<int:course_id>')
@login_required
def notifications(course_id):
    notifications = Notification.query.filter_by(course_id=course_id).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
