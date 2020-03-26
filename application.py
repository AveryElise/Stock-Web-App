from flask import Flask, render_template, request, url_for, session, g, redirect
from datetime import datetime
from flask_session import Session
from cs50 import SQL
import sqlite3
from sqlite3 import Error
app = Flask(__name__)

def create_connection(db_file):
	conn=None
	try:
		conn = sqlite3.connect(db_file)
		print(sqlite3.version)
	except Error as e:
		print(e)
	
	return conn


def inserttask(taskset):
	conn=create_connection(r"C:\Users\avery\Documents\Learn to Code\Standalone Projects\Task-Web-App\task.db")
	cur=conn.cursor()
	cur.execute('Insert into tasks(task, created) VALUES(?, ?)', taskset)
	conn.commit()
	conn.close()

def deletetask(taskid):
	conn=create_connection(r"C:\Users\avery\Documents\Learn to Code\Standalone Projects\Task-Web-App\task.db")
	cur=conn.cursor()
	cur.execute('DELETE FROM tasks WHERE taskid=?', (taskid,))
	conn.commit()
	conn.close()


def completetask(taskid):
	conn=create_connection(r"C:\Users\avery\Documents\Learn to Code\Standalone Projects\Task-Web-App\task.db")
	cur=conn.cursor()
	cur.execute('UPDATE tasks SET status = "completed" WHERE taskid=?', (taskid,))
	conn.commit()
	conn.close()


def gettasks():
	conn=create_connection(r"C:\Users\avery\Documents\Learn to Code\Standalone Projects\Task-Web-App\task.db")
	cur=conn.cursor()
	cur.execute('Select * from tasks WHERE status="active"')
	rows=cur.fetchall()
	l=[]
	for row in rows:
		temp={}
		temp['id']=row[0]
		temp['task']=row[1]
		temp['created']=row[2]
		l.append(temp)
	conn.commit()
	conn.close()
	return l


def getcompletedtasks():
	conn=create_connection(r"C:\Users\avery\Documents\Learn to Code\Standalone Projects\Task-Web-App\task.db")
	cur=conn.cursor()
	cur.execute('Select * from tasks WHERE status="completed"')
	rows=cur.fetchall()
	l=[]
	for row in rows:
		temp={}
		temp['id']=row[0]
		temp['task']=row[1]
		temp['created']=row[2]
		l.append(temp)
	conn.commit()
	conn.close()
	return l


@app.route('/')
def tasks():
	return render_template('home.html', title = 'Tasks', mytasks = gettasks())


@app.route('/completed')
def completed():
	return render_template('completed.html', title = 'Tasks', mytasks = getcompletedtasks())


@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/delete/<int:taskid>')
def delete(taskid):
	tasktodelete = taskid
	deletetask(tasktodelete)
	return redirect("/completed")


@app.route('/complete/<int:taskid>')
def complete(taskid):
	tasktocomplete = taskid
	completetask(tasktocomplete)
	return redirect("/")


@app.route('/create', methods = ['GET', 'POST'])
def create():
	idcounter=0
	if request.method == 'POST':
		newtask = request.form.get('newtask')
		date=datetime.now()
		created=str(date.month) + '/' + str(date.day) + '/' + str(date.year) + ' - ' + str(date.hour) + ':' + str(date.minute)
		taskset=(newtask, created)
		inserttask(taskset)
		return redirect("/")
	else:
		return render_template('home.html', title='Tasks', mytasks = gettasks())


app.run(debug=True)