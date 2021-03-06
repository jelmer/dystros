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

import urllib.parse
import urllib.request



def report(url, req, depth=None):
    """Send a CalDAV report request.

    :param url: URL to request against.
    :param req: Request as XML element
    :param depth: Optional depth. Defaults to '1'
    :return: Response
    """
    if depth is None:
        depth = '1'
    req = urllib.request.Request(
        url=url, headers={'Content-Type': 'application/xml'},
        data=ET.tostring(req), method='REPORT')
    req.add_header('Depth', depth)
    return urllib.request.urlopen(req)


def expect_tag(element, name):
    # TODO(jelmer)
    if isinstance(name, str):
        assert element.tag == name, "expected tag %s, got %s: %r" % (name, element.tag, element)
    else:
        assert element.tag in name, "expected one of %s, got %s: %r" % (', '.join(name), element.tag, element)


def multistat_extract_responses(multistatus):
    """Extract response from a multistat element.

    :param multistatus: Multistat element
    :return: Iterator over (href, status, propstat) tuples
    """
    expect_tag(multistatus, '{DAV:}multistatus')
    for response in multistatus:
        expect_tag(response, '{DAV:}response')
        href = None
        status = None
        propstat = None
        for responsesub in response:
            expect_tag(responsesub, ('{DAV:}href', '{DAV:}propstat', '{DAV:}status'))
            if responsesub.tag == '{DAV:}href':
                href = responsesub.text
            elif responsesub.tag == '{DAV:}propstat':
                propstat = []
                for propstatsub in responsesub:
                    expect_tag(propstatsub, ('{DAV:}status', '{DAV:}prop'))
                for propstatsub in responsesub:
                    if propstatsub.tag == '{DAV:}status':
                        prop_status = propstatsub.text
                for propstatsub in responsesub:
                    if propstatsub.tag == '{DAV:}prop':
                        for actualprop in propstatsub:
                            propstat.append((actualprop, prop_status))
            elif responsesub.tag == '{DAV:}status':
                status = responsesub.text
        yield (href, status, propstat)


def calendar_query(url, props, filter=None, depth=None):
    """Send a calendar-query request.

    :param url: URL to request against
    :param props: Properties to request (as XML elements or strings
    :param filter: Optional filter to apply
    :param depth: Optional Depth
    :return: Multistat response
    """
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


def freebusy_query(url, start, end, depth=None):
    """Query freebusy information.

    :param start: optional start time
    :param end: Optional end time
    :param depth: Optional depth
    :return: Freebusy results (as string)
    """
    reqxml = ET.Element('{urn:ietf:params:xml:ns:caldav}free-busy-query')
    propxml = ET.SubElement(reqxml, '{urn:ietf:params:xml:ns:caldav}time-range')
    if start is not None:
        propxml.set('start', vDDDTypes(start).to_ical().decode('ascii'))
    if end is not None:
        propxml.set('end', vDDDTypes(end).to_ical().decode('ascii'))
    with caldav.report(url, reqxml, depth) as f:
        assert f.status == 200, f.status
        return f.read()

def _extend_inner_filter(et, inner_filter):
    if inner_filter is None:
        return
    if not isinstance(inner_filter, list):
        inner_filter = [inner_filter]
    for f in inner_filter:
        et.append(f)


def comp_filter(name, inner_filter=None):
    """Create a component filter.

    :param name: Component name to filter on
    :param inner_filter: Optional filter for contents
    :return: A filter
    """
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}comp-filter')
    if name is not None:
        ret.set('name', name)
    _extend_inner_filter(ret, inner_filter)
    return ret


def prop_filter(name, inner_filter=None):
    """Create a property filter.

    :param name: Property name to filter on
    :param inner_filter: Optional filter for contents
    :return: A filter
    """
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}prop-filter')
    if name is not None:
        ret.set('name', name)
    _extend_inner_filter(ret, inner_filter)
    return ret


def text_match(text, collation=None):
    """Match against a specific string.

    :param text: Text to match against
    :param collation: Optional collation
    :return: A filter
    """
    ret = ET.Element('{urn:ietf:params:xml:ns:caldav}text-match')
    ret.text = text
    if collation is not None:
        ret.set('collation', collation)
    return ret


def getprop(url, props, depth=None):
    """Retrieve properties on a URL or set of URLs.

    :param url: URL to query
    :param props: List of properties to retrieve
    :param depth: Optional depth
    :return: See `multistat_extract_responses`
    """
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
    return multistat_extract_responses(respxml)


def get_current_user_principal(url):
    """Get the current user principal path.

    :param url: URL to fetch from
    :return: Current user principal
    """
    for href, href_status, propstat in getprop(url, ['{DAV:}current-user-principal']):
        expect_tag(propstat[0][0], '{DAV:}current-user-principal')
        children = list(propstat[0][0])
        expect_tag(children[0], '{DAV:}href')
        return urllib.parse.urljoin(url, children[0].text)
    raise KeyError
