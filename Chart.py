from flask import Flask, request, Markup, send_file, render_template, session, redirect, flash, url_for, jsonify, Response
from pony.orm import Database, Optional, Required, PrimaryKey, db_session, sql_debug, select
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mpd
import numpy as np
import datetime as dt
from GeneralFunctions import verify_password, decimalAverage
import pytz
from io import BytesIO

# def setup(APP, DB):
#     global app
#     app = APP
#     global db
#     db = DB
#
# print(f'app = {app}')

zulu = pytz.timezone('UTC')
pst = pytz.timezone("America/Vancouver")

def renderChart(Readings, dbFileName):

    DateCombined = []
    CommentDateCombined = []
    DailyAverageCombined = []
    CommentCombined = []
    CommentAverageCombined = []

    dATE = 0
    aM = 1
    pM = 2
    cOMMENT = 3
    aVERAGE = 4

    with db_session:
        qry = select((r.date, r.am, r.pm, r.comment, r.average) for r in Readings).order_by(1)
        # xx = qry.get_sql()
        try:
            recs = qry.fetch()
        except e:
            print(e)
        for rec in recs:
            if rec[aM] is None and rec[pM] is None:  # Use the old method based on the average field
                if rec[aVERAGE]:  # if average reading is Null, skip over partial readings
                    dtdate = rec[dATE]
                    dtdate = dt.datetime.strptime(dtdate, "%Y-%m-%d")
                    DateCombined.append(dtdate)
                    DailyAverageCombined.append(rec[aVERAGE])
                    if rec[cOMMENT]:
                        CommentDateCombined.append(dtdate)
                        CommentAverageCombined.append(rec[aVERAGE])
                        CommentCombined.append(rec[cOMMENT])
            else:  # use the new method based on a computed average
                if rec[pM]:  # if no evening reading, skip over this reading
                    dtdate = rec[dATE]
                    dtdate = dt.datetime.strptime(dtdate, "%Y-%m-%d")
                    DateCombined.append(dtdate)
                    DailyAVerage = float(decimalAverage(rec[aM], rec[pM]))
                    DailyAverageCombined.append(DailyAVerage)
                    if rec[cOMMENT]:
                        CommentDateCombined.append(dtdate)
                        CommentAverageCombined.append(DailyAVerage)
                        CommentCombined.append(rec[cOMMENT])

    DateCombined = mpd.date2num(DateCombined)
    CommentDateCombined = mpd.date2num(CommentDateCombined)

    fig, ax1 = plt.subplots()

    lineTarg = ax1.axhline(y=6, linewidth=4, color='k', label='Glucose Target Range')
    ax1.axhline(y=9, linewidth=4, color='k')

    background = 0.30

    lineCombined, = ax1.plot_date(DateCombined, DailyAverageCombined, label='Daily Blood Glucose', linestyle='-',
                                  linewidth=1, color='r', marker=None, tz=pst)  #

    ax1.yaxis.grid(True, linewidth=1)

    for i in range(len(CommentDateCombined)):
        text = f'<---{(CommentCombined[i], CommentDateCombined[i])}'
        text = f'<---{CommentCombined[i]}'
        # return pprint.pformat((text, CommentDateCombined[i], CommentAverageCombined[i]))
        ax1.annotate(text, (CommentDateCombined[i], CommentAverageCombined[i]), fontsize=12,
                     color='b')  # , rotation=0, , weight='bold'

    DateRange = np.concatenate((DateCombined,))
    minDate = min(DateRange)
    maxDate = max(DateRange)
    ax1.set_xlim(minDate, maxDate)

    df = mpl.dates.DateFormatter('%b-%d', tz=pst)
    ax1.xaxis.set_major_formatter(df)
    ax1.tick_params(which='major', width=2.0, length=4.0)  # , labelsize=10)
    xlocator = mpl.dates.DayLocator(tz=pst)
    ax1.xaxis.set_minor_locator(xlocator)

    plt.gcf().autofmt_xdate()

    z = np.polyfit(DateCombined, DailyAverageCombined, 2)
    # z = np.polynomial.chebyshev.chebfit(DateCombined, DailyAverageCombined, 2)
    p = np.poly1d(z)
    trendLine, = ax1.plot_date(DateCombined, p(DateCombined), 'k--', label='Trend Line')

    # ax1.legend(handles=[lineCombined, trendLine, lineTarg], loc='upper left') # , loc='lower right' 'best'
    ax1.legend(handles=[lineCombined, lineTarg, trendLine], loc='upper right')  #  , loc='lower right' 'best'

    plt.title('Average Daily Blood Glucose (Jardiance Trial)', loc='left')
    plt.title('William Trenker')
    #
    naivenow = dt.datetime.now()
    now = zuluawarenow = pst.localize(naivenow)  # zulu.localize(naivenow)
    # now = pstawarenow = zuluawarenow.astimezone(pst)
    # fmt = "%Y-%m-%d %I:%M:%S%p"
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
    return img
    # return send_file(img, mimetype='image/png')
