#!/usr/bin/env python3

import collections
import json
import sys
import threading
import os
import zmq
import logging

from os import listdir
from os.path import isfile, join, exists

from rlx_osal.osal_base_pb2 import OSALRequest, OSALResponse
from rlx_osal.errors import UnknownOSALMethodError, OSALMethodInvalidParameterError, OSALError, OSALBusyError, OSALNoneError, OSALParameterError, OSALProcessingError, OSALNoBackgroundError, OSALUnknownRequestError
from rlx_osal.outcome import Outcome


pluginsdir = "/usr/lib/python3/dist-packages/rlx_osal/plugins/"
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(1, pluginsdir)

descriptors = {}

logger = logging.getLogger("python3-rlx-osal")

plugins = ["osal_pb2.py"]
if exists(pluginsdir):
    plugins.extend([p for p in listdir(pluginsdir) if isfile(join(pluginsdir, p))])
for p in plugins:
    if not p.endswith("_pb2.py"):
        continue
    logger.info("loading OSAL plugin: %s" % p[:-7])
    m = __import__(p[:-3])
    for p in m.DESCRIPTOR.message_types_by_name.items():
        proc = p[0]  # name
        if proc in descriptors.keys():
            # FIXME: log warning, already exists
            continue
        descriptors[proc] = getattr(m, proc)

Response = collections.namedtuple('Response', ['outcome', 'errorMessage', 'response'])

class OSAL():

    # FIXME:add def __doc__ for autocompletion

    def __init__(self, configuration_file=None):
        self.descriptors = descriptors
        self.config = {"type": "unix",
                       "unix":
                       {"zmq_url": "ipc:///opt/roche/var/run/rlx-osal.sock",
                        "zmq_event_url": "ipc:///opt/roche/var/run/rlx-osal-event.sock",
                        "zmq_client_url": "ipc:///opt/roche/var/run/rlx-osal-client.sock"},
                       "tcp":
                       {"zmq_url": "tcp://localhost:8083",
                        "zmq_event_url": "tcp://localhost:8084",
                        "zmq_client_url": "tcp://localhost:8085"}
                       }

        self.read_osal_config()

        if configuration_file and os.path.exists(configuration_file):
            with open(configuration_file) as fd:
                self.config.update(json.load(fd))

        self.exit = threading.Event()
        self.socket_config = self.config[self.config['type']]
        self.context = zmq.Context()
        self.zmq_socket = self.context.socket(zmq.REQ)
        self.zmq_socket.connect(self.socket_config['zmq_url'])
        self.client_event_callbacks = {}

        self.clientThread = None
        self.eventThread = None
        self.zmq_event_socket = None

    def __del__(self):
        self.exit.set()
        self.zmq_socket.close()

        if self.zmq_event_socket is not None:
            self.zmq_event_socket.close()

        if self.eventThread is not None:
            self.eventThread.join()

        if self.clientThread is not None:
            self.clientThread.join()

    @staticmethod
    def __assign_field(msg, field, value):
        if field.label == field.LABEL_REPEATED:
            # For repeated fields extend works with singular fields and
            # singular message fields
            getattr(msg, field.name).extend(value)
        else:
            # Singular fields can just be assigned
            # Singular message fields need to make use of CopyFrom
            # message_type is None for singular fields
            if field.message_type is None:
                setattr(msg, field.name, value)
            else:
                getattr(msg, field.name).CopyFrom(value)

    def __getattr__(self, method_name):
        msg_cls = self.descriptors.get(method_name)

        if msg_cls is None:
            raise UnknownOSALMethodError(method_name)

        def zmqcall(*args, background=False, **kwargs):
            msg = msg_cls()

            if len(args) > len(msg.DESCRIPTOR.fields):
                raise OSALMethodInvalidParameterError("Too many values provided")

            # Fill fields based on the positional arguments
            for arg, field in zip(args, msg.DESCRIPTOR.fields):
                self.__assign_field(msg, field, arg)

            for key, arg in kwargs.items():
                try:
                    field = msg.DESCRIPTOR.fields_by_name[key]
                except:
                    raise OSALMethodInvalidParameterError(f"Unknown field {key}")

                self.__assign_field(msg, field, arg)

            envelope = OSALRequest()
            envelope.background = background
            envelope.request.Pack(msg)

            try:
                self.zmq_socket.send(envelope.SerializeToString())
                return self.get_response(self.zmq_socket.recv())
            except (zmq.ZMQError, zmq.Again):
                # FIXME: logger.error("send/recv {}".format(e))
                return None

            # FIXME: Error handling
            # if background:
            # return osal_resp
            # if osal_resp.outcome == Outcome.NONE.value:
                # raise OSALNoneError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.ERROR.value:
                # raise OSALError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.PARAMETER_ERROR.value:
                # raise OSALParameterError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.UNKNOWN_REQUEST.value:
                # raise OSALUnknownRequestError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.BUSY.value:
                # raise OSALBusyError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.NO_BACKGROUND.value:
                # raise OSALNoBackgroundError(message=osal_resp.errorMessage)
            # if osal_resp.outcome == Outcome.PROCESSING.value:
                # raise OSALProcessingError(message=osal_resp.errorMessage)
        return zmqcall

    def get_response(self, msg, osal_resp: OSALResponse=OSALResponse()) -> Response:
        osal_resp.ParseFromString(msg)
        c = None
        if osal_resp.data.type_url:
            message_name = osal_resp.data.type_url.split('/')[-1]
            c = self.descriptors[message_name]()
            c.ParseFromString(osal_resp.data.value)
        return Response(outcome=osal_resp.outcome, errorMessage=osal_resp.errorMessage, response=c)

    def read_osal_config(self, configuration_file="/etc/default/rlx-osal"):
        if configuration_file and os.path.exists(configuration_file):
            with open(configuration_file, "r") as cf:
                for line in cf.readlines():
                    if line.strip().startswith("ZEROMQ_TYPE="):
                        try:
                            value = int(line.split("=")[1].split("#")[0])
                            if value == 0:
                                self.config["type"] = "unix"
                            elif value == 1:
                                self.config["type"] = "tcp"
                            else:
                                logger.error("unsupported ZeroMQ socket type: %s", value)
                        except Exception as e:
                            logger.error("unable to parse ZeroMQ socket type: %s", e)

    def subscribe_events(self, callback):
        # connect to event socket
        self.zmq_event_socket = self.context.socket(zmq.SUB)
        self.zmq_event_socket.connect(self.socket_config['zmq_event_url'])
        self.zmq_event_socket.setsockopt(zmq.SUBSCRIBE, b'')

        # start thread
        self.eventThread = threading.Thread(target=self.evt_loop, args=[callback])
        self.eventThread.start()

    def subscribe_client_events(self, topic, callback):
        self.zmq_client_socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
        if topic not in self.client_event_callbacks:
            self.client_event_callbacks[topic] = callback
        # FIXME: else complain

    def enable_client_events(self):
        logger.info("enable_client_events")
        if self.clientThread is None:
            self.zmq_client_socket = self.context.socket(zmq.SUB)
            self.zmq_client_socket.set_hwm(0)  # important to not drop events
            self.zmq_client_socket.connect(self.socket_config['zmq_client_url'])

            self.clientThread = threading.Thread(target=self.client_event_loop)
            self.clientThread.start()

    def unsubscribe_client_events(self, topic):
        self.zmq_client_socket.setsockopt(zmq.UNSUBSCRIBE, topic.encode())
        if topic in self.client_event_callbacks:
            del self.client_event_callbacks[topic]
        # FIXME: else complain

    def evt_loop(self, callback):
        while not self.exit.is_set():
            try:
                msg = self.zmq_event_socket.recv(flags=zmq.NOBLOCK)
                rootevent = OSALResponse()
                rootevent.ParseFromString(msg)
                callback(rootevent)
            except (zmq.error.ZMQError, zmq.error.Again):
                self.exit.wait(timeout=1)
            except Exception as exc:
                logger.error("event zmq exception")
                logger.exception(exc)

    def client_event_loop(self):
        while not self.exit.is_set():
            try:
                topic, msg = self.zmq_client_socket.recv_multipart(flags=zmq.NOBLOCK)
            except zmq.error.Again:
                self.exit.wait(timeout=0.25)
                continue
            except Exception as exc:
                logger.error("client event zmq exception")
                logger.exception(exc)

            try:
                rootevent = OSALResponse()
                rootevent.ParseFromString(msg)
                eventname = rootevent.data.type_url.split('/')[-1]
                event = self.descriptors[eventname]()
                event.ParseFromString(rootevent.data.value)
            except Exception as exc:
                logger.error("client event exception")
                logger.exception(exc)

            try:
                t = topic.decode()
                if t in self.client_event_callbacks:
                    self.client_event_callbacks[t](event)
            except Exception as exc:
                logger.error("client event callback exception")
                logger.exception(exc)
        logger.info("client event loop terminated")

    def quit(self):
        self.exit.set()
