"""
Using an IvyServer
------------------

The following code is a typical example of use:

.. code-block:: python

    from ivy.ivy import IvyServer

    class MyAgent(IvyServer):
      def __init__(self, agent_name):
        IvyServer.__init__(self,agent_name)
        self.start('127.255.255.255:2010')
        self.bind_msg(self.handle_hello, 'hello .*')
        self.bind_msg(self.handle_button, 'BTN ([a-fA-F0-9]+)')

      def handle_hello(self, agent):
        print('[Agent %s] GOT hello from %r'%(self.agent_name, agent))

      def handle_button(self, agent, btn_id):
        print(
          '[Agent %s] GOT BTN button_id=%s from %r'
          % (self.agent_name, btn_id, agent)
        )
        # let's answer!
        self.send_msg('BTN_ACK %s'%btn_id)

    a=MyAgent('007')


Messages types:
  `BYE`, `ADD_REGEXP`, `MSG`, `ERROR`, `DEL_REGEXP`, `END_REGEXP`,
  `END_INIT`, `START_REGEXP`, `START_INIT`, `DIRECT_MSG`, `DIE`

Separators:
  `ARG_START`, `ARG_END`

Misc. constants:
  `DEFAULT_IVYBUS`, `PROTOCOL_VERSION`, `IVY_SHOULD_NOT_DIE`,
  `IvyApplicationConnected`, `IvyApplicationDisconnected`, `DEFAULT_TTL`

Objects and functions related to logging:
  `ivylogger`, `debug`, `log`, `warn`, `error`, `ivy_loghdlr`,
  `ivy_logformatter`

Implementation details
----------------------

An Ivy agent is made of several threads:

  - an :class:`IvyServer` instance

  - a UDP server, launched by the Ivy server, listening to incoming UDP
    broadcast messages

  - :class:`IvyTimer` objects

Copyright (c) 2005-2023 Sebastien Bigaret <sebastien.bigaret@telecom-bretagne.eu>

"""

import logging
import os
import random
import re
import socket
import socketserver
import struct
import sys
import threading
import time
import traceback

# type hint w/ list and dict are py3.9+
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

ivylogger = logging.getLogger('Ivy')

if os.environ.get('IVY_LOG_TRACE'):
    _TRACE = logging.TRACE = logging.DEBUG - 1  # type: ignore[attr-defined]
    logging.addLevelName(_TRACE, 'TRACE')
    trace = lambda *args, **kw: ivylogger.log(_TRACE, *args, **kw)  # noqa: E731
else:
    trace = lambda *args, **kw: None  # noqa: E731

debug = ivylogger.debug
info = log = ivylogger.info
warn = ivylogger.warning
error = ivylogger.error

ivy_loghdlr = logging.StreamHandler()  # stderr by default
ivy_logformatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(threadName)s %(message)s'
)

ivy_loghdlr.setFormatter(ivy_logformatter)
ivylogger.addHandler(ivy_loghdlr)

##
DEFAULT_IVYBUS = '127:2010'
PROTOCOL_VERSION = 3

# Message types. Refer to "The Ivy architecture and protocol" for details
BYE = 0
ADD_REGEXP = 1
MSG = 2
ERROR = 3
DEL_REGEXP = 4

# START_REGEXP and END_REGEXP are the ones declared in ivy.c
# however we'll use the aliases START_INIT and END_INIT here
END_REGEXP = END_INIT = 5
START_REGEXP = START_INIT = 6

DIRECT_MSG = 7
DIE = 8

PING = 9
PONG = 10

# Other constants
ARG_START = '\002'
ARG_END = '\003'

# for multicast, arbitrary TTL value taken from ivysocket.c:SocketAddMember
DEFAULT_TTL = 64

IvyApplicationConnected = 1
IvyApplicationDisconnected = 2

IvyRegexpAdded = 3
IvyRegexpRemoved = 4

IVY_SHOULD_NOT_DIE = 'Ivy Application Should Not Die'


def void_function(*arg: Any, **kw: Any) -> Any:
    """A function that accepts any number of parameters and does nothing"""
    pass


def UDP_init_and_listen(
    broadcast_addr: str, port: int, socket_server: "IvyServer"
) -> None:
    """
    Called by an IvyServer at startup; the method is responsible for:

    - sending the initial UDP broadcast message,

    - waiting for incoming UDP broadcast messages being sent by new clients
      connecting on the bus.  When it receives such a message, a connection
      is established to that client and that connection (a socket) is then
      passed to the IvyServer instance.

    :Parameters:
      - `broadcast_addr`: the broadcast address used on the Ivy bus
      - `port`: the port dedicated to the Ivy bus
      - `socket_server`: instance of an IvyServer handling communications
        for our client.
    """
    log('Starting Ivy UDP Server on %r:%r', broadcast_addr, port)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    on = 1
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, on)
    if hasattr(socket, 'SO_REUSEPORT'):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, on)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, on)

    s.bind(('', port))  # '' means: INADDR_ANY

    # Multicast
    if is_multicast(broadcast_addr):
        debug('Broadcast address is a multicast address')

        ifaddr = socket.INADDR_ANY
        mreq = struct.pack(
            '4sl', socket.inet_aton(broadcast_addr), socket.htonl(ifaddr)
        )
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, DEFAULT_TTL)
    # /Multicast

    msg = "%li %s %s %s\n" % (
        PROTOCOL_VERSION,
        socket_server.port,
        socket_server.agent_id,
        socket_server.agent_name,
    )
    s.sendto(msg.encode(), (broadcast_addr, port))

    s.settimeout(0.1)
    while socket_server.isAlive():
        try:
            udp_raw_msg, (ip, ivybus_port) = s.recvfrom(1024)
        except socket.timeout:
            continue

        udp_msg = udp_raw_msg.decode('UTF-8')
        debug('UDP got: %r source: %r:%r', udp_msg, ip, ivybus_port)

        appid = appname = None
        try:
            udp_msg_l = udp_msg.split(' ')
            protocol_version, port_number = int(udp_msg_l[0]), int(udp_msg_l[1])
            if len(udp_msg_l) > 2:
                # "new" udp protocol, with id & appname
                appid = udp_msg_l[2]
                appname = ' '.join(udp_msg_l[3:]).strip('\n')
                debug('IP %s has id: %s and name: %s', ip, appid, appname)
            else:
                debug('Received message w/o app. id & name from %r', ip)

        except ValueError:  # unpack error, invalid literal for int()
            warn('Received an invalid UDP message (%r) from :', udp_msg)

        if protocol_version != PROTOCOL_VERSION:
            error(
                'Received a UDP broadcast msg. w/ protocol version:%s , expected: %s',
                protocol_version,
                PROTOCOL_VERSION,
            )
            continue

        if appid == socket_server.agent_id:
            # this is us!
            debug('UDP from %r: ignored: we sent that one!', ip)
            continue

        # build a new socket and delegate its handling to the SocketServer
        debug('New client connected: %s:%s', ip, port_number)

        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, on)
        trace('New client %s:%s, socket %r', ip, port_number, new_socket)
        # Since we already have a client's name and id, lets register it
        # (this was previously done in IvyHandler's __init__() only)
        # but we want to check that we did not receive more than once a
        # broadcast coming from the same
        try:
            new_client = socket_server.register_client(
                ip, port_number, new_socket, appid, appname
            )
        except ValueError:
            # an agent with that app-id is already registered
            info(
                'UDP from %s:%s (%s):'
                ' discarding message, an application w/ id=%s is already registered',
                ip,
                port_number,
                appname,
                appid,
            )
            continue

        try:
            new_socket.connect((ip, port_number))
        except Exception:
            # e.g., timeout on connect
            info('Client %r: failed to connect to its socket, ignoring it', new_client)
            debug(
                'Client %r: failed to connect to its socket, got:%s',
                new_client,
                traceback.format_exc(),
            )
            socket_server.remove_client(
                ip, port_number, trigger_application_callback=False
            )
        else:
            socket_server.process_request(new_socket, (ip, port_number))
    log('UDP Server stopped')


def is_multicast(ip: str) -> bool:
    """
    Tells whether the specified ip is a multicast address or not

    :param ip: an IPv4 address in dotted-quad string format, for example
      192.168.2.3
    """
    return int(ip.split('.')[0]) in range(224, 239)


def decode_ivybus(ivybus: Optional[str] = None) -> Tuple[str, int]:
    """
    Transforms the supplied string into the corresponding broadcast address
    and port

    :param ivybus: if ``None`` or empty, defaults to environment variable
      ``IVYBUS``, or :py:const:`DEFAULT_IVYBUS` if no such env.var. exists

    :return: a tuple made of (broadcast address, port number). For example:
      ::

        >>> print decode_ivybus('192.168.12:2010')
        ('192.168.12.255', 2010)

    """
    if not ivybus:
        ivybus = os.getenv('IVYBUS', DEFAULT_IVYBUS)

    broadcast, port_s = ivybus.split(':', 1)
    port = int(port_s)
    broadcast = broadcast.strip('.')
    broadcast += '.' + '.'.join(
        ['255', '255', '255', '255'][: -len(broadcast.split('.'))]
    )
    # if broadcast is multicast it had 4 elements -> previous line added a '.'
    broadcast = broadcast.strip('.')
    debug('Decoded ivybus %s:%s', broadcast, port)
    return broadcast, port


def decode_MSG_params(params: str) -> Sequence[str]:
    '''Implements the special treatment of parameters in text messages
    (message type: MSG).  The purpose here is to make sure that, when
    their last parameter is not ETX-terminated, they are processed the
    same way as in the reference ivy-c library.
    '''
    MISSING_ETX = (
        'Received a misformatted message: last parameter is not ETX-terminated'
    )
    ret_params: Sequence[str] = []
    if ARG_END in params:  # there is at least one parameter
        # All parameters are ETX-terminated: we remove the last ARG_END==ETX
        # before  calling split(ARG_END)...
        if params[-1] == ARG_END:
            params = params[:-1]
        else:
            # ... However if the last ETX is missing, we pretend it was here
            # so that we behave exactly as ivy-c in this case.
            warn(MISSING_ETX)

        ret_params = params.split(ARG_END)

    elif len(params) > 0:
        # One parameter was transmitted but it has no trailing ARG_END/ETX:
        # let's conform to ivy-c behaviour and return it
        warn(MISSING_ETX)
        ret_params = (params,)

    return ret_params


def decode_msg(message: str) -> Tuple[int, int, Sequence[str]]:
    """
    Extracts from an ivybus message its message type, the conveyed
    numerical identifier and its parameters.

    :return: msg_type, numerical_id, parameters
    :except IvyMalformedMessage: if the message's type or numerical identifier are not
      integers

    """
    try:
        msg_id_s, _msg = message.split(' ', 1)
        num_id_s, _msg = _msg.split(ARG_START, 1)

        msg_id = int(msg_id_s)
        num_id = int(num_id_s)

        if msg_id == MSG:
            params = decode_MSG_params(_msg)

        else:
            if _msg and _msg[-1] == ARG_END:
                # Remove the trailing ARG_END before calling split()
                _msg = _msg[:-1]
            params = _msg.split(ARG_END)

    except ValueError as exc:
        raise IvyMalformedMessage from exc
    debug("message: %r -> params: %r", message, params)
    return msg_id, num_id, params


def encode_message(
    msg_type: int, numerical_id: int, params: Union[str, Sequence] = ''
) -> bytes:
    """

    params is string -> added as-is
    params is list -> concatenated, separated by ARG_END
    """
    msg = "%s %s" % (msg_type, numerical_id) + ARG_START

    # The following test is needed to reproduce the very same behaviour
    # observed w/ the C library
    # (tested w/ pyhello.py and ivyprobe)
    if isinstance(params, str):
        msg += params
    elif len(params):
        msg += ARG_END.join(params)
        msg += ARG_END
    trace('encode_message(params: %s) -> %s' % (repr(params), repr(msg + '\n')))

    raw_msg = (msg + '\n').encode()

    return raw_msg


class IvyProtocolError(Exception):
    """
    Raised when a received (well-formed) message is not recognized
    as a valid message
    """


class IvyMalformedMessage(Exception):
    """Raised when a received message is incorrectly formed"""


class IvyIllegalStateError(RuntimeError):
    """
    Raised when a method is called in an incorrect context, for
    example when attemptin to send a message whilst the server isn't
    initialised.
    """


NOT_INITIALIZED = 0
INITIALIZATION_IN_PROGRESS = 1
INITIALIZED = 2


class IvyClient:
    """
    Represents a client connected to the bus. Every callback methods
    registered by an agent receive an object of this type as their first
    parameter, so that they know which agent on the bus is the cause of the
    event which triggered the callback.

    An IvyClient is responsible for:
      - performing the initialization required by the Ivy protocol,
      - sending the various types of messages specified in the protocol.

    It is **not** responsible for receiving messages from the client: another
    object is in charge of that, namely an :class:`IvyHandler` object.

    The local IvyServer creates one IvyClient per agent on the bus.

    Protocol-related methods:
      :py:func:`start_init`, :py:func:`end_init`,

    Announcing changes in our subscriptions:
      :py:func:`send_new_subscription`, :py:func:`remove_subscription`,

    Sending messages:
      :py:func:`send_message`, :py:func:`send_direct_message`,
      :py:func:`send_die_message`, :py:func:`send_error`,
      :py:func:`send_ping`, :py:func:`send_pong`, :py:func:`wave_bye`

    MT-safety
    ---------
    MT-safe.
    """

    def __init__(
        self,
        ip: str,
        port: int,
        client_socket: socket.socket,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> None:
        self.agent_id = agent_id
        # agent_name will be overridden when start_init() is called
        # but nevermind,
        self.agent_name = agent_name
        self.ip = ip
        self.port = port
        self.socket = client_socket

        self.fqdn: str = socket.getfqdn(ip)
        self.status: int = NOT_INITIALIZED
        self.socket.settimeout(0.1)

        self.ping_ts_ns: List[int] = []  # timestamps, in nanoseconds
        self.ping_lock = threading.Lock()

    def start_init(self, agent_name: str) -> None:
        """
        Finalizes the initialization process by setting the client's
        agent_name.  This is a Ivy protocol requirement that an application
        sends its agent-name only once during the initial handshake (beginning
        with message of type ``START_INIT`` and ending with a type
        ``END_INIT``).  After this method is called, we expect to receive the
        initial subscriptions for that client (or none); the initialization
        process completes after `end_init` is called.

        :except IvyIllegalStateError: if the method has already been called
          once
        """
        if self.status != NOT_INITIALIZED:
            raise IvyIllegalStateError
        self.agent_name = agent_name
        self.status = INITIALIZATION_IN_PROGRESS
        debug('Client:%r: Starting initialization', self)

    def end_init(self) -> None:
        """
        Should be called when the initialization process ends.

        :except IvyIllegalStateError: if the method has already been called
          (and ``self.status`` has already been set to ``INITIALIZED``)
        """
        if self.status == INITIALIZED:
            raise IvyIllegalStateError
        debug('Client:%r: Initialization ended', self)
        self.status = INITIALIZED

    def send_message(self, num_id: int, captures: Sequence) -> None:
        """
        Sends a message to the client.

        :Parameters:
          - `num_id`: index of the client's subscription matched by the
            message
          - `captures`: the capturing groups found when the regexp of
            that subscription match the message
        """
        self._send(MSG, num_id, captures)

    def send_direct_message(self, num_id: int, msg: str) -> None:
        """
        Sends a direct message

        Note: the message will be encoded by `encode_message` with
        ``numerical_id=num_id`` and ``params==msg``; this means that if `msg`
        is not a string but a list or a tuple, the direct message will contain
        more than one parameter.  This is an **extension** of the original Ivy
        design, supported by python, but if you want to inter-operate with
        applications using the standard Ivy API the message you send *must* be
        a string. See in particular in ``ivy.h``::

          typedef void (*MsgDirectCallback)( IvyClientPtr app,
                                             void *user_data, int id, char *msg ) ;

        """
        if self.status == INITIALIZED:
            debug(
                'Client:%r: direct message being sent: id: %r msg: %r',
                self,
                num_id,
                msg,
            )
            self._send(DIRECT_MSG, num_id, msg)

    def send_die_message(self, num_id: int = 0, msg: str = '') -> None:
        """
        Sends a die message
        """
        if self.status == INITIALIZED:
            debug(
                'Client:%r: die msg being sent: num_id: %r msg: %r',
                self,
                num_id,
                msg,
            )
            self._send(DIE, num_id, msg)

    def send_new_subscription(self, idx: int, regexp: str) -> None:
        """
        Notifies the remote agent that we (the local agent) subscribe to
        a new type of messages

        :Parameters:
          - `idx`: the index/id of the new subscription. It is the
            responsibility of the local agent to make sure that every
            subscription gets a unique id.
          - `regexp`: a regular expression. The subscription consists in
            receiving messages matching the regexp.
        """
        self._send(ADD_REGEXP, idx, regexp)

    def send_ping(self) -> None:
        """
        Sends a PING request to the client. The time at which the
        request is sent is pushed into an internal LIFO stack, which is
        then used by :py:func:`get_next_ping_delta`.
        """
        with self.ping_lock:
            self.ping_ts_ns.append(time.monotonic_ns())
            self._send(PING, 0)

    def send_pong(self, num_id: int) -> None:
        """
        Sends a PONG message to a client.  This is intended to be
        sent after this client sent us a PING message.
        """
        self._send(PONG, num_id)

    def get_next_ping_delta(self) -> Optional[float]:
        """
        Returns the time (in seconds) elapsed since the oldest ping
        request.  See: :py:func:`get_next_ping_delta_ns` for details.

        :return: the time (seconds) elapsed since the oldest ping
          request, or None if there is not such request.
        """
        delta = self.get_next_ping_delta_ns()
        return delta / 1e9 if delta is not None else None

    def get_next_ping_delta_ns(self) -> Optional[int]:
        """
        Returns the time elapsed since the oldest ping request, in
        nanoseconds.  This oldest request is then discarded from the
        internal LIFO stack (see :py:func:`send_ping`).

        :return: the time (in nanoseconds) elapsed since the oldest ping
          request.  Returns ``None`` if there is no such request
          --i.e. either no ping was sent or the method has been called
          at least as many times as :py:func:`send_ping`).
        """
        with self.ping_lock:
            if len(self.ping_ts_ns) == 0:
                return None
            return time.monotonic_ns() - self.ping_ts_ns.pop(0)

    def remove_subscription(self, idx: int) -> None:
        """
        Notifies the remote agent that we (the local agent) are not
        interested in a given subscription.

        :Parameters:
          - `idx`: the index/id of a subscription previously registered with
            `send_new_subscription`.
        """
        self._send(DEL_REGEXP, idx)

    def wave_bye(self, num_id: int = 0) -> None:
        """Notifies the remote agent that we are about to quit"""
        self._send(BYE, num_id)

    def send_error(self, num_id: int, msg: str) -> None:
        """
        Sends an error message
        """
        self._send(ERROR, num_id, msg)

    def __eq__(self, client: Any) -> bool:
        """
        cf. dict[client] or dict[(ip,port)] UNNEEDED FOR THE MOMENT
        """
        if isinstance(client, IvyClient):
            return self.ip == client.ip and self.port == client.port

        if type(client) in (tuple, list) and len(client) == 2:
            return self.ip == client[0] and self.port == client[1]

        return False

    def __hash__(self) -> int:
        """``hash((self.ip, self.port))``"""
        return hash((self.ip, self.port))

    def __repr__(self) -> str:
        """Returns ``'ip:port (agent_name)'``"""
        return '%s:%s (%s)' % (self.ip, self.port, self.agent_name)

    def __str__(self) -> str:
        """Returns ``'agent_name@FQDN'``"""
        return '%s@%s' % (self.agent_name, self.fqdn)

    def _send(self, msg_type: int, *params: Any) -> None:
        """
        Internally used to send message to the remote agent through the opened
        socket `self.socket`.  This method catches all exceptions
        `socket.error` and `socket.timeout` and ignores them, simply logging
        them at the "info" level.

        The errors that can occur are for example::

            socket.timeout: timed out
            socket.error: (104, 'Connection reset by peer')
            socket.error: (32, 'Broken pipe')

        They can happen after a client disconnects abruptly (because it was
        killed, because the network is down, etc.). We assume here that if and
        when an error happens here, a disconnection will be detected shortly
        afterwards by the server which then removes this agent from the bus.
        Hence, we ignore the error; please also note that not ignoring the
        error can have an impact on code, for example, IyServer.send_msg()
        does not expect that IvyClient.send() fails and if it fails, it is
        possible that the server does not send the message to all possible
        subscribers.

        .. note:: ``ivysocket.c:SocketSendRaw()`` also ignores error, simply
           logging them.

        """
        if self.status != INITIALIZED:
            return

        try:
            self.socket.send(encode_message(msg_type, *params))
        except (socket.timeout, socket.error) as exc:
            log('[ignored] Error on socket (send) with %r: %s', self, exc)
            # debug(
            #     '[ignored] Error on socket (sending %s:%r) with %r: %s',
            #     msg_type, params, self, exc,
            #     exc_info=exc,
            # )


class ClientsBinding:
    """Holds agents on the bus which are subscribed (bound) to a given regexp"""

    __slots__ = ['pattern', 'clients']
    pattern: re.Pattern
    clients: List[Tuple[IvyClient, int]]

    def __init__(
        self, pattern: re.Pattern, clients: List[Tuple[IvyClient, int]]
    ) -> None:
        self.pattern = pattern
        self.clients = clients or []

    def regexp(self) -> str:
        return self.pattern.pattern


class IvyServer(socketserver.ThreadingTCPServer):
    """An Ivy server is responsible for receiving and handling the messages
    that other clients send on an Ivy bus to a given agent.

    An IvyServer has two important attributes: :py:attr:`usesDaemons` and
    :py:attr:`server_termination`.

    Communication on the ivybus:
      :py:func:`start`, :py:func:`send_msg`,
      :py:func:`send_direct_message`, :py:func:`send_ready_message`,
      :py:func:`handle_msg`, :py:func:`stop`

    Inspecting the ivybus:
      :py:func:`get_clients`, :py:func:`_get_client`,
      :py:func:`get_client_with_name`

    Our own subscriptions:
      :py:func:`get_subscriptions`,
      :py:func:`bind_msg`, :py:func:`unbind_msg`,
      :py:func:`_add_subscription`, :py:func:`_remove_subscription`,
      :py:func:`_get_fct_for_subscription`

    Other clients' subscriptions:
      :py:func:`add_client_binding`, :py:func:`get_client_bindings`,
      :py:func:`remove_client_binding`

    Handling callbacks:
      Callbacks can be registered either by assigning a Callable to a
      class attribute or by calling the corresponding method:

      :py:attr:`app_callback`
      :py:attr:`regexp_change_callback`, :py:func:`bind_regexp_change`
      :py:attr:`die_callback`, :py:func:`bind_die_change`
      :py:attr:`direct_callback`, :py:func:`bind_direct_msg`
      :py:attr:`pong_callback`, :py:func:`bind_pong`


    MT-safety
    ---------
    All public methods (not starting with an underscore ``_``) are
    MT-safe

    """

    def __init__(
        self,
        agent_name: str,
        ready_msg: Optional[str] = '',
        app_callback: Callable = void_function,
        die_callback: Callable = void_function,
        usesDaemons: bool = False,
    ) -> None:
        """
        Builds a new IvyServer.  A client only needs to call `start()` on the
        newly created instances to connect to the corresponding Ivy bus and to
        start communicating with other applications.

        MT-safety: both functions :py:func:`app_callback` and
        :py:func:`die_callback` must be prepared to be called concurrently

        :Parameters:
          - `agent_name`: the client's agent name
          - `ready_msg`: a message to send to clients when they connect
          - `app_callback`: a function called each time a client connects or
            disconnects. This function is called with a single parameter
            indicating which event occurred: `IvyApplicationConnected` or
            `IvyApplicationDisconnected`.
          - `die_callback`: called when the IvyServer receives a DIE message
          - `usesDaemons`: see above.

        .. seealso:: :py:func:`bind_msg()`, :py:func:`start()`
        """
        self._thread: Optional[threading.Thread] = None

        # the empty string is equivalent to INADDR_ANY
        socketserver.ThreadingTCPServer.__init__(self, ('', 0), IvyHandler)
        #: The port on which the TCP server awaits connection
        self.port = self.socket.getsockname()[1]
        # self.allow_reuse_address=True

        # _clients_ip_port: maps (ip,port) to the index of the associated client
        # in _clients.
        # * Both elements _clients_ip_port and _clients are equivalent to a
        #   simple dict mapping (ip, port) to client
        # * With such a simple dict, iterations on clients would require
        #   either acquiring the global lock, or copy()'ing the dict.values()
        #   before releasing the lock and iterating; we want to avoid both
        #   for performance reasons
        # * Using a map for _clients_ip_port rather than a list means that the
        #   index of a client can be retrieved as O(1) rather than O(n).
        #   Esp. important in get_client() which is involved in handling
        #   incoming msgs
        # * remove_client() is the only operation in O(n)
        self._clients_ip_port: Dict[
            Tuple[str, int], int
        ] = {}  # (ip, port)→index of the client in _clients
        self._clients: Tuple[IvyClient, ...] = ()  # list of connected clients

        #: private, maps regexp to ClientsBinding
        self._clients_bindings: Dict[str, ClientsBinding] = {}

        #: idx -> (regexp, function), see bind_msg() for details, below
        self._subscriptions: Dict[int, Tuple] = {}
        #: the next index to use within the _subscriptions map.
        self._next_subst_idx = 0

        self.agent_name = agent_name
        self.ready_message = ready_msg

        # app_callback's parameter event=CONNECTED / DISCONNECTED
        self.app_callback = app_callback
        self.die_callback = die_callback
        self.direct_callback = void_function
        self.regexp_change_callback = void_function
        self.pong_callback = void_function

        #: the global_lock protects: _clients_ip_port, _clients, _subscriptions and
        #: _next_subst_idx.
        #: The lock should be held for as short a time as possible ; in particular, it
        #: should not be held while sending messages on the bus or executing callbacks
        self._global_lock = threading.RLock()

        #: Holds ``(broadcast_addr, port)`` of the Ivy bus after the server is started
        self.ivybus: Optional[Tuple[str, int]] = None

        self.usesDaemons = usesDaemons
        """
        Whether the threads are daemonic or not.  Daemonic threads
        do not prevent python from exiting when the main thread stop,
        while non-daemonic ones do.  Default is False.  This attribute
        should be set through :py:func:`__init__()` time and should not be
        modified afterwards.
        """

        self.server_termination = threading.Event()
        """
        A :py:class:`threading.Event` object that is set on server
        shutdown.  It can be used either to test whether the server has
        been stopped (``server_termination.isSet()``) or to wait until
        it is stopped (``server_termination.wait()``).  Application code
        should not try to set the Event directly, rather it will call
        :py:func:`stop()` to terminate the server.
        """

        self.agent_id = (
            agent_name
            + time.strftime('%Y%m%d%H%M%S')
            + '%05i' % random.randint(0, 99999)
            + str(self.port)
        )

    @staticmethod
    def run_callback(
        callback: Callable,
        callback_description: str,
        agent: IvyClient,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """
        Runs a callback, catching any exception it may raise.

        :Parameters:
         - `callback`: the function to be called
         - `callback_description`: the description to use in the error message,
           when an exception is raised.
         - `agent`: the :py:class:`IvyClient` triggering the callback, which
           is passed as the first argument to the callback
         - `on_exc`: the returned value in case an exception was raised by
           the callback.
         - `args`: other positional arguments are passed as-is to the callback.
         - `kw`: other keyword  arguments are passed as-is to the callback.

        :return: the value returned by the callback, or `on_exc` if
          an exception was raised

        """
        on_exc = kw.get('on_exc', None)
        try:
            return callback(agent, *args, **kw)
        except Exception:
            error('%s: exception raised', callback_description, exc_info=sys.exc_info())
            return on_exc

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        """
        Handle requests (calling :py:func:`handle_request()`) until doomsday... or
        until :py:func:`stop()` is called.

        This method is registered as the target method for the thread.
        It is also responsible for launching the UDP server in a separate
        thread, see :py:func:`UDP_init_and_listen` for details.

        You should not need to call this method, use :py:func:`start` instead.
        """
        if self.ivybus is None:
            raise IvyIllegalStateError("Server has not been start()ed")
        t2 = threading.Thread(target=UDP_init_and_listen, args=(self.ivybus + (self,)))
        t2.daemon = self.usesDaemons
        log('Starting UDP listener')
        t2.start()

        self.socket.settimeout(0.1)
        super().serve_forever(poll_interval)
        log('TCP Ivy Server terminated')

    def start(self, ivybus: Optional[str] = None) -> None:
        """
        Binds the server to the ivybus. The server remains connected until
        :py:func:`stop` is called, or until it receives and accepts a 'die' message.

        :except IvyIllegalStateError: if the server has already been
          started
        """
        if self._thread is not None:
            error('Cannot start: IvyServer already started')
            raise IvyIllegalStateError('not running')

        self.ivybus = decode_ivybus(ivybus)

        log('Starting IvyServer on port %li', self.port)
        self.server_termination.clear()
        self._thread = threading.Thread(target=self.serve_forever)
        self._thread.daemon = self.usesDaemons
        self._thread.start()

    def stop(self) -> None:
        """
        Disconnects the server from the ivybus. It also sets the
        :py:attr:`server_termination` event.

        :except IvyIllegalStateError: if the server is not running
        """
        if not self.isAlive():
            error('Cannot stop: not running')
            raise IvyIllegalStateError('not running')

        self.ivybus = None
        with self._global_lock:
            clients = self._clients
        for client in clients:
            try:
                client.wave_bye()
            except socket.error:
                pass
        self.shutdown()
        self.server_termination.set()
        self._thread.join()  # type: ignore  # not None if it isAlive()
        self._thread = None

    def isAlive(self) -> bool:
        if self._thread is None:
            return False
        return self._thread.is_alive()

    def get_clients(self) -> List[str]:
        """
        Returns the list of the agent names of all connected clients

        :see: get_client_with_name
        """
        with self._global_lock:
            return [
                c.agent_name for c in self._clients if c.status == INITIALIZED  # type: ignore  # noqa
            ]  # c.agent_name cannot be None if it is initialized

    def get_client(self, ip: str, port: int) -> IvyClient:
        """
        Returns the corresponding client, and create a new one if needed.

        If agent_id is not None, the method checks whether a client with the
        same id is already registered; if it exists, the method exits by
        returning None.

        You should not need to call this, use :py:func:`get_client_with_name` instead
        """
        with self._global_lock:
            try:
                idx = self._clients_ip_port[(ip, port)]
                return self._clients[idx]
            except KeyError:
                raise ValueError("Client is not registered")

    def register_client(
        self,
        ip: str,
        port: int,
        client_socket: socket.socket,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> IvyClient:
        """
        Creates a new IvyClient.

        If agent_id is not None, the method checks whether a client with the
        same id is already registered; if it exists, the method exits by
        returning None.

        You should not need to call this, use :py:func:`get_client_with_name` instead
        """
        with self._global_lock:
            if (ip, port) in self._clients_ip_port:
                raise ValueError("Already exists")
            new_client = IvyClient(ip, port, client_socket, agent_id, agent_name)
            self._clients_ip_port[(ip, port)] = len(self._clients)
            self._clients += (new_client,)
            return new_client

    def get_client_with_name(self, name: str) -> List[IvyClient]:
        """
        Returns the list of the clients registered with a given agent-name

        :see: get_clients
        """
        clients = []
        with self._global_lock:
            for client in self._clients:
                if client.agent_name == name:
                    clients.append(client)
            return clients

    def handle_new_client(self, client: IvyClient) -> None:
        """
        Completes connection with the client
        """
        # TODO: maybe add a flag (while connecting) on the client, that would prevent
        # sending msg. etc. as CNX. not confirmed

        self.run_callback(
            self.app_callback,
            'application callback (connection)',
            client,
            IvyApplicationConnected,
        )

    def handle_die_message(self, msg_id: int, from_client: IvyClient) -> bool:
        """ """
        should_die = self.run_callback(
            self.die_callback, 'die callback', from_client, msg_id
        )
        should_die = should_die != IVY_SHOULD_NOT_DIE

        log(
            'Received a die msg from: %s with id: %s -- should die=%s',
            from_client or '<unknown>',
            msg_id,
            should_die,
        )
        if should_die:
            self.stop()
        return should_die

    def handle_direct_msg(self, client: IvyClient, num_id: int, msg: str) -> None:
        """
        :param client:
        :param num_id:
        :param msg:
        :return:
        """
        client_s = client or '<unknown>'
        log('Received a direct msg from: %s with id: %s -- %r', client_s, num_id, msg)
        description = "direct message callback: num_id:%s msg:%r" % (num_id, msg)
        self.run_callback(self.direct_callback, description, client, num_id, msg)

    def handle_regexp_change(
        self, client: IvyClient, event: int, num_id: int, regexp: str
    ) -> None:
        """ """
        log(
            'Regexp change: %s %s regexp %d: %s',
            client or '<unknown>',
            event == ADD_REGEXP and 'add' or 'remove',
            num_id,
            regexp,
        )
        event = IvyRegexpAdded if event == ADD_REGEXP else IvyRegexpRemoved
        description = (
            "regexp change callback ("
            + (ADD_REGEXP and 'add' or 'remove')
            + "): num_id:{num_id} regexp:{regexp}"
        )
        self.run_callback(
            self.regexp_change_callback, description, client, event, num_id, regexp
        )

    def handle_pong(self, client: IvyClient, delta: float) -> None:
        """ """
        log(
            'Received a pong reply from: %s with delta: %s',
            client or '<unknown>',
            delta,
        )
        self.run_callback(self.pong_callback, 'pong callback', client, delta)

    def remove_client(
        self, ip: str, port: int, trigger_application_callback: bool = True
    ) -> Optional[IvyClient]:
        """
        Removes a registered client

        This method is responsible for calling ``server.app_callback``

        :return: the removed client, or None if no such client was found

        .. note:: NO NETWORK CLEANUP IS DONE
        """
        with self._global_lock:
            try:
                idx = self._clients_ip_port[(ip, port)]
            except KeyError:
                debug('Trying to remove a non registered client %s:%s', ip, port)
                return None
            removed_client = self._clients[idx]
            debug('Removing client %r', removed_client)
            self._clients = self._clients[:idx] + self._clients[idx + 1 :]
            del self._clients_ip_port[(ip, port)]
            self._clients_ip_port = {
                k: i if i < idx else i - 1 for k, i in self._clients_ip_port.items()
            }
            self._remove_client_bindings(removed_client)
        if trigger_application_callback:
            self.run_callback(
                self.app_callback,
                'application callback (disconnection)',
                removed_client,
                IvyApplicationDisconnected,
            )
        return removed_client

    def add_client_binding(
        self, client: IvyClient, binding_id: int, regexp: str
    ) -> None:
        try:
            with self._global_lock:
                if regexp in self._clients_bindings:
                    self._clients_bindings[regexp].clients.append((client, binding_id))
                else:
                    self._clients_bindings[regexp] = ClientsBinding(
                        pattern=re.compile(regexp),
                        clients=[(client, binding_id)],
                    )
        except re.error as invalid_regexp:
            raise ValueError(
                'Client:%r: Invalid regexp %r:%r' % (self, binding_id, regexp)
            ) from invalid_regexp

    def get_client_bindings(self, client: IvyClient) -> List[Tuple[int, str]]:
        client_bindings = []
        with self._global_lock:
            for regexp, binding in self._clients_bindings.items():
                for _client, _binding_id in binding.clients:
                    if _client == client:
                        client_bindings.append((_binding_id, regexp))
        return client_bindings

    def remove_client_binding(
        self, client: IvyClient, binding_id: int
    ) -> Optional[str]:
        with self._global_lock:
            for regexp, binding in self._clients_bindings.items():
                try:
                    binding.clients.remove((client, binding_id))
                    return regexp
                except ValueError:
                    pass
        return None

    def _remove_client_bindings(self, client: IvyClient) -> None:
        with self._global_lock:
            for _, binding in self._clients_bindings.items():
                binding.clients = [(c, _i) for c, _i in binding.clients if c != client]

    def send_msg(self, message: str, *, to: Optional[IvyClient] = None) -> int:
        """
        Send a message to the clients which subscribed to such a
        message (or to a specific client if parameter `to` is set).
        Specifically, a message is sent to a given client *each time*
        the message matches one of its subscriptions ; as a consequence,
        this can result in more than one (ivy) message being sent to a
        client, depending on its subscriptions.

        :param message: the message to send

        :param to: the client to which the message is to be sent. When
          ``None`` (the default) the message is sent to all connected
          clients.

        :return: the number of times a subscription matched the message
        """
        count = 0
        with self._global_lock:
            regexps = list(self._clients_bindings.values())

        for clients_binding in regexps:
            regexp = clients_binding.pattern
            match = regexp.match(message)
            if match:
                # Value for an optional group not participating in the
                # match defaults to the empty string
                captures = match.groups(default='')
                for client, binding_id in clients_binding.clients:
                    if to is None or client is to:
                        client.send_message(binding_id, captures)
                        count += 1

        return count

    def send_direct_message(
        self, agent_name: str, num_id: int, msg: str, stop_on_first: bool = True
    ) -> bool:
        """
        Sends a direct message to the agent named ``agent_name``.  If there
        is more than one agent with that name on the bus, parameter
        `stop_on_first` determines the behaviour.

        :Parameters:
          - `agent_name`: the name of the agent(s) to which the direct message
            should be sent.
          - `num_id`: a numerical identifier attached to the direct message
          - `msg`: the direct message itself
          - `stop_on_first`: if ``True``, the message to all agents having the
            same name will receive the message; if ``False`` the method exits
            after the first message has been sent.

        :return: ``True`` if at least one direct message was sent
        """
        with self._global_lock:
            clients = self._clients
        ret_status = False
        for client in clients:
            if client.agent_name != agent_name:
                continue
            client.send_direct_message(num_id, msg)
            ret_status = True
            if stop_on_first:
                break
        return ret_status

    def send_ready_message(self, client: IvyClient) -> None:
        """Sends the ready message."""
        if self.ready_message:
            self.send_msg(self.ready_message, to=client)

    def _add_subscription(self, regexp: str, fct: Callable) -> int:
        """
        Registers a new regexp and binds it to the supplied fct. The id
        assigned to the subscription and returned by method is **unique**
        to that subscription for the life-time of the server object: even in
        the case when a subscription is unregistered, its id will _never_
        be assigned to another subscription.

        :return: the unique id for that subscription
        """
        # explicit lock here: even if this method is private, it is
        # responsible for the uniqueness of a subscription's id, so we
        # prefer to lock it one time too much than taking the risk of
        # forgetting it (hence, the need for a reentrant lock)
        with self._global_lock:
            idx = self._next_subst_idx
            self._next_subst_idx += 1
            self._subscriptions[idx] = (regexp, fct)
            return idx

    def _remove_subscription(self, idx: int) -> str:
        """
        Unregisters the corresponding regexp

        .. warning:: this method is not MT-safe, callers must acquire the
           global lock

        :return: the regexp that has been removed
        :except KeyError: if no such subscription can be found
        """
        return self._subscriptions.pop(idx)[0]

    def _get_fct_for_subscription(self, idx: int) -> Callable:
        """
        .. warning:: this method is not Multi-Thread-safe, callers must acquire the
           global lock
        """
        return self._subscriptions[int(idx)][1]

    def handle_msg(self, client: IvyClient, idx: int, *params: Any) -> None:
        """
        Simply call the function bound to the subscription id `idx` with
        the supplied parameters.
        """
        with self._global_lock:
            try:
                regexp, callback = self._subscriptions[int(idx)]
            except KeyError:
                # it is possible that we receive a message for a regexp that
                # was subscribed then unregistered
                warn(
                    'Asked to handle an unknown subscription: id:%r params: %r'
                    ' --ignoring',
                    idx,
                    params,
                )
                return
        self.run_callback(
            callback,
            'callback for subscription %i (%s)' % (idx, regexp),
            client,
            *params,
        )

    def get_subscriptions(self) -> List[Tuple[int, str]]:
        with self._global_lock:
            return [(idx, s[0]) for idx, s in self._subscriptions.items()]

    def bind_direct_msg(self, on_direct_msg_fct: Callable) -> None:
        """Registers a callback to be called when a direct message is received."""
        self.direct_callback = on_direct_msg_fct

    def bind_regexp_change(self, on_regexp_change_callback: Callable) -> None:
        """
        Registers a callback to be called when a client on the bus adds or removes
        one of its subscriptions.
        """
        self.regexp_change_callback = on_regexp_change_callback

    def bind_pong(self, on_pong_callback: Callable) -> None:
        """Registers a callback to be called when receiving a "pong" message."""
        self.pong_callback = on_pong_callback

    def bind_msg(self, on_msg_fct: Callable, regexp: str) -> int:
        """
        Registers a new subscription, by binding a regexp to a function, so
        that this function is called whenever a message matching the regexp
        is received.

        :Parameters:
          - `on_msg_fct`: a function accepting as many parameters as there is
            groups in the regexp. For example:

            - the regexp ``'^hello .*'`` corresponds to a function called w/ no
              parameter,
            - ``'^hello (.*)'``: one parameter,
            - ``'^hello=([^ ]*) from=([^ ]*)'``: two parameters

          - `regexp`: (string) a regular expression

        :return: the binding's id, which can be used to unregister the binding
          with :py:func:`unbind_msg()`
        """
        with self._global_lock:
            idx = self._add_subscription(regexp, on_msg_fct)
            clients = self._clients
        for client in clients:
            client.send_new_subscription(idx, regexp)
        return idx

    def unbind_msg(self, num_id: int) -> str:
        """
        Unbinds a subscription

        :param num_id: the binding's id, as returned by :py:func:`bind_msg()`

        :return: the regexp corresponding to the unsubscribed binding
        :except KeyError: if no such subscription can be found
        """
        with self._global_lock:
            regexp = self._remove_subscription(num_id)  # KeyError
            clients = self._clients
        # notify others that we have no interest anymore in this regexp
        for client in clients:
            client.remove_subscription(num_id)
        return regexp


class IvyHandler(socketserver.StreamRequestHandler):
    """
    An IvyHandler is associated to one IvyClient connected to our server.

    It runs into a dedicate thread as long as the remote client is connected
    to us.

    It is in charge of examining all messages that are received and to
    take any appropriate actions.

    Implementation note: the IvyServer is accessible in ``self.server``
    """

    server: IvyServer

    def handle(self) -> None:
        """ """
        # self.request is the socket object
        # self.server is the IvyServer

        bufsize = 1024
        client_socket = self.request
        ip = self.client_address[0]
        port = self.client_address[1]

        trace('New IvyHandler for %s:%s, socket %r', ip, port, client_socket)

        try:
            client = self.server.get_client(ip, port)
        except ValueError:
            client = self.server.register_client(ip, port, client_socket)

        debug('Got a request from ip=%s port=%s', ip, port)

        # First, send our initial subscriptions
        client_socket.send(
            encode_message(START_INIT, self.server.port, self.server.agent_name)
        )
        for idx, subscr in self.server.get_subscriptions():
            client_socket.send(encode_message(ADD_REGEXP, idx, subscr))
        client_socket.send(encode_message(END_INIT, 0))

        while self.server.isAlive():
            try:
                msgs = client_socket.recv(bufsize).decode('UTF-8')
            except socket.timeout:
                # trace('timeout on socket bound to client %r', client)
                continue
            except socket.error as exc:
                log('Error on socket (recv) with %r: %s', client, exc)
                self.server.remove_client(ip, port)
                break  # the server will close the TCP connection

            if not msgs:
                # client is not connected anymore
                log('Lost connection with %r', client)
                self.server.remove_client(ip, port)
                break  # the server will close the TCP connection

            # Sometimes the message is not fully read on the first try,
            # so we insist to get the final newline
            if msgs[-1:] != '\n':
                # w/ the following idioms (also replicated a second time below)
                # we make sure that we wait until we get a message containing
                # the final newline, or if the server is terminated we stop
                # handling the request
                while self.server.isAlive():
                    try:
                        _msg = client_socket.recv(bufsize).decode('UTF-8')
                        break
                    except socket.timeout:
                        continue
                if not self.server.isAlive():
                    break

                msgs += _msg
                while _msg[-1:] != '\n' and self.server.isAlive():
                    while self.server.isAlive():
                        try:
                            _msg = client_socket.recv(bufsize).decode('UTF-8')
                            break
                        except socket.timeout:
                            continue

                    msgs += _msg

                if not self.server.isAlive():
                    break

            debug('Got a request from ip=%s port=%s: %r', ip, port, msgs)

            msgs = msgs[:-1]

            msgs = msgs.split('\n')
            for msg in msgs:
                keep_connection_alive = self.process_ivymessage(msg, client)
                if not keep_connection_alive:
                    self.server.remove_client(ip, port)
                    break
        log('Closing connection to client %r', client)

    def process_ivymessage(self, msg: str, client: IvyClient) -> bool:
        """
        Examines the message (after passing it through the :py:func:`decode_msg()`
        filter) and takes the appropriate actions depending on the message
        types.  Please refer to the document `The Ivy Architecture and
        Protocol <http://www.eei.cena.fr/products/ivy/documentation>`_ and to
        the python code for further details.


        :Parameters:
          - `msg`: (should not include a newline at end)
          - `client`: the agent sending the message

        :return: ``False`` if the connection should be terminated, ``True``
          otherwise

        """
        # cf. static void Receive() in ivy.c
        try:
            msg_id, num_id, params = decode_msg(msg)
        except IvyMalformedMessage:
            warn('Received an incorrect message: %r from: %r', msg, client)
            # TODO: send back an error message
            return True

        debug('Got: msg_id: %r, num_id: %r, params: %r', msg_id, num_id, params)

        err_msg = ''
        try:
            if msg_id == BYE:
                # num_id: not meaningful. No parameter.
                log('%s waves bye-bye: disconnecting', client)
                return False

            elif msg_id == ADD_REGEXP:
                # num_id=id for the regexp, one parameter: the regexp (string)
                err_msg = 'Client %r was not properly initialized' % client
                log(
                    '%s sending a new subscription id:%r regexp:%r',
                    client,
                    num_id,
                    params,
                )
                regexp = params[0]
                try:
                    self.server.add_client_binding(client, num_id, regexp)
                except ValueError as e:
                    warn('%s sent an invalid regexp (id:%r):%r', client, num_id, regexp)
                    debug('Invalid regexp', exc_info=e)
                else:
                    self.server.handle_regexp_change(client, ADD_REGEXP, num_id, regexp)
                # TODO: handle errors (e.g. 2 subscriptions w/ the same id)

            elif msg_id == DEL_REGEXP:
                # num_id=id for the regexp to removed, no parameter
                err_msg = 'Client %r was not properly initialized' % client
                log('%s removing subscription id:%r', client, num_id)
                removed_regexp = self.server.remove_client_binding(client, num_id)
                if removed_regexp:
                    self.server.handle_regexp_change(
                        client, DEL_REGEXP, num_id, removed_regexp
                    )
                else:
                    warn(
                        '%s tried to remove a non-registered subscription w/ id:%r',
                        client,
                        num_id,
                    )

            elif msg_id == MSG:
                # num_id: regexp_id, parameters: the substrings captured by
                # the regexp
                log('From %s: (regexp=%s) %r', client, num_id, params)
                self.server.handle_msg(client, num_id, *params)

            elif msg_id == ERROR:
                # num_id: not meaningful, parameter=error msg
                warn('Client %r sent a protocol error: %s', client, params)
                # TODO: send BYE and close connection, as in ivy.c?

            elif msg_id == START_INIT:
                # num_id: tcp port number, parameter: the client's agentname
                err_msg = (
                    'Client %r sent the initial subscription more than once' % client
                )
                client_name = params[0]
                client.start_init(client_name)
                log('%s connected from %r', client_name, client)

            elif msg_id == END_INIT:
                # num_id: not meaningful. No parameter.
                client.end_init()
                # app. callback
                self.server.handle_new_client(client)
                # send ready message
                self.server.send_ready_message(client)

            elif msg_id == DIE:
                # num_id: not meaningful. No parameter.
                self.server.handle_die_message(num_id, client)

            elif msg_id == DIRECT_MSG:
                # num_id: not meaningful.
                direct_message = params[0]
                log(
                    'Client %r sent us a direct msg num_id:%s msg:%r',
                    client,
                    num_id,
                    direct_message,
                )
                self.server.handle_direct_msg(client, num_id, direct_message)

            elif msg_id == PING:
                debug('Received PING w/ id: %i from %r', num_id, client)
                client.send_pong(num_id)

            elif msg_id == PONG:
                debug('Received PONG from %r (id: %i)', client, num_id)
                delta = client.get_next_ping_delta()
                if delta is None:
                    warn('Client %r sent a unsollicited PONG msg', client)
                else:
                    self.server.handle_pong(client, delta)

            else:
                warn('Unhandled msg from %r: %r', client, msg)

        except IvyIllegalStateError as exc:
            raise IvyProtocolError(err_msg) from exc

        return True


class IvyTimer(threading.Thread):
    """
    An IvyTimer object is responsible for calling a function regularly.  It is
    bound to an :py:class:`IvyServer` and stops when its server stops.

    Interacting with a timer object:
      - Each timer gets a unique id, stored in the attribute ``id``. Note that
        a dead timer's id can be reassigned to another one (a dead timer is a
        timer that has been stopped)

      - To start a timer, simply call its method :py:func:`start`

      - To modify a timer's delay: simply assign :py:attr:`delay`, the
        modification will be taken into account after the next tick. The delay
        should be given in milliseconds.

      - to stop a timer, assign :py:attr:`abort` to ``True``, the timer will stop
        at the next tick (the callback won't be called)

    MT-safety:
      **Please note:** ``start()`` starts a new thread; if the same function is
      given as the callback to different timers, that function should be
      prepared to be called concurrently.  Specifically, if the callback
      accesses shared variables, they should be protected against concurrency
      problems (using locks e.g.).

    """

    def __init__(
        self, server: IvyServer, nbticks: int, delay_ms: int, callback: Callable
    ):
        """
        Creates and activates a new timer.

        :Parameters:
          - `server`: the :py:class:`IvyServer` related to this timer --when the server
            stops, so does the timer.
          - `nbticks`: the number of repetition to make. ``0`` (zero) means:
            endless loop
          - `delay`: the delay, in milliseconds, between two ticks
          - `callback`: a function called at each tick. This function is
            called with one parameter, the timer itself

        """
        threading.Thread.__init__(self)
        self.server = server
        #: The number of ticks after which the timer stops. Zero (0) means infinity.
        self.nbticks = nbticks
        #: The delay between two ticks, in milliseconds
        self.delay = delay_ms
        #: The function to be called at each tick.
        self.callback = callback
        #: When set to True, stops the timer at the next tick (the
        # callback won't be called)
        self.abort = False
        #: The timer unique id
        self.id = id(self)
        self.daemon = server.usesDaemons

    def run(self) -> None:
        """
        Calls the callback every :py:attr:`delay` ms.  See
        :py:class:`IvyTimer` for details on termination.
        """
        ticks = -1
        while self.server.isAlive() and not self.abort and ticks < self.nbticks:
            if self.nbticks:  # 0 means: endless
                ticks += 1
            self.callback(self)
            time.sleep(self.delay / 1000.0)
        log('IvyTimer %s terminated', self.id)
