from flask import Flask, request, Markup, send_file, render_template
import matplotlib as mpl
mpl.use('Agg')
from pony.orm import Database, Optional, Required, PrimaryKey, db_session, sql_debug, select
import matplotlib.pyplot as plt
import matplotlib.dates as mpd
import numpy as np
from io import BytesIO
import time
import datetime as dt
from pathlib import Path
import json
import pytz
import pprint

dbFileName = "glucose.db"
dbPath = Path(f'/home/bill/glucose2/{dbFileName}')
# dbPath = Path(dbFile)
db = Database()

class Readings(db.Entity):
    date = PrimaryKey(dt.datetime)
    average = Required(float)
    comment = Optional(str)

zulu = pytz.timezone('UTC')
pst = pytz.timezone("America/Vancouver")

db.bind(provider='sqlite', filename=str(dbPath), create_db=False)
db.generate_mapping(create_tables=False)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.jinja2', title='Glucose Chart')

@app.route('/averages')
def averages():
    return render_template('averages.jinja2', title='Blood Glucose Daily Average', req=dir(request), timestamp=time.time())

@app.route('/dataentry')
def dataentry():
    return render_template('dataentry.jinja2', title='Data Entry', req=dir(request), timestamp=time.time())

@app.route(Markup('/chart'))
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
                dtdate = dt.datetime.strptime(rec[0], "%Y-%m-%d")
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
        ax1.annotate(text, (CommentDateCombined[i], CommentAverageCombined[i]), weight='bold', fontsize=12, color='b') #, rotation=0,

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
    p = np.poly1d(z)
    trendLine, = ax1.plot_date(DateCombined, p(DateCombined), 'k--', label='Trend Line')

    ax1.legend(handles=[lineCombined, trendLine, lineTarg], loc='upper left') # , loc='lower right' 'best'

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

if __name__ == '__main__':
   app.run(host='localhost', port=9000, debug = True)
