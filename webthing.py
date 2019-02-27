'''
Mozilla WebThing library.
'''

import streams
from mozilla.webthing import webserver
from wireless import wifi
import json
import requests


class Thing():
    '''
====
Thing class
====

.. class:: Thing

    A Thing is an object exposing some REST API containing properties, actions
    and events.
    '''
    properties = {}
    getters = {}
    setters = {}

    actions = {}
    action_request = []
    # making a copy of each action request in seperate lists;
    # one for the name of the action and one for the unique id
    action_request_specific = {}
    action_request_specific_id = {}
    events = {}
    # making a list to have each event description
    event_descr = {}
    callbacks = {}
    running = {}
    _uid = 0

    def __init__(self, thing_id, name, description=None, base_url="/", timestamp_fn=None):
        '''
.. method:: __init__(thing_id, name, description=None, base_url="/", timestamp_fn=None)

    * *thing_id* is the unique id for a Thing
    * *name* is pretty name for human interfaces
    * *description* is a human readable description of this Thing
    * *base_url* is the base path, configurable for advanced purposes.
    * *timestamp_fn* is a function to call for retrieving a timestamp string to be used in events generation.
        '''
        self.id = thing_id
        self.name = name
        if description==None:
            self.description = "No description provided"
        else:
            self.description = description

        self.webserver = None

        self.timestamp_fn = timestamp_fn()
        if not base_url.startswith("/"):
            base_url = "/" + base_url
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        self.base_url = base_url


    def _get_uid(self):
        self._uid += 1
        return self._uid


    def _set_webserver(self, server):
        '''
        Store a webserver instance for using it later when an action is created.
        '''
        self.webserver = server


    def add_property(self, prop_id, label, prop_type, getter, setter=None, unit=None, description=None):
        '''
..  method:: add_property(prop_id, label, prop_type, getter, setter=None, unit=None, description=None)

        Add a new property to this thing.

    * *prop_id* is a string for identifying uniquely a property
    * *label* is a pretty name for this property
    * *prop_type* can be one of ["integer", "number", "boolean"].
    * *getter* is a function that must return current status of this property
    * *setter* is a function that must accept new status as a parameter and set it
    * *unit* is a pretty name for the measure unit of this property
    * *description* is a human readable description of this property
        '''
        if description==None:
            inner_descr = "No description provided"
        else:
            inner_descr = description
        prop = {
            "label": label,
            "type": prop_type,
            "readOnly": setter is None,
            "description":  inner_descr,
            "links": [{"href":"%s%s/properties/%s" % (self.base_url, self.id, prop_id)}],
        }
        if unit:
            prop["unit"] = unit
        self.properties[prop_id] = prop
        self.getters[prop_id] = getter
        if setter:
            self.setters[prop_id] = setter


    def add_action(self, act_id, label, callback, input_type=None, description=None):
        '''
..  method:: add_action(act_id, label, callback, input_type=None, description=None)

    Add a new action to this thing.

    * *act_id* is a string for identifying uniquely an action
    * *label* is a pretty name for this action
    * *input_type* can be one of ["integer", "number", "boolean"].
    * *callback* is a function that must accept a parameter of `input_type` and use it
    * *description* is a human readable description of this action
        '''
        action = {
            "label": label,
        }
        action["description"] = description
        action["input"] = {"type":input_type}
        self.actions[act_id] = action
        self.callbacks[act_id] = callback

    def register_event(self, evt_id, description):
        '''
..  method:: register_event(evt_id, description)

    Register a new event type to this Thing.

    * *evt_id* is a string for identifying uniquely this event type.
    * *description* is a human readable description for this event.
        '''
        event_description = {"description": description}
        self.event_descr[evt_id]= event_description
        self.events[evt_id] = {"data":0, "timestamp":0}


    def signal_event(self, evt_id, inp_data=None):
        '''
..  method:: signal_event(evt_id, inp_data=None)

    Log a new event of type `evt_id`.

    * *evt_id* is a string for choosing a registered event type.
    * *inp_data* is an optional argument for this event type.
        '''
        if inp_data is None:
            event = {"timestamp":self.timestamp_fn}
            self.events[evt_id] = {"timestamp":self.timestamp_fn}
        else:
            event = {"data":inp_data, "timestamp":self.timestamp_fn}
            pinToggle(LED0)
            self.events[evt_id]["data"] = inp_data
            self.events[evt_id]["timestamp"] = self.timestamp_fn

        # registering a handler for each event to respond with its information
        webserver.register_handler(
            "%s%s/events/%s" % (self.base_url, self.id, evt_id),
            "get",
            self._get_event_specific,
            args=(evt_id)
        )


    def _dispatch_action(self, static_args, payload):
        res = {}

        if len(payload) != 1:
            # Only one action at a time
            raise NameError

        for act_id in payload:
            if act_id not in self.actions or "input" not in payload[act_id]:
                # Action id not found
                raise NameError
            res[act_id] = self.callbacks[act_id](True, payload[act_id]["input"])
            act_req_id = self._get_uid()
            act_url = '%s%s/actions/%s/%s' % (self.base_url, self.id, act_id, act_req_id)
            self.webserver.register_handler(
                act_url,
                'delete',
                self._cancel_action,
                args=(act_req_id,)
            )

            self.webserver.register_handler(                        #registering a handler for each action request to respond with its information
                act_url,
                'get',
                self._get_action_request_specific_id,
                args=(act_req_id,)
            )

            self.running[act_req_id] = self.callbacks[act_id]
            self.action_request_specific[act_id] = payload
            self.action_request_specific_id[act_req_id] = payload

        self.action_request.append(payload)
        payload["status"] = "pending"
        payload["href"] = act_url

        return (201, "Created", payload)

    def _dispatch_all_event(self, static_args, payload):                     #responds with all event requests
        return (200, "OK",[self.events])


    def _cancel_action(self, static_args):
        act_req_id = static_args[0]
        if act_req_id not in self.running:
            # Only one action at a time
            raise NameError
        self.running[act_req_id](False, None)
        del self.running[act_req_id]


    def _get_all_properties(self):
        res = {}
        for prop_id in self.properties:
            res[prop_id] = self.getters[prop_id]()
        return res

    def _get_all_actions_requests(self):
        return (200, "OK",self.action_request)

    def _get_action_request_specific(self,act_id):
        return (200, "OK",self.action_request_specific[act_id])

    def _get_action_request_specific_id(self,act_req_id):
        return (200, "OK",self.action_request_specific_id[act_req_id])

    def _get_event_specific(self,evt_id):
        return (200, "OK",self.events[evt_id])


    def as_dict(self):
        '''
.. method:: as_dict()

        Return a dict representing this Thing.
        '''
        thing = {
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "actions": self.actions,
            "events": self.event_descr,
            #"events": self.events,
            "links": [
                {
                    "rel": "properties",
                    "href": "/%s/properties" % self.id
                },
                {
                    "rel": "actions",
                    "href": "%s%s/actions" % (self.base_url, self.id)
                },
                {
                    "rel": "events",
                    "href": "%s%s/events" % (self.base_url, self.id)
                },
            ]
        }

        #if self.description:
        #    thing["description"] = self.description

        return thing


def encapsulate(args, *fun_args):
    # Utility function for encapsulating a function result inside a dict.

    # `args` is tuple where args[0] is the key and args[1] is a function to call
    # for generating the dictionary.
    # `payload` is a dictionary to be passed as argument to the function called.

    # Example:
    # --------

    # Request:
    # GET /device/led

    # Returns:
    # {
    #     "led": get_led()    # previously registered getter
    # }
    return {args[0]: args[1](*fun_args)}


def decapsulate(args, payload):
    # Utility function for decapsulating a payload received from an API endpoint,
    # and call the function with the resulting object.

    # Example:
    # --------

    # Request:
    # PUT /device/led
    # { "led": false }

    # Effect:
    # set_led(false)    # call the previously registered setter with the param
    # Returns:
    # { "led": false }
    if not args[0] in payload:
        return {
            "error": True,
            "message": "Missing required field: %s" % args[0]
        }
    return {
        args[0]: args[1](payload[args[0]])
    }


def list_things(static_args):
    things = static_args[0]
    return [thing.as_dict() for thing in things]


def run_server(things):
    ip = _get_self_ip()
    if not ip:
        print("Please connect to Wi-Fi first.")
        raise RuntimeError

    print("Device IP address is: %s" % ip)

    thread(webserver.start)

    if isinstance(things, Thing):
        # If the parameter is a single thing we make a list with it
        things = [things]

    webserver.register_handler("/", "get", list_things, args=(things, ))
    for thing in things:
        thing._set_webserver(webserver) # Thing need a webserver to dinamically add actions endpoints
        webserver.register_handler("/%s" % thing.id, "get", thing.as_dict)
        # Properties
        webserver.register_handler(
            "%s%s/properties" % (thing.base_url, thing.id),
            "get",
            thing._get_all_properties
        )

        for prop_id in thing.properties:
            prop = thing.properties[prop_id]

            # Register property getter
            webserver.register_handler(
                "%s%s/properties/%s" % (thing.base_url, thing.id, prop_id),
                "get",
                encapsulate,
                args=(prop_id, thing.getters[prop_id])
            )
            if not prop["readOnly"]:
                # Register property setter
                webserver.register_handler(
                    "%s%s/properties/%s" % (thing.base_url, thing.id, prop_id),
                    "put",
                    decapsulate,
                    args=(prop_id, thing.setters[prop_id])
                )


        # Actions dispatcher
        webserver.register_handler(
            "%s%s/actions" % (thing.base_url, thing.id),
            "post",
            thing._dispatch_action,
            args=(True, )
        )
        webserver.register_handler(
            "%s%s/actions" % (thing.base_url, thing.id),
            "cancel",
            thing._dispatch_action,
            args=(False, )
        )

        # events dispatcher
        webserver.register_handler(
            "%s%s/events" % (thing.base_url, thing.id),
            "get",
            thing._dispatch_all_event,
            args=(False, )
        )
        #
        webserver.register_handler(
            "%s%s/actions" % (thing.base_url, thing.id),
            "get",
            thing._get_all_actions_requests,
            args=(False, )
        )

        for act_id in thing.actions:
            # Register action getter
            webserver.register_handler(
                "%s%s/actions/%s" % (thing.base_url, thing.id, act_id),
                "get",
                thing._get_action_request_specific,
                args=(act_id,)
            )
        print("Device ready at: http://%s/%s" % (ip, thing.id))


def _get_self_ip():
    if wifi.is_linked():
        info = wifi.link_info()
        return info[0]
    return None

