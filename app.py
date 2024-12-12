import os
from flask import Flask, render_template, request, redirect, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure random key

# MongoDB Connection
uri = "mongodb+srv://soujashban:hrVGtkBurivaUCbN@cluster0.hykpe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))

# Create a new database
db = client['LearningPlatform']

# Create collections
users_collection = db['Users']
courses_collection = db['Courses']
tests_available_collection = db['TestsAvailable']
test_results_collection = db['TestResults']

def save_user(username, email, password, grade, mode):
    # Hash the password before storing
    hashed_password = generate_password_hash(password)
    
    # Check if user already exists
    existing_user = users_collection.find_one({'email': email})
    if existing_user:
        return False
    
    # Insert new user
    users_collection.insert_one({
        'username': username,
        'email': email,
        'password': hashed_password,
        'grade': grade,
        'mode': mode
    })
    return True

def find_user_by_email(email):
    return users_collection.find_one({'email': email})

def get_materials_by_grade(grade):
    """
    Retrieve materials for a specific grade from the Materials folder
    """
    materials_path = os.path.join('Materials', f'Grade {grade}')
    
    if not os.path.exists(materials_path):
        return []
    
    materials = []
    for root, dirs, files in os.walk(materials_path):
        for file in files:
            # Create a relative path from the Materials folder
            relative_path = os.path.relpath(os.path.join(root, file), materials_path)
            materials.append({
                'filename': file,
                'path': relative_path,
                'full_path': os.path.join(root, file)
            })
    
    return materials

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = find_user_by_email(email)
        
        if user and check_password_hash(user['password'], password):
            # Store all user details in session
            session['username'] = user['username']
            session['email'] = email
            session['grade'] = user['grade']
            session['mode'] = user['mode']
            
            flash('Login successful!', 'success')
            
            # Route based on user mode
            if user['mode'] == 'digital':
                return redirect('/home-digital')
            else:
                return redirect('/home-textbook')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Capture data from both steps of signup
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        grade = request.form['grade']
        mode = request.form['mode']
        
        # Check if email already exists
        if find_user_by_email(email):
            flash('Email already registered', 'error')
            return render_template('signup.html')
        
        # Save user
        if save_user(username, email, password, grade, mode):
            flash('Signup successful! Please log in.', 'success')
            return redirect('/login')
        else:
            flash('Error during signup', 'error')
    
    return render_template('signup.html')

@app.route('/home-digital')
def dashboardDigital():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    # Ensure user is in digital mode
    if session.get('mode') != 'digital':
        flash('Access denied', 'error')
        return redirect('/login')
    
    # Get materials for the user's grade
    materials = get_materials_by_grade(session['grade'])
    
    # Get available tests
    tests = get_available_tests(session['grade'])
    
    # Get user's test results
    test_results = get_user_test_results(session['email'])
    
    # Pass user information and materials to the template
    return render_template('home.html', 
                           username=session['username'], 
                           grade=session['grade'],
                           materials=materials,
                           tests=tests,
                           test_results=test_results)

@app.route('/home-textbook')
def dashboardTextbook():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    # Ensure user is in textbook mode
    if session.get('mode') != 'textbook':
        flash('Access denied', 'error')
        return redirect('/login')
    
    # Pass user information to the template
    return render_template('home-test.html', 
                           username=session['username'], 
                           grade=session['grade'])

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect('/login')

@app.route('/download-material')
def download_material():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    material_path = request.args.get('path')
    grade = session['grade']
    
    # Construct full path
    full_path = os.path.join('Materials', f'Grade {grade}', material_path)
    
    # Check if file exists
    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=True)
    else:
        flash('Material not found', 'error')
        return redirect('/home-digital')

# Functions for managing courses
def add_course(course_name, grade, subject):
    course = {
        'name': course_name,
        'grade': grade,
        'subject': subject
    }
    return courses_collection.insert_one(course).inserted_id

def get_courses_by_grade(grade):
    return list(courses_collection.find({'grade': grade}))

# Functions for managing tests
def add_available_test(test_name, subject, grade, difficulty):
    test = {
        'name': test_name,
        'subject': subject,
        'grade': grade,
        'difficulty': difficulty
    }
    return tests_available_collection.insert_one(test).inserted_id

def get_available_tests(grade, subject=None):
    query = {'grade': grade}
    if subject:
        query['subject'] = subject
    return list(tests_available_collection.find(query))

# Functions for managing test results
def save_test_result(user_email, test_id, score, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now()
    
    result = {
        'user_email': user_email,
        'test_id': test_id,
        'score': score,
        'timestamp': timestamp
    }
    return test_results_collection.insert_one(result).inserted_id

def get_user_test_results(user_email):
    return list(test_results_collection.find({'user_email': user_email}))

# Additional routes
@app.route('/courses')
def list_courses():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    courses = get_courses_by_grade(session['grade'])
    return render_template('courses.html', courses=courses)

@app.route('/tests')
def list_tests():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    tests = get_available_tests(session['grade'])
    return render_template('tests.html', tests=tests)

@app.route('/test_results')
def list_test_results():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    results = get_user_test_results(session['email'])
    return render_template('test_results.html', results=results)

@app.route('/materials')
def list_materials():
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect('/login')
    
    # Get materials for the user's grade
    materials = get_materials_by_grade(session['grade'])
    return render_template('materials.html', 
                           username=session['username'], 
                           grade=session['grade'],
                           materials=materials)



if __name__ == '__main__':
    app.run(debug=True)