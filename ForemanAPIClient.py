#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains the ForemanAPIClient and
APILevelNotSupportedExceptrion classes
"""

import logging
import requests
import json
import socket

LOGGER = logging.getLogger('ForemanAPIClient')



class APILevelNotSupportedException(Exception):
    """
    Dummy class for unsupported API levels

.. class:: APILevelNotSupportedException
    """
    pass



class ForemanAPIClient:
    """
    Class for communicating with the Foreman API.

.. class:: ForemanAPIClient
    """
    API_MIN = 2
    """
    int: Minimum supported API version. You really don't want to use v1.
    """
    HEADERS = {'User-Agent': 'katprep (https://github.com/stdevel/katprep)'}
    """
    dict: Default headers set for every HTTP request
    """
    HOSTNAME = ""
    """
    str: Foreman API hostname
    """
    USERNAME = ""
    """
    str: Foreman API username
    """
    PASSWORD = ""
    """
    str: Foreman API password
    """
    URL = ""
    """
    str: Foreman API base URL
    """
    SESSION = None
    """
    Session: HTTP session to Foreman host
    """

    def __init__(self, hostname, username, password):
        """
        Constructor, creating the class. It requires specifying a
        hostname, username and password to access the API. After
        initialization, a connected is established.

        :param hostname: Foreman host
        :type hostname: str
        :param username: API username
        :type username: str
        :param password: corresponding password
        :type password: str
        """
        self.HOSTNAME = self.validate_hostname(hostname)
        self.USERNAME = username
        self.PASSWORD = password
        self.URL = "https://{0}/api/v2".format(self.HOSTNAME)
        #start session and check API version
        self.__connect()
        self.validate_api_support()



    def __connect(self):
        """This function establishes a connection to Foreman."""
        global SESSION
        self.SESSION = requests.Session()
        self.SESSION.auth = (self.USERNAME, self.PASSWORD)



    #TODO: find a nicer way to displaying _all_ the hits...
    def __api_request(self, method, sub_url, payload="", hits=1337, page=1):
        """
        Sends a HTTP request to the Foreman API. This function requires
        a valid HTTP method and a sub-URL (such as /hosts). Optionally,
        you can also specify payload (for POST, DELETE, PUT) and hits/page
        and a page number (when retrieving data using GET).
        There are also alias functions available.

        :param method: HTTP request method (GET, POST, DELETE, PUT)
        :type method: str
        :param sub_url: relative path within the API tree (e.g. /hosts)
        :type sub_url: str
        :param payload: payload for POST/PUT requests
        :type payload: str
        :param hits: numbers of hits/page for GET requests (must be set sadly)
        :type hits: int
        :param page: number of page/results to display (must be set sadly)
        :type page: int

.. todo:: Find a nicer way to display all hits, we shouldn't use 1337 hits/page

.. seealso:: api_get()
.. seealso:: api_post()
.. seealso:: api_put()
.. seealso:: api_delete()
        """
        #send request to API
        try:
            if method.lower() not in ["get", "post", "delete", "put"]:
                #going home
                raise ValueError("Illegal method '{}' specified".format(method))

            #setting headers
            my_headers = self.HEADERS
            if method.lower() != "get":
                #add special headers for non-GETs
                my_headers["Content-Type"] = "application/json"
                my_headers["Accept"] = "application/json,version=2"

            #send request
            if method.lower() == "put":
                #PUT
                result = self.SESSION.put(
                    "{}{}".format(self.URL, sub_url),
                    data=payload, headers=my_headers
                )
            elif method.lower() == "delete":
                #DELETE
                result = self.SESSION.delete(
                    "{}{}".format(self.URL, sub_url),
                    data=payload, headers=my_headers
                )
            elif method.lower() == "post":
                #POST
                result = self.SESSION.post(
                    "{}{}".format(self.URL, sub_url),
                    data=payload, headers=my_headers
                )
            else:
                #GET
                result = self.SESSION.get(
                    "{}{}?per_page={}&page={}".format(
                        self.URL, sub_url, hits, page),
                    headers=self.HEADERS
                )
            if "unable to authenticate" in result.text.lower():
                raise ValueError("Unable to authenticate")
            if result.status_code not in [200, 201, 202]:
                raise ValueError("{}: HTTP operation not successful {}".format(
                    result.status_code, result.text))
            else:
                #return result
                if method.lower() == "get":
                    return result.text
                else:
                    return True

        except ValueError as err:
            LOGGER.error(err)
            pass

    #Aliases
    def api_get(self, sub_url, hits=1337, page=1):
        """
        Sends a GET request to the Foreman API. This function requires a
        sub-URL (such as /hosts) and - optionally - hits/page and page
        definitons.

        :param sub_url: relative path within the API tree (e.g. /hosts)
        :type sub_url: str
        :param hits: numbers of hits/page for GET requests (must be set sadly)
        :type hits: int
        :param page: number of page/results to display (must be set sadly)
        :type page: int
        """
        return self.__api_request("get", sub_url, "", hits, page)

    def api_post(self, sub_url, payload):
        """
        Sends a POST request to the Foreman API. This function requires a
        sub-URL (such as /hosts/1) and payload data.

        :param sub_url: relative path within the API tree (e.g. /hosts)
        :type sub_url: str
        :param payload: payload for POST/PUT requests
        :type payload: str
        """
        return self.__api_request("post", sub_url, payload)

    def api_delete(self, sub_url, payload):
        """
        Sends a DELETE request to the Foreman API. This function requires a
        sub-URL (such as /hosts/2) and payload data.

        :param sub_url: relative path within the API tree (e.g. /hosts)
        :type sub_url: str
        :param payload: payload for POST/PUT requests
        :type payload: str
        """
        return self.__api_request("delete", sub_url, payload)

    def api_put(self, sub_url, payload):
        """
        Sends a PUT request to the Foreman API. This function requires a
        sub-URL (such as /hosts/3) and payload data.

        :param sub_url: relative path within the API tree (e.g. /hosts)
        :type sub_url: str
        :param payload: payload for POST/PUT requests
        :type payload: str
        """
        return self.__api_request("put", sub_url, payload)



    def validate_api_support(self):
        """
        Checks whether the API version on the Foreman server is supported.
        Using older version than API v2 is not recommended. In this case, an
        exception will be thrown.
        """
        try:
            #get api version
            result_obj = json.loads(
                self.api_get("/status")
            )
            LOGGER.debug("API version {} found.".format(
                result_obj["api_version"]))
            if result_obj["api_version"] != self.API_MIN:
                raise APILevelNotSupportedException(
                    "Your API version ({}) does not support the required calls."
                    "You'll need API version {} - stop using historic"
                    " software!".format(result_obj["api_version"], self.API_MIN)
                )
        except ValueError as err:
            LOGGER.error(err)



    @staticmethod
    def validate_hostname(hostname):
        """
        Validates that the Foreman API uses a FQDN as hostname.
        Also looks up the "real" hostname if "localhost" is specified.
        Otherwise, the picky Foreman API won't connect.

        :param hostname: the hostname to validate
        :type hostname: str
        """
        if hostname == "localhost":
            #get real hostname
            hostname = socket.gethostname()
        else:
            #convert to FQDN if possible:
            fqdn = socket.gethostbyaddr(hostname)
            if "." in fqdn[0]:
                hostname = fqdn[0]
        return hostname



    def get_url(self):
        """Returns the configured URL of the object instance"""
        return self.URL

    #TODO: implement - generic function with alias?
    #def get_name_by_id(self, name, api_object):
        #"""Return a Foreman object's name by its ID.

        #Keyword arguments:
        #name -- Foreman object name
        #api_object -- Foreman object type (e.g. host, environment)
        #"""

    def get_id_by_name(self, name, api_object):
        """
        Returns a Foreman object's internal ID by its name. Currently,
        this function works fine for hostgroups, locations, organizations,
        environments and hosts.

        :param name: Foreman object name
        :type name: str
        :param api_object: Foreman object type (e.g. host, environment)
        :type api_object: str
        """
        valid_objects = [
            "hostgroup", "location", "organization", "environment", "host"
        ]
        try:
            if api_object.lower() not in valid_objects:
                #invalid type
                raise ValueError(
                    "Unable to lookup name by invalid field"
                    " type '{}'".format(api_object)
                )
            else:
                #get ID by name
                result_obj = json.loads(
                    self.api_get("/{}s".format(api_object))
                )
                #TODO: nicer way than looping? numpy?
                for entry in result_obj["results"]:
                    if entry["name"].lower() == name.lower():
                        LOGGER.debug(
                            "{} {} seems to have ID #{}".format(
                                api_object, name, entry["id"]
                            )
                        )
                        return entry["id"]
        except ValueError as err:
            LOGGER.error(err)



    def get_hostparam_id_by_name(self, host, param_name):
        """
        Returns a Foreman host parameter's internal ID by its name.

        :param host: Foreman host object ID
        :type host: int
        :param param_name: host parameter name
        :type param_name: str
        """
        try:
            result_obj = json.loads(
                self.api_get("/hosts/{}/parameters".format(host))
            )
            #TODO: nicer way than looping? numpy?
            #TODO allow/return multiple IDs to reduce overhead?
            for entry in result_obj["results"]:
                if entry["name"].lower() == param_name.lower():
                    LOGGER.debug(
                        "Found relevant parameter '{}' with ID #{}".format(
                            entry["name"], entry["id"]
                        )
                    )
                    return entry["id"]

        except ValueError as err:
            LOGGER.error(err)
