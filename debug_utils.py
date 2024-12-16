DBG = True
DBG_INIT = True
DBG_LAYOUT = True
DBG_TREE = True
DBG_CMD_EDITOR = True
DBG_MACRO = True
DBG_STICKY = True
DBG_STACK = True
DBG_PANEL = True
DBG_PM = True
DBG_PROP = True
DBG_PROP_PATH = True


def _log(color, *args):
    msg = ""
    for arg in args:
        if msg:
            msg += ", "
        msg += str(arg)
    print(color + msg + '\033[0m')


def logi(*args):
    _log('\033[34m', *args)


def loge(*args):
    _log('\033[31m', *args)


def logh(msg):
    _log('\033[1;32m', "")
    _log('\033[1;32m', msg)


def logw(*args):
    _log('\033[33m', *args)
