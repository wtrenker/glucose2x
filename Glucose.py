from flask import Flask, request, Markup, send_file, render_template, session, redirect, flash, url_for, jsonify
import matplotlib as mpl
mpl.use('Agg')
from pony.orm import Database, Optional, Required, PrimaryKey, db_session, sql_debug, select
from forms import SigninForm, DataEntryForm, SelectReadingForm, EditReadingForm
from GeneralFunctions import verify_password, decimalAverage
import matplotlib.pyplot as plt
import matplotlib.dates as mpd
import numpy as np
from collections import namedtuple
from io import BytesIO
import time
import os
import datetime as dt
from pathlib import Path
import json
import pytz
import pprint
import logging
import logging.handlers
import FileSessLog as fsl

dbFileName = "glucose.db"
dbPath = Path(f'/home/bill/glucose2/db/{dbFileName}')
# dbPath = Path(dbFile)
db = Database()

class Readings(db.Entity):
    date = PrimaryKey(str)
    average = Optional(float)
    comment = Optional(str)
    hold = Optional(float)

# class Info(db.Entity):
#     name = PrimaryKey(str)
#     value = Optional(str)

zulu = pytz.timezone('UTC')
pst = pytz.timezone("America/Vancouver")

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
    log = noop()

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

@app.route(Markup('/chart'), methods=['GET'])
def chart():

    DateCombined = []
    CommentDateCombined = []
    DailyAverageCombined = []
    CommentCombined = []
    CommentAverageCombined = []

    with db_session:
        qry = select((r.date, r.average, r.comment) for r in Readings).order_by(1)
        recs = qry.fetch()
        for rec in recs:
            if rec[1]: # if average reading is Null, skip over partial readings
                dtdate = rec[0]
                dtdate = dt.datetime.strptime(dtdate, "%Y-%m-%d")
                DateCombined.append(dtdate)
                DailyAverageCombined.append(rec[1])
                if rec[2]:
                    CommentDateCombined.append(dtdate)
                    CommentAverageCombined.append(rec[1])
                    CommentCombined.append(rec[2])


    DateCombined = mpd.date2num(DateCombined)
    CommentDateCombined = mpd.date2num(CommentDateCombined)
        
    fig, ax1 = plt.subplots()

    lineTarg = ax1.axhline(y=6, linewidth=4, color='k', label='Glucose Target Range')
    ax1.axhline(y=9, linewidth=4, color='k')

    background = 0.30
    
    lineCombined, = ax1.plot_date(DateCombined, DailyAverageCombined, label='Daily Blood Glucose', linestyle='-', linewidth=1, color='r', marker=None, tz=pst) #


    ax1.yaxis.grid(True, linewidth=1)

    for i in range(len(CommentDateCombined)):
        text = f'<---{(CommentCombined[i], CommentDateCombined[i])}'
        text = f'<---{CommentCombined[i]}'
        #return pprint.pformat((text, CommentDateCombined[i], CommentAverageCombined[i]))
        ax1.annotate(text, (CommentDateCombined[i], CommentAverageCombined[i]), fontsize=12, color='b') #, rotation=0, , weight='bold'

    DateRange = np.concatenate((DateCombined,))
    minDate = min(DateRange)
    maxDate = max(DateRange)
    ax1.set_xlim(minDate, maxDate)
 
    df = mpl.dates.DateFormatter('%b-%d', tz=pst)
    ax1.xaxis.set_major_formatter(df)
    ax1.tick_params(which='major', width=2.0, length=4.0) #, labelsize=10)
    xlocator = mpl.dates.DayLocator(tz=pst)
    ax1.xaxis.set_minor_locator(xlocator)

    plt.gcf().autofmt_xdate()


    z = np.polyfit(DateCombined, DailyAverageCombined, 2)
    # z = np.polynomial.chebyshev.chebfit(DateCombined, DailyAverageCombined, 2)
    p = np.poly1d(z)
    trendLine, = ax1.plot_date(DateCombined, p(DateCombined), 'k--', label='Trend Line')

    ax1.legend(handles=[lineCombined, trendLine, lineTarg], loc='upper right') # , loc='lower right' 'best'

    plt.title('Average Daily Blood Glucose (Jardiance Trial)', loc='left')
    plt.title('William Trenker')
    #
    naivenow = dt.datetime.now()
    now = zuluawarenow = pst.localize(naivenow)   #zulu.localize(naivenow)
    # now = pstawarenow = zuluawarenow.astimezone(pst)
    #fmt = "%Y-%m-%d %I:%M:%S%p"
    ymd = now.strftime('%Y-%m-%d')
    hour = now.strftime('%I')
    if hour[0] == '0':   hour = hour[1]
    minsec = now.strftime('%M:%S')
    ampm = now.strftime('%p').replace('AM', 'am').replace('PM', 'pm')
    zone = now.strftime('%Z')
    now = f"{ymd} {hour}:{minsec}{ampm} {zone}"
    dbNow = f'({dbFileName}) {now}'
    plt.title(dbNow, fontsize=10, loc='right')
    #
    ax1.set_xlabel('Date')  # Note that this won't work on plt or ax2
    ax1.set_ylabel('Blood Glucose (mmol/L)')

    fig.set_size_inches(16, 8.5)
    # fig.tight_layout()

    img = BytesIO()
    fig.savefig(img)
    img.seek(0)
    return send_file(img, mimetype='image/png')

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
            with db_session:
                numberOfHeldReadings = len(Readings.select(lambda c: c.hold is not None))
            log(f'signin: numberOfHeldReadings = {numberOfHeldReadings}')
            jinjadict.update(dict(numberOfHeldReadings=numberOfHeldReadings))
            # return render_template('Admin.jinja2', **jinjadict)
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
    if not(fsl.getSession('signedin')):
        log(f'admin: redirect(url_for("signin")')
        return redirect(url_for('signin'))
    flash(dbPath)
    with db_session:
        numberOfHeldReadings = len(Readings.select(lambda c: c.hold is not None))
    log(f'admin: numberOfHeldReadings = {numberOfHeldReadings}')
    if numberOfHeldReadings == 0:
        flash('There are no partial readings.')
    elif numberOfHeldReadings == 1:
        flash('There is one partial reading.')
    else:
        flash(f'There are {numberOfHeldReadings} partial readings.')
    log(f'admin: render_template("Admin.jinja2")')
    fsl.putSession('numberOfHeldReadings', numberOfHeldReadings)
    return render_template('Admin.jinja2', **jinjadict)
    # return redirect(url_for('admin'))

@app.route("/enter", methods=['GET', 'POST'])
def enter():

    log(f'enter() {request.method}')
    log(f'enter: isLoggedIn = {fsl.getSession("signedin")}')

    flash(dbPath)

    if request.method == 'GET':
        if not (fsl.getSession('signedin')):
            return redirect(url_for('signin'))
        form = DataEntryForm(request.form)
        jinjadict.update(dict(form=form))
        rv = render_template('EnterReading.jinja2', **jinjadict)
        return rv

    elif request.method == 'POST':
        form = DataEntryForm(request.form)
        reqdate = request.form['ddate']
        comment = request.form['annotation']
        morning = request.form['amreading']
        evening = request.form['pmreading']
        if evening == '':
            average = None
            hold = morning
        else:
            average = decimalAverage(morning, evening)
            hold = None
        try:
            with db_session:
                Readings(date=reqdate, average=average, comment=comment, hold=hold)
        except Exception as e:
            e = str(e)
            if e.find('UNIQUE constraint failed') > -1:
                flash('ERROR: That date is already entered.')
            else:
                flash(f'ERROR: {e}')
        with db_session:
            numberOfHeldReadings = len(Readings.select(lambda c: c.hold is not None))
        return render_template('Admin.jinja2', **jinjadict)
        # rv = redirect(url_for('admin'))
        # # rv = jsonify(rv)
        # return rv

    else:
        return "fall through"

@app.route("/selectReading", methods=['GET'])
def selectReading():

    if not fsl.getSession('signedin'):
        return redirect(url_for('signin'))

    flash(dbPath)

    form = SelectReadingForm(request.form)
    jinjadict.update(dict(form=form))
    with db_session:
        heldReadings = Readings.select(lambda c: c.hold is not None).order_by(1)
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
    hr = heldReading(WorkingDate, reading.hold, reading.comment)
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
    evening = form.data['pmreading']
    if evening is None:
        return render_template('NoEvening.jinja2', **jinjadict)
    assert WorkingDate is not None
    with db_session:
        reading = Readings[WorkingDate]
        morning = reading.hold
        reading.hold = None
        reading.average = decimalAverage(morning, evening)
        reading.comment = form.data['annotation']
    return redirect(url_for('admin'))


if __name__ == '__main__':
    port = 5000
    app.run(host='wtrenker.com', port=port, debug=True, use_reloader=False)
# use_reloader=False is the key to getting multi-threaded debug working in PyCharm
