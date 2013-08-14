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


LINE = unichr(0x2500) * 20
LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(name)s: %(message)s'
LOG = logging.getLogger(__name__)


def _check_dir_writeable(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        if not os.access(path, os.W_OK):
            raise IOError('No write access to %s' % path)


class Item(object):
    '''An item in an Alfred feedback XML message'''
    def __init__(self, title, subtitle=None, icon=None, valid=False, arg=None,
                 uid=None, random_uid=True):
        self.title = title
        self.subtitle = subtitle
        self.icon = icon if icon is not None else 'icon.png'
        self.uid = uid
        self.valid = valid
        self.arg = arg
        self.random_uid = random_uid

    def to_xml(self):
        attrs = []

        if self.random_uid:
            attrs.append(u'uid="%s"' % uuid.uuid4())
        elif self.uid:
            attrs.append(u'uid="%s"' % self.uid)

        if self.valid:
            attrs.append('valid="yes"')
        else:
            attrs.append('valid="no"')

        if self.arg is not None:
            attrs.append(u'arg="%s"' % self.arg)

        xml = [u'<item %s>' % (u' '.join(attrs))]

        title = escape(self.title)
        xml.append(u'<title>%s</title>' % title)

        if self.subtitle is not None:
            subtitle = escape(self.subtitle)
            xml.append(u'<subtitle>%s</subtitle>' % subtitle)
        if self.icon is not None:
            if isinstance(self.icon, dict):
                xml.append(u'<icon type="%s">%s</icon>' % (
                    self.icon['type'], self.icon['path']))
            else:
                xml.append(u'<icon>%s</icon>' % self.icon)

        xml.append(u'</item>')
        return ''.join(xml)

    def __str__(self):
        return '{{Item: title="%s", valid=%s, arg="%s"}}' % (
            self.title.encode('utf-8'), self.valid, self.arg)

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return self.__str__()


class AlfredWorkflow(object):
    def __init__(self):
        self._bundle_info = plistlib.readPlist('info.plist')
        self._bundle_id = self._bundle_info['bundleid']
        self._cache_dir = os.path.expanduser(
            '~/Library/Caches/com.runningwithcrayons.Alfred-2'
            '/Workflow Data/%s' % self._bundle_id)
        self._data_dir = os.path.expanduser(
            '~/Library/Application Support/Alfred 2/Workflow Data/%s' %
            self._bundle_id)

        conf = {}
        if os.path.exists('config.json'):
            with open('config.json', 'rt') as cfile:
                conf = json.load(cfile)

        self.log_level = conf.get('loglevel', 'INFO')
        log_file = os.path.join(self.cache_dir, 'debug.log')
        handler = handlers.TimedRotatingFileHandler(
            log_file, when='H', interval=1, backupCount=1)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.getLogger().addHandler(handler)

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, level):
        self._log_level = level
        logging.getLogger().setLevel(getattr(logging, level))

    def save_config(self):
        config = {'loglevel': self.log_level}
        with open('config.json', 'wt') as cfile:
            json.dump(config, cfile, indent=2)

    @property
    def bundle_info(self):
        return self._bundle_info

    @property
    def bundle_id(self):
        return self._bundle_id

    @property
    def data_dir(self):
        _check_dir_writeable(self._data_dir)
        return self._data_dir

    @property
    def cache_dir(self):
        _check_dir_writeable(self._cache_dir)
        return self._cache_dir

    def puts(self, msg):
        '''Output a string.'''
        stdout.write(msg.encode('utf-8'))

    def fuzzy_match(self, test, text):
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

    def fuzzy_match_list(self, test, items, key=None):
        '''Return the subset of items that fuzzy match a string [test]'''
        matches = []
        for item in items:
            if key:
                istr = key(item)
            else:
                istr = str(item)

            if self.fuzzy_match(test, istr):
                matches.append(item)
        return matches

    def to_xml(self, items):
        '''Convert a list of Items to an Alfred XML feedback message'''
        msg = [u'<?xml version="1.0"?>', u'<items>']

        for item in items:
            msg.append(item.to_xml())

        msg.append(u'</items>')
        return u''.join(msg)

    def run_script(self, script):
        '''Run an AppleScript, returning its output'''
        from subprocess import Popen, PIPE
        p = Popen(['osascript', '-ss', '-'], stdin=PIPE, stdout=PIPE,
                  stderr=PIPE)
        stdout, stderr = p.communicate(script)
        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def get_from_user(self, title, prompt, hidden=False, value=None,
                      extra_buttons=None):
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
        buttons = '{%s}' % ', '.join(['"%s"' % b for b in buttons])

        hidden = 'with hidden answer' if hidden else ''

        script = '''
            on run argv
              tell application "Alfred 2"
                  activate
                  set alfredPath to (path to application "Alfred 2")
                  set alfredIcon to path to resource "appicon.icns" in bundle ¬
                    (alfredPath as alias)

                  try
                    display dialog "{p}:" with title "{t}" ¬
                      default answer "{v}" ¬
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

    def get_confirmation(self, title, prompt, default='No'):
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

    def show_message(self, title, message):
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

    def tell(self, name, query=''):
        '''Tell something.'''
        LOG.debug('tell(%s, %s)', name, query)
        try:
            cmd = 'tell_%s' % name
            if getattr(self, cmd):
                items = getattr(self, cmd)(query)
            else:
                items = [Item('Invalid action "%s"' % name)]
        except Exception, e:
            LOG.exception('Error telling')
            items = [Item('Error: %s' % e)]
        self.puts(self.to_xml(items))

    def do(self, name, query=''):
        '''Do something.'''
        try:
            cmd = 'do_%s' % name
            if getattr(self, cmd):
                getattr(self, cmd)(query)
            else:
                self.puts('Invalid command "%s"' % name)
        except Exception, e:
            LOG.exception('Error showing')
            self.puts('Error: %s' % e)


if __name__ == '__main__':
    from sys import argv
    globals()[argv[1]](*argv[2:])
