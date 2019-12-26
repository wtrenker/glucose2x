from pony.orm import Database, Optional, Required, PrimaryKey, db_session, sql_debug, select
# from pathlib import Path
import json
import pprint

db = Database()

class SessionInfo(db.Entity):
    name = PrimaryKey(str)
    value = Optional(str)

db.bind(provider='sqlite', filename='db/SessionLog.db', create_db=False)
db.generate_mapping(create_tables=False)

def _getjasonobj(objtype):
    assert objtype in ['log', 'session']
    with db_session:
        infojson = SessionInfo[objtype]
    valuestr = infojson.value
    if valuestr is None or valuestr == '':
        return ''
    valuestr = json.loads(valuestr)
    return valuestr

def _exists(objtype):
    assert objtype in ['log', 'session']
    rv = _getjasonobj(objtype)
    return rv and rv != ''

def initSession():
    with db_session:
        objsess = SessionInfo['session']
        objsess.value = json.dumps({})

def initLog():
    with db_session:
        objsess = SessionInfo['log']
        objsess.value = json.dumps([])

def getSession(name):
    pydict = _getjasonobj('session')
    if pydict == '':
        return None
    return pydict.get(name)

def getContainer(objtype):
    assert objtype in ['log', 'session']
    pyContainer = _getjasonobj(objtype)
    return pyContainer

def putContainer(objtype, value):
    assert objtype in ['log', 'session']
    container = getContainer(objtype)
    value = json.dumps(value)
    if objtype == 'session':
        container.update(value)
    else:
        container.append(value)

def putSession(name, value):
    dbdict = getContainer('session')
    dbdict = dbdict if dbdict is not None and dbdict != '' else {}
    dbdict.update({name:value})
    jsondict = json.dumps(dbdict)
    with db_session:
        sessjson = SessionInfo['session']
        sessjson.value = jsondict
sess = putSession

def putLog(line):
    dblist = getContainer('log')
    dblist = dblist if dblist is not None and dblist != '' else []
    dblist.append(line)
    jsonlist = json.dumps(dblist)
    with db_session:
        sessjson = SessionInfo['log']
        sessjson.value = jsonlist
log = putLog

def getCode():
    with db_session:
        codeobj = SessionInfo['code']
    codesstr = codeobj.value
    if codesstr is None or codesstr == '':
        return ''
    return codesstr

def containerExists(objtype):
    assert objtype in ['log', 'session']
    try:
        rv = _getjasonobj(objtype)
    except:
        rv = None
    return rv is not None and rv != ''

def rem(name):
    pass

def dumplog():
    print('-----==--- db log -----------')
    logdict = getContainer('log')
    if not logdict:
        print('empty log')
    else:
        for logline in logdict:
            print(logline)
    print('------- end of db log --------')

if __name__ == '__main__':
    initLog()
    log('Ths is line 1')
    log('Ths is line 2')
    log('Ths is line 3')
    dumplog()

    initSession()
    # sess('name', 'me')
    # sess('stuff', 34567)
    #
    # val = _getjasonobj('code')
    # print(val)
