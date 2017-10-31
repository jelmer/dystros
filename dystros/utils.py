#!/usr/bin/python
#
# Dystros
# Copyright (C) 2016 Jelmer Vernooij <jelmer@jelmer.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import argparse

from defusedxml.ElementTree import fromstring as xmlparse
# Hmm, defusedxml doesn't have XML generation functions? :(
from xml.etree import ElementTree as ET

import datetime
from icalendar.cal import Calendar
from icalendar.prop import vDDDTypes
import optparse
import os
import urllib.parse
import urllib.request

from dystros import caldav
from dystros.config import GetConfig

def install_opener():
    auth_handler = urllib.request.HTTPBasicAuthHandler()
    config = GetConfig()
    if 'password' in config and 'user' in config:
        auth_handler.add_password(realm='data-abundance',
                                  uri=config['base_url'],
                                  user=config['user'],
                                  passwd=config['password'])
    opener = urllib.request.build_opener(auth_handler)
    opener.addheaders = [('User-Agent', 'dystros/calutils')]
    urllib.request.install_opener(opener)

install_opener()

class CalendarOptionGroup(optparse.OptionGroup):
    """Return a optparser OptionGroup.

    :param parser: An OptionParser
    :param default_kind: Default kind
    :return: An OptionGroup
    """

    def __init__(self, parser):
        optparse.OptionGroup.__init__(self, parser, "Calendar Settings")
        config = GetConfig()
        self.add_option('--url', type=str, dest="url", help="Calendar URL.",
                        default=config['default_url'])


def add_calendar_arguments(parser):
    """Add an argument group for calendar options.

    :param parser: An ArgumentParser
    """
    group = parser.add_argument_group("Calendar Settings")
    config = GetConfig()
    group.add_argument('--url', type=str, dest="url", help="Calendar URL.",
                       default=config['default_url'])


def statuschar(evstatus):
    """Convert an event status to a single status character.

    :param evstatus: Event status description
    :return: A single character, empty string if the status is unknown
    """
    return {'TENTATIVE': '?',
            'CONFIRMED': '.',
            'CANCELLED': '-'}.get(evstatus, '')


def format_month(dt):
    return dt.strftime("%b")


def format_daterange(start, end):
    if end is None:
        return "%d %s-?" % (start.day, format_month(start))
    if start.month == end.month:
        if start.day == end.day:
            return "%d %s" % (start.day, format_month(start))
        return "%d-%d %s" % (start.day, end.day, format_month(start))
    return "%d %s-%d %s" % (start.day, format_month(start), end.day, format_month(end))


def asdate(dt):
    if getattr(dt, "date", None):
        a_date = dt.date()
    else:
        a_date = dt
    return dt


def keyEvent(a):
    """Create key for an event

    :param a: First event
    """
    a = a['DTSTART'].dt
    if getattr(a, "date", None):
        a_date = a.date()
        a = (a.hour, a.minute)
    else:
        a_date = a
        a = (0, 0)
    return (a_date, a)


DEFAULT_PRIORITY = 10
DEFAULT_DUE_DATE = datetime.date(datetime.MAXYEAR, 1, 1)


def keyTodo(a):
    priority = a.get('PRIORITY')
    if priority is not None:
        priority = int(priority)
    else:
        priority = DEFAULT_PRIORITY
    due = a.get('DUE')
    if due:
        if getattr(due.dt, "date", None):
            due_date = due.dt.date()
            due_time = (due.dt.hour, due.dt.minute)
        else:
            due_date = due.dt
            due_time = (0, 0)
    else:
        due_date = DEFAULT_DUE_DATE
        due_time = None
    return (priority, due_date, due_time, a['SUMMARY'])


def get_all_calendars(url, depth=None, filter=None):
    for (href, status, propstat) in caldav.calendar_query(
            url, ['{DAV:}getetag', '{urn:ietf:params:xml:ns:caldav}calendar-data'], filter):
        data = None
        for prop, prop_status in propstat:
            if prop.tag == '{urn:ietf:params:xml:ns:caldav}calendar-data':
                data = prop.text
        assert data is not None, "data missing for %r" % href
        yield href, Calendar.from_ical(data)


def get(url):
    req = urllib.request.Request(url=url, method='GET')
    with urllib.request.urlopen(req) as f:
        assert f.status == 200, f.status
        return (f.get_header('ETag'), f.read())


def put(url, content_type, data, if_match=None):
    req = urllib.request.Request(url=url, data=data, method='PUT')
    if if_match is not None:
        req.add_header('If-Match', ', '.join(if_match))
    req.add_header('Content-Type', content_type)
    with urllib.request.urlopen(req) as f:
        pass
    assert f.status in (201, 204, 200), f.status


def post(url, content_type, data, if_match=None):
    req = urllib.request.Request(url=url, data=data, method='POST')
    if if_match is not None:
        req.add_header('If-Match', ', '.join(if_match))
    req.add_header('Content-Type', content_type)
    with urllib.request.urlopen(req) as f:
        pass
    assert f.status in (201, 204, 200), f.status


def getprop(url, props, depth=None):
    reqxml = ET.Element('{DAV:}propfind')
    propxml = ET.SubElement(reqxml, '{DAV:}prop')
    for prop in props:
        if isinstance(prop, str):
            ET.SubElement(propxml, prop)
        else:
            propxml.append(prop)

    if depth is None:
        depth = '0'
    req = urllib.request.Request(url=url, headers={'Content-Type': 'application/xml'}, data=ET.tostring(reqxml), method='PROPFIND')
    req.add_header('Depth', depth)
    with urllib.request.urlopen(req) as f:
        assert f.status == 207, f.status
        respxml = xmlparse(f.read())
    return caldav.multistat_extract_responses(respxml)


def get_addmember_url(url):
    for (href, href_status, propstat) in getprop(url, ['{DAV:}add-member']):
        if href_status == 'HTTP/1.1 404 Not Found':
            raise KeyError(url)
        for prop, propstatus in propstat:
            if prop.tag == '{DAV:}add-member':
                if propstatus == 'HTTP/1.1 200 OK':
                    return urllib.parse.urljoin(url, list(prop)[0].text)
    raise KeyError(url)


def get_vevent_by_uid(url, uid, depth='1'):
    uidprop = ET.Element('{urn:ietf:params:xml:ns:caldav}calendar-data')
    uidprop.set('name', 'UID')
    dataprop = ET.Element('{urn:ietf:params:xml:ns:caldav}calendar-data')
    ret = caldav.calendar_query(
        url, props=[uidprop, dataprop, '{DAV:}getetag'], depth=depth,
        filter=caldav.comp_filter("VCALENDAR",
            caldav.comp_filter("VEVENT",
                caldav.prop_filter("UID", caldav.text_match(text=uid, collation="i;octet")))))

    for (href, status, propstat) in ret:
        if status == 'HTTP/1.1 404 Not Found':
            raise KeyError(uid)
        etag = None
        data = None
        for prop, prop_status in propstat:
            if prop.tag == '{urn:ietf:params:xml:ns:caldav}calendar-data':
                data = prop.text
            if prop.tag == '{DAV:}getetag':
                etag = prop.text
        assert data is not None, "data missing for %r" % href
        return (href, etag, Calendar.from_ical(data))
    raise KeyError(uid)


def add_member(url, content_type, content):
    """Add a new member to a collection.

    :param url: URL of collection
    :param content_type; Content type of new member
    :param content: Content (as bytes)
    """
    addmember_url = get_addmember_url(url)
    post(addmember_url, content_type, content)
