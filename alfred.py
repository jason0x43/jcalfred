#!/usr/bin/python
# coding=UTF-8

import logging
import plistlib
import os.path
import json
import uuid
from logging import handlers
from sys import stdout
from xml.sax.saxutils import escape


BUNDLE_INFO = plistlib.readPlist('info.plist')
BUNDLE_ID = BUNDLE_INFO['bundleid']
CACHE_DIR = os.path.expanduser('~/Library/Caches'
                               '/com.runningwithcrayons.Alfred-2'
                               '/Workflow Data/{}'.format(BUNDLE_ID))
DATA_DIR = os.path.expanduser('~/Library/Application Support/Alfred 2'
                              '/Workflow Data/{}'.format(BUNDLE_ID))
LINE = unichr(0x2500) * 20

LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(name)s: %(message)s'
LOG = logging.getLogger(__name__)


def _check_dir_writeable(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        if not os.access(path, os.W_OK):
            raise IOError('No write access to {}'.format(path))


class Item(object):
    '''An item in an Alfred feedback XML message'''
    def __init__(self, title, subtitle=None, uid=None, icon=None, valid=False,
                 arg=None):
        self.title = title
        self.subtitle = subtitle
        self.icon = icon if icon is not None else 'icon.png'
        self.uid = uid
        self.valid = valid
        self.arg = arg

    def to_xml(self):
        attrs = []

        if self.uid:
            attrs.append(u'uid="{}-{}"'.format(BUNDLE_ID, self.uid))
        else:
            attrs.append(u'uid="{}"'.format(uuid.uuid4()))

        if self.valid:
            attrs.append('valid="yes"')
        else:
            attrs.append('valid="no"')

        if self.arg is not None:
            attrs.append(u'arg="{}"'.format(self.arg))

        xml = [u'<item {}>'.format(u' '.join(attrs))]

        title = escape(self.title)
        xml.append(u'<title>{}</title>'.format(title))

        if self.subtitle is not None:
            subtitle = escape(self.subtitle)
            xml.append(u'<subtitle>{}</subtitle>'.format(subtitle))
        if self.icon is not None:
            if isinstance(self.icon, dict):
                xml.append(u'<icon type="{}">{}</icon>'.format(
                    self.icon['type'], self.icon['path']))
            else:
                xml.append(u'<icon>{}</icon>'.format(self.icon))

        xml.append(u'</item>')
        return ''.join(xml)

    def __str__(self):
        return '{{Item: title="{}", valid={}, arg="{}"}}'.format(
            self.title.encode('utf-8'), self.valid, self.arg)

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return self.__str__()


class AlfredWorkflow(object):
    def __init__(self):
        conf = {}
        if os.path.exists('config.json'):
            with open('config.json', 'rt') as cfile:
                conf = json.load(cfile)

        self.log_level = conf.get('loglevel', 'INFO')
        logging.getLogger().setLevel(getattr(logging, self.log_level))

        log_file = os.path.join(self.cache_dir, 'debug.log')
        handler = handlers.TimedRotatingFileHandler(
            log_file, when='H', interval=1, backupCount=1)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(handler)

    def save_config(self):
        config = {'loglevel': self.log_level}
        with open('config.json', 'wt') as cfile:
            json.dump(config, cfile)

    @property
    def bundle_id(self):
        return BUNDLE_ID

    @property
    def data_dir(self):
        _check_dir_writeable(DATA_DIR)
        return DATA_DIR

    @property
    def cache_dir(self):
        _check_dir_writeable(CACHE_DIR)
        return CACHE_DIR

    def puts(self, msg):
        '''Output a string.'''
        stdout.write(msg.encode('utf-8'))

    def tell(self, name, query=''):
        '''Tell something.'''
        LOG.debug('tell({}, {})'.format(name, query))
        try:
            cmd = 'tell_{}'.format(name)
            if getattr(self, cmd):
                items = getattr(self, cmd)(query)
            else:
                items = [Item('Invalid action "{}"'.format(name))]
        except Exception, e:
            LOG.exception('Error telling')
            items = [Item('Error: {}'.format(e))]
        self.puts(to_xml(items))

    def do(self, name, query=''):
        '''Do something.'''
        try:
            cmd = 'do_{}'.format(name)
            if getattr(self, cmd):
                getattr(self, cmd)(query)
            else:
                self.puts('Invalid command "{}"'.format(name))
        except Exception, e:
            LOG.exception('Error showing')
            self.puts('Error: {}'.format(e))


def fuzzy_match(test, text):
    '''Return true if the given text fuzzy matches the test'''
    start = 0
    test = test.lower()
    text = text.lower()
    for c in test:
        i = text.find(c, start)
        if i == -1:
            return False
        start = i + 1
    return True


def fuzzy_match_list(test, items, key=None):
    '''Return the subset of items that fuzzy match a string [test]'''
    matches = []
    for item in items:
        if key:
            istr = key(item)
        else:
            istr = str(item)

        if fuzzy_match(test, istr):
            matches.append(item)
    return matches


def to_xml(items):
    '''Convert a list of Items to an Alfred XML feedback message'''
    msg = [u'<?xml version="1.0"?>', u'<items>']

    for item in items:
        msg.append(item.to_xml())

    msg.append(u'</items>')
    return u''.join(msg)


def run_script(script):
    '''Run an AppleScript, returning its output'''
    from subprocess import Popen, PIPE
    p = Popen(['osascript', '-ss', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(script)
    return stdout.decode('utf-8'), stderr.decode('utf-8')


def get_from_user(title, prompt, hidden=False, value=None, extra_buttons=None):
    '''Popup a dialog to request some piece of information.

    The main use for this function is to request information that you don't
    want showing up in Alfred's command history.
    '''
    if value is None:
        value = ''

    buttons = ['Cancel', 'Ok']
    if extra_buttons:
        if isinstance(extra_buttons, (list, tuple)):
            buttons = extra_buttons + buttons
        else:
            buttons.insert(0, extra_buttons)
    buttons = '{{{}}}'.format(', '.join(['"{}"'.format(b) for b in buttons]))

    hidden = 'with hidden answer' if hidden else ''

    script = '''
        on run argv
          tell application "Alfred 2"
              activate
              set alfredPath to (path to application "Alfred 2")
              set alfredIcon to path to resource "appicon.icns" in bundle ¬
                (alfredPath as alias)

              try
                display dialog "{p}:" with title "{t}" default answer "{v}" ¬
                  buttons {b} default button "Ok" with icon alfredIcon {h}
                set answer to (button returned of result) & "|" & ¬
                  (text returned of result)
              on error number -128
                set answer to "Cancel|"
              end
          end tell
        end run'''.format(v=value, p=prompt, t=title, h=hidden, b=buttons)

    from subprocess import Popen, PIPE
    p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(script)
    response = stdout.decode('utf-8').rstrip('\n')
    button, sep, value = response.partition('|')
    return (button, value)


def get_confirmation(title, prompt, default='No'):
    '''Display a confirmation dialog'''
    script = '''
        on run argv
          tell application "Alfred 2"
              activate
              set alfredPath to (path to application "Alfred 2")
              set alfredIcon to path to resource "appicon.icns" in bundle ¬
                (alfredPath as alias)

              try
                display dialog "{p}" with title "{t}"  ¬
                  buttons {{"Yes", "No"}} default button "{d}" ¬
                  with icon alfredIcon
                set answer to (button returned of result)
              on error number -128
                set answer to "No"
              end
          end tell
        end run'''.format(p=prompt, t=title, d=default)

    from subprocess import Popen, PIPE
    p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(script)
    return stdout.decode('utf-8').rstrip('\n')


def show_message(title, message):
    '''Display a message dialog'''
    script = '''
        on run argv
          tell application "Alfred 2"
              activate
              set alfredPath to (path to application "Alfred 2")
              set alfredIcon to path to resource "appicon.icns" in bundle ¬
                (alfredPath as alias)

              display dialog "{m}" with title "{t}" buttons ¬
                {{"Ok"}} default button "Ok" with icon alfredIcon
          end tell
        end run'''.format(t=title, m=message)

    from subprocess import Popen, PIPE
    p = Popen(['osascript', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.communicate(script)


if __name__ == '__main__':
    from sys import argv
    globals()[argv[1]](*argv[2:])
