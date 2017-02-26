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


def report(url, req, depth=None):
    if depth is None:
        depth = '1'
    req = urllib.request.Request(url=url, data=ET.tostring(req), method='REPORT')
    req.add_header('Depth', depth)
    return urllib.request.urlopen(req)


def _extend_inner_filter(et, inner_filter):
    if inner_filter is None:
        return
    if not isinstance(inner_filter, list):
        inner_filter = [inner_filter]
    for f in inner_filter:
        et.append(f)


def comp_filter(name, inner_filter=None):
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}comp-filter')
    if name is not None:
        ret.set('name', name)
    _extend_inner_filter(ret, inner_filter)
    return ret


def prop_filter(name, inner_filter=None):
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}prop-filter')
    if name is not None:
        ret.set('name', name)
    _extend_inner_filter(ret, inner_filter)
    return ret


def text_match(text, collation):
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}text-match')
    ret.text = text
    ret.set('collation', collation)
    return ret


def multistat_extract_responses(multistatus):
    assert multistatus.tag == '{DAV:}multistatus', repr(multistatus)
    for response in multistatus:
        assert response.tag == '{DAV:}response'
        href = None
        status = None
        propstat = None
        for responsesub in response:
            if responsesub.tag == '{DAV:}href':
                href = responsesub.text
            elif responsesub.tag == '{DAV:}propstat':
                propstat = responsesub
            elif responsesub.tag == '{DAV:}status':
                status = responsesub.text
            else:
                assert False, 'invalid %r' % responsesub.tag
        yield (href, status, propstat)


def calendar_query(url, props, filter=None, depth=None):
    reqxml = ET.Element('{urn:ietf:params:xml:ns:caldav}calendar-query')
    propxml = ET.SubElement(reqxml, '{DAV:}prop')
    for prop in props:
        if isinstance(prop, str):
            ET.SubElement(propxml, prop)
        else:
            propxml.append(prop)

    if filter is not None:
        filterxml = ET.SubElement(reqxml, '{urn:ietf:params:xml:ns:caldav}filter')
        filterxml.append(filter)

    with report(url, reqxml, depth) as f:
        assert f.status == 207, f.status
        respxml = xmlparse(f.read())
    return multistat_extract_responses(respxml)


def get_all_calendars(url, depth=None, filter=None):
    for (href, status, propstat) in calendar_query(
            url, ['{DAV:}getetag', '{urn:ietf:params:xml:ns:caldav}calendar-data'], filter):
        by_status = {}
        for propstatsub in propstat:
            if propstatsub.tag == '{DAV:}status':
                status = propstatsub.text
            elif propstatsub.tag == '{DAV:}prop':
                by_status[status] = propstatsub
            else:
                assert False, 'invalid %r' % propstatsub.tag
        data = None
        for prop in by_status.get('HTTP/1.1 200 OK', []):
            if prop.tag == '{urn:ietf:params:xml:ns:caldav}calendar-data':
                data = prop.text
        assert data is not None, "data missing for %r" % href
        yield href, Calendar.from_ical(data)


def get(url):
    req = urllib.request.Request(url=url, method='GET')
    with urllib.request.urlopen(req) as f:
        assert f.status == 200, f.status
        return (f.get_header('ETag'), f.read())


def put(url, data, if_match=None):
    req = urllib.request.Request(url=url, data=data, method='PUT')
    if if_match is not None:
        req.add_header('If-None-Match', ', '.join(if_match))
    with urllib.request.urlopen(req) as f:
        pass
    assert f.status in (201, 204, 200), f.status


def post(url, content_type, data, if_match=None):
    req = urllib.request.Request(url=url, data=data, method='POST')
    if if_match is not None:
        req.add_header('If-None-Match', ', '.join(if_match))
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
    req = urllib.request.Request(url=url, data=ET.tostring(reqxml), method='PROPFIND')
    req.add_header('Depth', depth)
    with urllib.request.urlopen(req) as f:
        assert f.status == 207, f.status
        respxml = xmlparse(f.read())
    return multistat_extract_responses(respxml)


def get_addmember_url(url):
    for (href, status, propstat) in getprop(url, ['{DAV:}add-member']):
        if status == 'HTTP/1.1 404 Not Found':
            raise KeyError(url)
        by_status = {}
        for propstatsub in propstat:
            if propstatsub.tag == '{DAV:}status':
                if propstatsub.text == 'HTTP/1.1 404 Not Found':
                    raise KeyError(uid)
            elif propstatsub.tag == '{DAV:}prop':
                by_status[status] = propstatsub
            else:
                assert False, 'invalid %r' % propstatsub.tag
        for prop in by_status.get('HTTP/1.1 200 OK', []):
            if prop.tag == '{DAV:}add-member':
                return urllib.parse.urljoin(url, list(prop)[0].text)
    raise KeyError(url)


def get_vevent_by_uid(url, uid, depth='1'):
    uidprop = ET.Element('{urn:ietf:params:xml:ns:caldav}calendar-data')
    uidprop.set('name', 'UID')
    dataprop = ET.Element('{urn:ietf:params:xml:ns:caldav}calendar-data')
    ret = calendar_query(
        url, props=[uidprop, dataprop, '{DAV:}getetag'], depth=depth,
        filter=comp_filter("VCALENDAR",
            comp_filter("VEVENT",
                prop_filter("UID", text_match(text=uid, collation="i;octet")))))

    for (href, status, propstat) in ret:
        if status == 'HTTP/1.1 404 Not Found':
            raise KeyError(uid)
        by_status = {}
        for propstatsub in propstat:
            if propstatsub.tag == '{DAV:}status':
                if propstatsub.text == 'HTTP/1.1 404 Not Found':
                    raise KeyError(uid)
            elif propstatsub.tag == '{DAV:}prop':
                by_status[status] = propstatsub
            else:
                assert False, 'invalid %r' % propstatsub.tag
        etag = None
        data = None
        for prop in by_status.get('HTTP/1.1 200 OK', []):
            if prop.tag == '{urn:ietf:params:xml:ns:caldav}calendar-data':
                data = prop.text
            if prop.tag == '{DAV:}getetag':
                etag = prop.text
        assert data is not None, "data missing for %r" % href
        return (href, etag, Calendar.from_ical(data))
    raise KeyError(uid)


def get_freebusy(url, start, end, depth=None):
    reqxml = ET.Element('{urn:ietf:params:xml:ns:caldav}free-busy-query')
    propxml = ET.SubElement(reqxml, '{urn:ietf:params:xml:ns:caldav}time-range')
    if start is not None:
        propxml.set('start', vDDDTypes(start).to_ical().decode('ascii'))
    if end is not None:
        propxml.set('end', vDDDTypes(end).to_ical().decode('ascii'))
    with report(url, reqxml, depth) as f:
        assert f.status == 200, f.status
        return f.read()
