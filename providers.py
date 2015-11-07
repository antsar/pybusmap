from requests import get
from lxml import etree
import json
from models import Agency, Region, Update
from app import db
from sqlalchemy.exc import IntegrityError

"""
Data sources are defined here.
"""

class Nextbus():
    """
    NextBus Inc. - www.nextbus.com
    API Format: XML
    API Doc: https://www.nextbus.com/xmlFeedDocs/NextBusXMLFeed.pdf
    """

    api_url = "http://webservices.nextbus.com/service/publicXMLFeed"

    @classmethod
    def get_agencies(cls):
        request = {
            'command': 'agencyList',
        }
        response = get(cls.api_url, params=request)
        xmlroot = etree.fromstring(response.content)
        tree = etree.ElementTree(xmlroot)
        agencies = tree.findall('agency')
        for agency in agencies:
            region = Region.get_or_create(db.session, title=agency.get('regionTitle'))
            a = Agency(
                tag = agency.get('tag'),
                title = agency.get('title'),
                short_title = agency.get('shortTitle'),
                region = region)
            try:
                db.session.add(a)
                db.session.flush()
            except IntegrityError as e:
                db.session.rollback()
        db.session.add(Update(dataset="agency"))
        db.session.commit()
