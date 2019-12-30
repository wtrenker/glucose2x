from flask import Flask, request, Markup, send_file, render_template, session, redirect, flash, url_for, jsonify, Response
from pony.orm import Database, Optional, Required, PrimaryKey, db_session, sql_debug, select
from forms import SigninForm, DataEntryForm, SelectReadingForm, EditReadingForm, PickReadingForm
from GeneralFunctions import verify_password, decimalAverage
from collections import namedtuple
import time
import os
from pathlib import Path
import FileSessLog as fsl
import Chart

import pprint

dbFileName = "glucose.db"
dbPath = Path(f'/home/bill/glucose2/db/{dbFileName}')
# dbPath = Path(dbFile)
db = Database()

class Readings(db.Entity):
    date = PrimaryKey(str)
    am = Required(float)
    pm = Optional(float)
    comment = Optional(str)
    average = Optional(float)

DAtE = 0
AM = 1

PM = 2
COMMENT = 3
AVERAGE = 4

# class Info(db.Entity):
#     name = PrimaryKey(str)
#     value = Optional(str)


db.bind(provider='sqlite', filename=str(dbPath), create_db=False)
db.generate_mapping(create_tables=False)

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = os.urandom(512)
app.debug = True

if app.debug:
    fsl.initLog()
    log = fsl.log
else:
    def noop(dummy1): pass
    log = noop

jinjadict = {}

@app.errorhandler(405)
def methodNotAllowed(e):
    f = request.full_path.split('?', 1)[0]
    jinjadict.update(dict(f=f))
    return render_template('405.jinja2', **jinjadict), 405

@app.errorhandler(500)
def methodNotAllowed(e):
    return render_template('500.jinja2'), 500


firstTimeThrough= True
@app.route('/', methods=['GET'])
def home():
    global firstTimeThrough
    if firstTimeThrough:
        fsl.initSession()
        fsl.initLog()
        firstTimeThrough = False
    log('*********************** starting **********************')
    log(f'home() {request.method}')
    fsl.putSession('signedin', False)
    return render_template('Home.jinja2', title='Glucose Chart')

@app.route('/averages', methods=['GET'])
def averages():
    return render_template('Averages.jinja2', title='Blood Glucose Daily Average', req=dir(request), timestamp=time.time())

def setupNumberOfPartials():
    with db_session:
        numberOfHeldReadings = len(Readings.select(lambda c: c.am is not None and c.pm is None))
    fsl.putSession('numberOfHeldReadings', numberOfHeldReadings)
    log(f'setUpNumberOfPartials: numberOfHeldReadings = {numberOfHeldReadings}')
    if numberOfHeldReadings == 0:
        flash('There are no partial readings.')
    elif numberOfHeldReadings == 1:
        flash('There is one partial reading.')
    else:
        flash(f'There are {numberOfHeldReadings} partial readings.')
    jinjadict.update(dict(numberOfHeldReadings=numberOfHeldReadings))

@app.route("/signin", methods=['GET', 'POST'])
def signin():
    # f = open('/home/bill/glucose2/glucose2/wdt.log', 'w')
    # f.write(f'signin() {request.method}')
    # f.close()

    log(f'signin() {request.method}')

    if request.method == 'GET':
        flash(dbPath)
        form = SigninForm(request.form)
        jinjadict.update(dict(form=form))
        log('signin: render_template(Signin.jinja2)')
        return render_template('Signin.jinja2', **jinjadict)
    else:
        form = SigninForm(request.form)
        jinjadict.update(dict(form=form))
        typedcode = form.data['code']
        log(f'signin: typedcode = {typedcode}')
        savedcode = fsl.getCode()
        log(f'signin: savedcode = {savedcode}')
        signedin = verify_password(savedcode, typedcode)
        fsl.putSession('signedin', signedin)
        if signedin:
            # with db_session:
            #     numberOfHeldReadings = len(Readings.select(lambda c: (c.am is not None and c.pm is not None) or c.hold is not None))
            # log(f'signin: numberOfHeldReadings = {numberOfHeldReadings}')
            # jinjadict.update(dict(numberOfHeldReadings=numberOfHeldReadings))

            rv = redirect(url_for('admin'))
            log('signin: redirect(url_for("admin"))')
            return rv
        else:
            flash('Try Again')
            return redirect(url_for('signin'))

@app.route("/admin", methods=['GET'])
def admin():
    log(f'admin() {request.method}')
    if fsl.getSession('signedin'):
        log(f'admin: signedin exists and = {fsl.getSession("signedin")}')
    else:
        log(f'admin: signedin does not exist')
        log(f'admin: redirect(url_for("signin")')
        return redirect(url_for('signin'))
    flash(dbPath)
    setupNumberOfPartials()
    log(f'admin: render_template("Admin.jinja2")')
    stuff = jinjadict
    return render_template('Admin.jinja2', **jinjadict)

class myResponse(object):
    pass

@app.route("/enter", methods=['GET', 'POST'])
def enterData():

    log(f'enterData() {request.method}')
    log(f'enterData: isLoggedIn = {fsl.getSession("signedin")}')

    flash(dbPath)

    if request.method == 'GET':
        if not (fsl.getSession('signedin')):
            return redirect(url_for('signin'))
        form = DataEntryForm(request.form)
        jinjadict.update(dict(form=form))
        rv = render_template('EnterReading.jinja2', **jinjadict)
        return rv

    else:
        # form = DataEntryForm(request.form)
        reqdate = request.form['ddate']
        comment = request.form['annotation']
        morning = request.form['amreading']
        evening = request.form['pmreading']
        if evening == '': evening = None
        try:
            with db_session:
                Readings(date=reqdate, am=morning, pm=evening, comment=comment, average=None)
        except Exception as e:
            e = str(e)
            if e.find('UNIQUE constraint failed') > -1:
                flash('ERROR: That date is already entered.')
            else:
                flash(f'ERROR: {e}')
        setupNumberOfPartials()
        return render_template('Admin.jinja2', **jinjadict)
        # return redirect(url_for('enterData'))
        # return redirect('/enter', Response=myResponse)

@app.route("/selectReading", methods=['GET'])
def selectReading():

    if not fsl.getSession('signedin'):
        return redirect(url_for('signin'))

    flash(dbPath)

    form = SelectReadingForm(request.form)
    jinjadict.update(dict(form=form))
    with db_session:
        heldReadings = Readings.select(lambda c: c.am is not None and c.pm is None).order_by(1)
        heldReadingsList = list(heldReadings)
    numberOfHeldReadings = len(heldReadingsList)
    if numberOfHeldReadings > 0:
        heldReadingDates = []
        index = 1
        for heldReading in heldReadingsList:
            heldReadingDates.append((f'D{index}', heldReading.date))
            index += 1
        form.helddateslist.choices = heldReadingDates
        fsl.putSession('heldDates', heldReadingDates)

        return render_template('SelectReading.jinja2', **jinjadict)  # form=heldForm)
    else:
        return render_template('NoneHeld.jinja2', **jinjadict)

@app.route("/edit", methods=['POST'])
def edit():

    flash(dbPath)

    form = SelectReadingForm(request.form)
    FormIndex = form.data['helddateslist']
    heldReadingDates = fsl.getSession('heldDates')
    fsl.putSession('heldDates', None)
    heldReadingDates = dict(heldReadingDates)
    WorkingDate = heldReadingDates[FormIndex]
    fsl.putSession('WorkingDate', WorkingDate)
    with db_session:
        reading = Readings[WorkingDate]
    heldReading = namedtuple('heldReading', ['readingDate', 'amreading', 'annotation'])
    hr = heldReading(WorkingDate, reading.am, reading.comment)
    form = EditReadingForm(obj=hr)
    jinjadict.update(dict(form=form))
    return render_template('EditReading.jinja2', **jinjadict)

@app.route("/update", methods=['POST'])
def update():

    if not fsl.getSession('signedin'):
        return redirect(url_for('signin'))

    WorkingDate = fsl.getSession('WorkingDate')
    fsl.putSession('WorkingDate', None)
    form = EditReadingForm(request.form)
    morning = form.data['amreading']
    evening = form.data['pmreading']
    if evening is None:
        return render_template('NoEvening.jinja2', **jinjadict)
    assert WorkingDate is not None
    with db_session:
        reading = Readings[WorkingDate]
        reading.pm = evening
        reading.comment = form.data['annotation']
    return redirect(url_for('admin'))

@app.route("/delete", methods=['GET', 'POST'])
def delete():

    if not fsl.getSession('signedin'):
        return redirect(url_for('signin'))

    if request.method == 'GET':
        return render_template('Delete.jinja2', **jinjadict)

    else:
        '''
        get selectedDate from request.form
        get Readig object from db
        
        '''

@app.route("/pick", methods=['GET', 'POST'])
def pick():
    if not fsl.getSession('signedin'):
        return redirect(url_for('signin'))
    form = PickReadingForm(request.form)
    if request.method == 'GET':
        jinjadict.update(dict(form=form))
        return render_template('PickReadingByDate.jinja2', **jinjadict)
    else:

        return f'picked data is {form.date}'

@app.route(Markup('/chart'), methods=['GET'])
def chart():
    img = Chart.renderChart(Readings, dbFileName)
    return send_file(img, mimetype='image/png')


if __name__ == '__main__':
    port = 5000
    app.run(host='wtrenker.com', port=port, debug=True, use_reloader=False)
# use_reloader=False is the key to getting multi-threaded debug working in PyCharm
