#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class for sending some very basic commands to Icinga 2.x
monitoring systems.
"""

import logging
import requests
from urlparse import urlparse
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta



class Icinga2APIClient:
    """
.. class:: Icinga2APIClient
    """
    HEADERS = {
        'User-Agent': 'katprep (https://github.com/stdevel/katprep)',
        'Accept': 'application/json',
        'Content-Type': "application/json"
    }
    """
    dict: Default headers set for every HTTP request
    """
    SESSION = None
    """
    session: API session
    """
    LOGGER = logging.getLogger('Icinga2APIClient')
    """
    logging: Logger instance
    """
    VERIFY_SSL = False
    """
    bool: Setting whether to check SSL certificate
    """

    def __init__(self, url, username="", password="", verify_ssl=False):
        """
        Constructor, creating the class. It requires specifying a
        URL, an username and password to access the API.

        :param url: Icinga URL
        :type url: str
        :param username: API username
        :type username: str
        :param password: corresponding password
        :type password: str
        """
        #set logging
        self.LOGGER.setLevel(logging.ERROR)

        #set connection data
        if "/v1" in url:
            self.URL = url
        else:
            self.URL = "{}/v1".format(url)
        self.USERNAME = username
        self.PASSWORD = password

        #set SSL information and connect
        if verify_ssl:
            self.VERIFY_SSL = True
        self.__connect()



    def __connect(self):
        """
        This function establishes a connection to the Icinga2 API.
        """
        self.SESSION = requests.Session()
        if self.USERNAME != "":
            self.SESSION.auth = HTTPBasicAuth(self.USERNAME, self.PASSWORD)



    def __api_request(self, method, sub_url, payload=""):
        """
        Sends a HTTP request to the Nagios/Icinga API. This function requires
        a valid HTTP method and a sub-URL (such as /cgi-bin/status.cgi).
        Optionally, you can also specify payload (for POST).
        There are also alias functions available.

        :param method: HTTP request method (GET, POST)
        :type method: str
        :param sub_url: relative path (e.g. /cgi-bin/status.cgi)
        :type sub_url: str
        :param payload: payload for POST requests
        :type payload: str
        """
        #send request to API
        try:
            if method.lower() not in ["get", "post"]:
                #going home
                raise ValueError("Illegal method '{}' specified".format(method))

            #execute request
            if method.lower() == "post":
                #POST
                result = self.SESSION.post(
                    "{}{}".format(self.URL, sub_url),
                    headers=self.HEADERS, data=payload, verify=self.VERIFY_SSL
                    )
            else:
                #GET
                result = self.SESSION.get(
                    "{}{}".format(self.URL, sub_url),
                    headers=self.HEADERS, verify=self.VERIFY_SSL
                    )

            if result.status_code != 200:
                raise ValueError("{}: HTTP operation not successful".format(
                    result.status_code))
            else:
                #return result
                if method.lower() == "get":
                    return result.text
                else:
                    return True

        except ValueError as err:
            self.LOGGER.error(err)
            raise

    #Aliases
    def __api_get(self, sub_url):
        """
        Sends a HTTP GET request to the Nagios/Icinga API. This function
        requires a sub-URL (such as /cgi-bin/status.cgi).

        :param sub_url: relative path (e.g. /cgi-bin/status.cgi)
        :type sub_url: str
        """
        return self.__api_request("get", sub_url)

    def __api_post(self, sub_url, payload):
        """
        Sends a HTTP POST request to the Nagios/Icinga API. This function
        requires a sub-URL (such as /cgi-bin/status.cgi).

        :param sub_url: relative path (e.g. /cgi-bin/status.cgi)
        :type sub_url: str
        :param payload: payload data
        :type payload: str
        """
        return self.__api_request("post", sub_url, payload)



    def __calculate_time(self, hours):
        """
        Calculates the time range for POST requests in the format the
        Icinga 2.x API requires. For this, the current time/date
        is chosen and the specified amount of hours is added.

        :param hours: Amount of hours for the time range
        :type hours: int
        """
        current_time = time.strftime("%s")
        end_time = format(
            datetime.now() + timedelta(hours=int(hours)),
            '%s')
        return (current_time, end_time)



    def __manage_downtime(
            self, object_name, object_type, hours, comment, remove_downtime
        ):
        """
        Adds or removes scheduled downtime for a host or hostgroup.
        For this, a object name and type are required.
        You can also specify a comment and downtime period.

        :param object_name: Hostname or hostgroup name
        :type object_name: str
        :param object_type: host or hostgroup
        :type object_type: str
        :param hours: Amount of hours for the downtime
        :type hours: int
        :param comment: Downtime comment
        :type comment: str
        :param remove_downtime: Removes a previously scheduled downtime
        :type remove_downtime: bool
        """
        #calculate timerange
        (current_time, end_time) = self.__calculate_time(hours)

        if object_type.lower() == "hostgroup":
            if remove_downtime:
                #remove hostgroup downtime
                payload = {
                    "type": "foobar",
                    "filter": "\"{}\" in host.groups".format(object_name),
                }
            else:
                #create hostgroup downtime
                payload = {
                    "type": "foobar",
                    "filter": "\"{}\" in host.groups".format(object_name),
                    "start_time": int(current_time),
                    "end_time": int(end_time),
                    "fixed": True,
                    "author": self.USERNAME,
                    "comment": comment,
                }
        else:
            if remove_downtime:
                #remove host downtime
                payload = {
                    "type": "foobar",
                    "filter": "host.name==\"{}\"".format(object_name),
                }
            else:
                #create host downtime
                payload = {
                    "type": "foobar",
                    "filter": "host.name==\"{}\"".format(object_name),
                    "start_time": int(current_time),
                    "end_time": int(end_time),
                    "fixed": True,
                    "author": self.USERNAME,
                    "comment": comment,
                }
        #send POST
        if remove_downtime:
            payload["type"] = "Host"
            self.__api_post("/actions/remove-downtime", json.dumps(payload))
            payload["type"] = "Service"
            return self.__api_post("/actions/remove-downtime", json.dumps(payload))
        else:
            payload["type"] = "Host"
            self.__api_post("/actions/schedule-downtime", json.dumps(payload))
            payload["type"] = "Service"
            return self.__api_post("/actions/schedule-downtime", json.dumps(payload))



    def schedule_downtime(self, object_name, object_type, hours=8, \
        comment="Downtime managed by katprep"):
        """
        Adds scheduled downtime for a host or hostgroup.
        For this, a object name and type are required.
        Optionally, you can specify a customized comment and downtime
        period (the default is 8 hours).

        :param object_name: Hostname or hostgroup name
        :type object_name: str
        :param object_type: host or hostgroup
        :type object_type: str
        :param hours: Amount of hours for the downtime (default: 8 hours)
        :type hours: int
        :param comment: Downtime comment
        :type comment: str
        """
        return self.__manage_downtime(object_name, object_type, hours, \
            comment, remove_downtime=False)



    def remove_downtime(self, object_name, object_type):
        """
        Removes scheduled downtime for a host or hostgroup
        For this, a object name is required.

        :param object_name: Hostname or hostgroup name
        :type object_name: str
        :param object_type: host or hostgroup
        :type object_type: str
        """
        return self.__manage_downtime(object_name, object_type, hours=8, \
            comment="Downtime managed by katprep", remove_downtime=True)



    def has_downtime(self, object_name, object_type="host"):
        """
        Returns whether a particular object (host, hostgroup) is currently in
        scheduled downtime. This required specifying an object name and type.

        :param object_name: Hostname or hostgroup name
        :type object_name: str
        :param object_type: Host or hostgroup (default: host)
        :type object_type: str
        """
        #retrieve and load data
        result = self.__api_get("/objects/{}s?host={}".format(
           object_type, object_name)
        )
        data = json.loads(result)

        #check if downtime
        #TODO: how to do this for hostgroups?!
        if object_type == "host":
            for result in data["results"]:
                if result["attrs"]["downtime_depth"] > 0:
                    return True
            return False



    def get_services(self, object_name, only_failed=True):
        """
        Returns all or failed services for a particular host.

        :param object_name:
        :type object_name: str
        :param only_failed: True will only report failed services
        :type only_failed: bool
        """

        result = self.__api_get("/objects/services?host={}".format(
            object_name)
        )
        data = json.loads(result)
        services = []
        for result in data["results"]:
            service = result["attrs"]["display_name"]
            state = result["attrs"]["state"]
            #print "Service: {}".format(result["attrs"]["display_name"])
            #print "  State: {}".format(result["attrs"]["state"])
            if only_failed == False or state == 0:
                this_service = {"name": service, "state": state}
                services.append(this_service)
        return services



    def get_hosts(self):
        """
        Returns hosts by their name and IP.
        """

        result = self.__api_get("/objects/hosts")
        data = json.loads(result)
        hosts = []
        for result in data["results"]:
            host = result["attrs"]["display_name"]
            ip = result["attrs"]["address"]
            this_host = {"name": host, "ip": ip}
            hosts.append(this_host)
        return hosts