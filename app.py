from flask import *
from sqlalchemy import *
app = Flask(__name__)
import random
import time

app.static_folder = 'static'
app.config["SESSION_PERMANENT"] = False #sets up user and makes them not logged in forever
app.config["SESSION_TYPE"] = "filesystem"

app.secret_key = "65154d29a180088a4eb6a726e07cc63b449e5d8855b048ac" #Random string

engine = create_engine('sqlite:///userdata.db')
connection = engine.connect()
connection.execute(text("""
CREATE TABLE IF NOT EXISTS USERS( 
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uname TEXT UNIQUE NOT NULL,
    passw TEXT NOT NULL)
    """))

connection.execute(text("""
CREATE TABLE IF NOT EXISTS QUESTIONS (
    QuestionID INTEGER PRIMARY KEY AUTOINCREMENT,
    Question TEXT NOT NULL,
    CorrectAnswer TEXT NOT NULL,
    Incorrect1 TEXT NOT NULL,
    Incorrect2 TEXT NOT NULL,
    Incorrect3 TEXT NOT NULL,
    Topic TEXT NOT NULL,
    Owner INTEGER,
    FOREIGN KEY (owner) REFERENCES USERS(id)
)
"""))


connection.execute(text("""
CREATE TABLE IF NOT EXISTS RESULTS (
    ResultID INTEGER PRIMARY KEY AUTOINCREMENT,
    Score INTEGER NOT NULL,
    Owner INTEGER,
    Topic TEXT NOT NULL,
    FOREIGN KEY (owner) REFERENCES USERS(id)
)
"""))

connection.commit()


#Routes to access pages 
@app.route("/")
def home():
    return render_template('index.html')

@app.route("/view", methods=['GET'])
def view():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    query = text("SELECT Question, CorrectAnswer FROM QUESTIONS WHERE OWNER = :owner")#Selects questions where owner is user id
    with engine.begin() as conn:
        result = conn.execute(query, {"owner": username}).fetchall()
        print(result)
    question_dict = [{"question": row[0], "answers": row[1]} for row in result]
    return render_template('view.html', question = question_dict)


#Delete Logic + Edit Page 25/05
@app.route("/edit", methods=['GET', 'POST'])
def edit():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    query = text("SELECT QuestionID, Question, CorrectAnswer, Topic FROM QUESTIONS WHERE OWNER = :owner")#Selects questions where owner is user id
    with engine.begin() as conn:
        result = conn.execute(query, {"owner": username}).fetchall()
        print(result)
    question_dict = [{"id": row[0], "question": row[1], "answers": row[2], "Topic": row[3]} for row in result]
    return render_template('edit.html', question = question_dict)



@app.route('/deletequestion/<int:question_id>', methods=['GET', 'POST'])
def deletecard(question_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    if not question_id: #This will only occur if user manually navigates to the deletecard url without clicking delete
        redirect(url_for('edit'))
    query = text("""
    DELETE FROM questions
    WHERE questionID =:questionID AND owner = :owner""")#Checks owner to ensure only the owner can delete their own cards and not others
    with engine.begin() as conn:
        conn.execute(query, {"questionID": question_id, "owner": username})
    return redirect(url_for('edit'))






#Add Question logic 30/04
@app.route("/add", methods=['GET'])
def add():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('add.html')


@app.route('/add', methods=['POST'])
def add_form():
    topic= request.form['Topic'].upper() #Gets info from form 
    question = request.form['Question']
    correct= request.form['Correct']
    ic1= request.form['Incorrect1']
    ic2= request.form['Incorrect2']
    ic3= request.form['Incorrect3']
    user= session['user']
    if not topic or not question or not correct or not ic1 or not ic2 or not ic3: #Makes sure no fields are empty
        flash("One or more fields are empty")
        time.sleep(0.1)
        return redirect(url_for('add')) #Reloads add page 
    else: 
        insert_q= text(''' INSERT INTO QUESTIONS (Question, CorrectAnswer, Incorrect1, Incorrect2, Incorrect3, Topic, Owner)
        VALUES (:question, :correct, :ic1, :ic2, :ic3,:topic, :user)''') #Inserts to sql
        with engine.begin() as conn:
            conn.execute(insert_q, {"question": question, "correct": correct, "ic1": ic1, "ic2": ic2, "ic3": ic3,"topic":topic, "user":user}) #Adds q to database table
            return redirect(url_for('home')) #Redirects to home

#7/05 Study logic
@app.route("/study", methods=['GET'])
def study():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    topics = connection.execute(text("SELECT topic FROM QUESTIONS WHERE owner = :u"), {"u": username}).fetchall()
    return render_template('study.html', topics=topics)




@app.route("/start_quiz", methods=['GET','POST'])
def start_quiz():
    if 'user' not in session:
        return redirect(url_for('login'))
    if not request.form.get('Topic'): #Ensures user will have selected a topic in quiz screen and not manually navigated to url
        return redirect(url_for('study'))
    chosen_topic = request.form.get('Topic').upper()
    username = session['user']
    if not chosen_topic:
        return redirect(url_for('study'))
    query = text("SELECT * FROM QUESTIONS WHERE Topic = :topic and Owner = :u") #Creates query to get all Q's + Answers
    questions = connection.execute(query, {"topic": chosen_topic, "u": username}).fetchall()
    quiz_data=[]
    if not questions:
        return redirect(url_for('add'))
    for row in questions: #shuffles the answers so correct one isnt always on the top of the page
        answers = [row[2], row[3], row[4], row[5]] #puts all the answer data in a list
        random.shuffle(answers) #Shuffles the answers
        quiz_data.append({"question": row[1], "answers": answers}) #adds both Q and A into a single array
    print(quiz_data)
    return render_template('quiz.html', questions = quiz_data, topic = chosen_topic)


#Submit logic 31/05 and 1/06
@app.route("/submit_quiz", methods=['GET','POST'])
def submit_quiz():
    if request.method == 'GET': #Makes it so user cant manually go to url or reload 
        return redirect(url_for('study'))
    if 'user' not in session:
        return redirect(url_for('login'))
    uname = session['user']
    score = 0 
    chosen_topic = request.form.get('Topic').upper()
    query = text("SELECT Question, CorrectAnswer FROM QUESTIONS WHERE Topic = :topic and Owner = :u")
    db_questions = connection.execute(query, {"topic": chosen_topic, "u": uname}).fetchall() # Gets all questions from topic that user made
    for row in db_questions:
        db_q_text = row[0]# Question from db
        correct_answer = row[1] #answer from db
        user_answer= request.form.get(db_q_text) #gets user answer from form
        if user_answer == correct_answer:
            score +=1 #if user is right score goes up by 1 
    insert_result = text("""INSERT INTO RESULTS (Score, Owner, Topic) VALUES (:Score, :User, :Topic)""")
    with engine.begin() as conn:
        conn.execute(insert_result, {"Score": score, "User": uname, "Topic": chosen_topic})
    session['last_quiz'] = { #Creates a session variable to get results on page (Nested dictionary)
        'topic': chosen_topic,
        'score': score,
        'total': len(db_questions)}
    quiz_summary = session.get('last_quiz')
    return redirect(url_for('results'))





@app.route("/results", methods=['GET'])
def results():
    if 'user' not in session:
        return redirect(url_for('login')) #Checks if user logged in
    quiz_summary = session.get('last_quiz') #gets all the quiz data
    if not quiz_summary:
        return redirect(url_for('study')) #if user hasnt done quiz take them back to study
    percent = round((quiz_summary['score']/ quiz_summary['total'])*100) #Calculates % to show on page
    session.pop('last_quiz', None) #removes last quiz so it doesnt stay as session variable and user can take multiple quizzes
    return render_template('results.html', topic = quiz_summary['topic'], score= quiz_summary['score'], total = quiz_summary['total'], percentage = percent)
    




@app.route("/login", methods=['GET'])
def login():
    return render_template('login.html')


@app.route("/register", methods=['GET'])
def reg():
    return render_template('register.html')



#login/register logic (Started 23/04)
@app.route("/login", methods=['POST'])
def login_action():
    u = request.form['Username'] #gets from form
    pw= request.form['Password']
    if not u or not pw: #IF nothing in fields
        return redirect(url_for('login'))
    check_statement = text("SELECT passw FROM USERS WHERE uname = :username") #runs an sql query to check if user already exists, if they do then it fails
    result = connection.execute(check_statement, {"username": u}).fetchone()
    if result and result[0] == pw:
        session['user'] = u
        return redirect(url_for('home'))
    else:
        flash("Invalid Credentials")
        return redirect(url_for('login'))





@app.route("/register", methods=['POST'])
def register_action():
    uname = request.form['Username']
    passw= request.form['Password']
    passwc= request.form['Pass2']
    if not uname: #If any arent filled in refresh page + Show error
        print("ERROR Username")
        flash("username required")
        return redirect(url_for('reg'))
    if not passw:
        print("ERROR PW")
        flash("Password Required")
        return redirect(url_for('reg'))
    if not passwc:
        flash("Please confirm password")
        return redirect(url_for('reg'))
    if not passw == passwc:
        flash("ERROR Passwords don't match")
        return redirect(url_for('reg'))
    check_statement = text("SELECT COUNT (*) FROM USERS WHERE uname = :uname") #runs an sql query to check if user already exists, if they do then it fails
    result = connection.execute(check_statement, {"uname": uname}).fetchone() #Fetches the amount of users with said name
    count = result[0]
    if count > 0:
        flash("Username Taken")
        return redirect(url_for('reg'))
    else:
        insert_com= ''' insert into users (Uname, Passw)
                        VALUES ('{}','{}');'''.format(uname, passw) #adds the user credentials to db table
        connection.execute(text(insert_com))
        connection.commit()
        return redirect(url_for('login')) #Goes to login page



@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))





if __name__ == "__main__":
    app.run(debug=True)
