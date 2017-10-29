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
                propstat = responsesub
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
