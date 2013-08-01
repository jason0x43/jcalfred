#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Access the Mac OS X keychain.

This script was inspired by Stever Webster's keychain.py (https://github.com/
spjwebster/keychain.py), which was originally based on Stuart Colville's
Keychain.py. It's has fewer features than either of the others, but I didn't
really need to do much other than get and set passwords.
'''

import sys
from subprocess import check_output, call, CalledProcessError, STDOUT


SERVICE_NAME = 'jalf'


TAG_NAMES = {
    '0x00000007': 'name',
    'svce': 'service',
    'acct': 'account',
    'icmt': 'comment',
}


if sys.platform != 'darwin':
    raise Exception('This library only works on Mac OS X')


def _parse_keychain_item(lines):
    '''Parse a keychain item.'''
    item = {}
    for line in lines:
        if line.startswith('password: '):
            ipass = line[10:].strip().strip('"')
            item['password'] = ipass
        elif line.startswith(' '):
            line = line.strip()
            if line.startswith('0'):
                tag, sep, val = line.partition(' ')
                vtype, sep, val = val.partition('=')
            else:
                tag, sep, val = line.partition('<')
                tag = tag.strip('"')
                vtype, sep, val = val.partition('=')

            if val == '<NULL>':
                continue

            if tag in TAG_NAMES:
                item[TAG_NAMES[tag]] = val.strip('"')
    return item


def get_item(account, service=SERVICE_NAME):
    '''Retrieve a keychain item.

    account   the account password to get
    service   (optional) service name for the password
    '''
    cmd = ['security', 'find-generic-password', '-g', '-a', account, '-s',
           service]

    try:
        out = check_output(cmd, stderr=STDOUT)
        item = _parse_keychain_item(out.split('\n'))
        return item
    except CalledProcessError:
        return None


def set_item(account, password, comment=None, service=SERVICE_NAME):
    '''Add or update a keychain item.

    account    the name of the account the password is for (e.g., plugin name)
    password   the password value
    comment    (optional) text to be stored with password
    service    (optional) the service the password is for
    '''
    label = '{}.{}'.format(service, account)
    cmd = ['security', 'add-generic-password', '-w', password, '-a', account,
           '-s', service, '-U', '-l', label]
    if comment:
        cmd += ['-j', comment]

    try:
        call(cmd)
    except CalledProcessError:
        return None


def del_item(account, service=SERVICE_NAME):
    '''Delete a keychain item.

    account    the name of the account the password is for (e.g., plugin name)
    service    (optional) the service the password is for
    '''
    cmd = ['security', 'delete-generic-password', '-a', account, '-s', service]
    check_output(cmd, stderr=STDOUT)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('get', 'set', 'del'))
    parser.add_argument('account')
    args = parser.parse_args()

    if args.command == 'get':
        print get_item(args.account)
    elif args.command == 'set':
        from getpass import getpass
        passwd = getpass('Password: ')
        set_item(args.account, passwd)
    elif args.command == 'del':
        del_item(args.account)
