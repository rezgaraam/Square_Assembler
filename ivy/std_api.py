# Copyright (c) 2005-2023 Sebastien Bigaret <sebastien.bigaret@telecom-bretagne.eu>
"""
Implements the standard Ivy API.

The :doc:`tutorial` gives an overview of the most important features.
You can also refer to the example code ``pyhello.py`` for an example of use.

All methods in this module are frontends to a `ivy.IvyServer` instance, stored
in the module's attribute `_IvyServer`.

Connecting to/disconnecting from the Ivy bus:

  :py:func:`IvyInit`, :py:func:`IvyStart`, :py:func:`IvyMainLoop`,
  :py:func:`IvyStop`

Handling our subscriptions:

  :py:func:`IvyBindMsg`, :py:func:`IvyUnbindMsg`, :py:func:`IvyGetMessages()`,

Reacting to other types of messages:
  :py:func:`IvyBindDirectMsg`, :py:func:`IvyBindPong`/:py:func:`IvySetPongCallback()`

Inspecting the Ivy bus:

  :py:func:`IvyGetApplicationList`, :py:func:`IvyGetApplication`,
  :py:func:`IvyGetApplicationName`, :py:func:`IvyGetApplicationHost`,
  :py:func:`IvyGetApplicationMessages`

Interacting with other Ivy clients:

  :py:func:`IvySendMsg`, :py:func:`IvySendDirectMsg`, :py:func:`IvySendDieMsg`,
  :py:func:`IvySendError()`,
  :py:func:`IvyBindRegexpChange`,
  :py:func:`IvySendPing()`,
  :py:func:`IvyBindPong`/:py:func:`IvySetPongCallback()`

Timers:

  :py:func:`IvyTimerRepeatAfter`, :py:func:`IvyTimerModify`,
  :py:func:`IvyTimerRemove`
"""
import signal
import warnings
from collections.abc import Callable
from typing import List, Optional, Tuple, TypeVar

from .ivy import (
    IvyApplicationConnected,
    IvyApplicationDisconnected,
    IvyClient,
    IvyRegexpAdded,
    IvyRegexpRemoved,
    void_function,
)

_IvyServer = None

__all__ = [
    'IvyApplicationConnected',
    'IvyApplicationDisconnected',
    'IvyBindDirectMsg',
    'IvyBindMsg',
    'IvyBindPong',
    'IvyBindRegexpChange',
    'IvyClient',
    'IvyGetApplication',
    'IvyGetApplicationHost',
    'IvyGetApplicationList',
    'IvyGetApplicationMessages',
    'IvyGetApplicationName',
    'IvyGetMessages',
    'IvyInit',
    'IvyMainLoop',
    'IvyRegexpAdded',
    'IvyRegexpRemoved',
    'IvySendDieMsg',
    'IvySendDirectMsg',
    'IvySendError',
    'IvySendMsg',
    'IvySendPing',
    'IvySetPongCallback',
    'IvyStart',
    'IvyStop',
    'IvyTimerModify',
    'IvyTimerRemove',
    'IvyTimerRepeatAfter',
    'IvyUnBindMsg',
    'IvyUnbindMsg',
    'void_function',
]

T = TypeVar('T')


def public_api(fct: Callable) -> Callable:
    """Indicates that decorated functions are part of the public API"""
    if fct.__name__ not in __all__:
        warnings.warn(
            "function {} marked as @public_api but it is not in __all__".format(
                fct.__name__
            )
        )
    # __all__.append(fct.__name__)
    return fct


@public_api
def IvyInit(
    agent_name: str,
    ready_msg: Optional[str] = None,
    main_loop_type_ignored: int = 0,
    on_cnx_fct: Callable = void_function,
    on_die_fct: Callable = void_function,
) -> None:
    """
    Initializes the module. This method should be called exactly once before any
    other method is called.
    """
    global _IvyServer
    assert _IvyServer is None
    from .ivy import IvyServer

    _IvyServer = IvyServer(agent_name, ready_msg, on_cnx_fct, on_die_fct)


@public_api
def IvyStart(ivybus: Optional[str] = None) -> None:
    """
    Starts the Ivy server and fully activates the client.  Please refer to the
    discussion in :py:func:`IvyMainLoop()` 's documentation.
    """
    assert _IvyServer is not None
    _IvyServer.start(ivybus)


@public_api
def IvyMainLoop() -> None:
    """
    Simulates the original main loop: simply waits for the server termination.

    Note that while the original API requires this to be called, this module
    does NOT rely in any way on this method. In particular, a client is
    fully functional and begins to receive messages as soon as the
    :py:func:`IvyStart()` method is called.
    """
    assert _IvyServer is not None
    signal.signal(signal.SIGINT, lambda *arg: IvyStop())
    while not _IvyServer.server_termination.wait(5):
        pass


@public_api
def IvyStop() -> None:
    """Notifies the other participants on the bus that this agent is
    signing off, and properly terminates the underlying listening
    thread.  When this method returns, the agent is disconnected from
    the bus.
    """
    assert _IvyServer is not None
    _IvyServer.stop()


@public_api
def IvyBindMsg(on_msg_fct: Callable, regexp: str) -> int:
    """
    Registers a method that should be called each time a message matching
    regexps is sent on the Ivy bus.

    :return: an id identifying the binding, that can be used to unregister it
      (see :py:func:`IvyUnbindMsg`)
    """
    assert _IvyServer is not None
    return _IvyServer.bind_msg(on_msg_fct, regexp)


@public_api
def IvyBindDirectMsg(on_msg_fct: Callable) -> None:
    """
    Registers a method that should be called each time someone sends us
    a direct message

    """
    assert _IvyServer is not None
    _IvyServer.bind_direct_msg(on_msg_fct)


@public_api
def IvyUnbindMsg(binding_id: int) -> str:
    """
    Unregisters a binding.

    :param binding_id: the binding's id, as previously returned by :py:func:`IvyBindMsg`
    :return: the regexp corresponding to the unsubscribed binding
    :except KeyError: if no such subscription can be found

    .. versionadded:: 3.2
    """
    assert _IvyServer is not None
    return _IvyServer.unbind_msg(binding_id)


@public_api
def IvyUnBindMsg(binding_id: int) -> str:
    """
    Unregisters a binding.  This is the same as
    :py:func:`IvyUnbindMsg`, except that it is named like in the Java
    API (``unBindMsg()``).  If in doubt, use :py:func:`IvyUnbindMsg`
    preferably.

    :param binding_id: the binding's id, as previously returned by :py:func:`IvyBindMsg`
    :return: the regexp corresponding to the unsubscribed binding
    :except KeyError: if no such subscription can be found

    """
    return IvyUnbindMsg(binding_id)


@public_api
def IvyBindRegexpChange(regexp_change_callback: Callable) -> None:
    """
    Registers a function to be called when an agent adds or removes a binding.

    This function will receive 4 parameters: an `IvyClient`, the event (either
    `IvyRegexpAdded` or `IvyRegexpRemoved`), the identifier of the subscriptions
    and the regular expression itself (as a string).

    """
    assert _IvyServer is not None
    return _IvyServer.bind_regexp_change(regexp_change_callback)


@public_api
def IvySendMsg(msg: str) -> int:
    """
    Sends a message on the bus, to the agents which have one or more
    bindings that the message matches.
    """
    assert _IvyServer is not None
    return _IvyServer.send_msg(msg)


@public_api
def IvySendDieMsg(client: IvyClient) -> None:
    """
    Sends a "die" message to `client`, instructing him to terminate.

    :param client: an :py:class:`ivy.ivy.IvyClient` object,  as returned by
      :py:func:`IvyGetApplication()`
    """
    assert _IvyServer is not None
    client.send_die_message()


@public_api
def IvySendDirectMsg(client: IvyClient, num_id: int, msg: str) -> None:
    """
    Sends a direct message to an other Ivy client, with the supplied
    numerical id and message.

    :Parameters:
      - `client`: an :py:class:`ivy.ivy.IvyClient` object, as returned by
        :py:func:`IvyGetApplication()`
      - `num_id`: an additional integer to use. It may, or may not, be
        meaningful, this only depends on the usage your application makes of
        it, the Ivy protocol itself does not care and simply transmits it
        along with the message.
      - `msg`: the message to send
    """
    assert _IvyServer is not None
    client.send_direct_message(num_id, msg)


@public_api
def IvySendError(client: IvyClient, num_id: int, error_msg: str) -> None:
    """
    Sends an "error" message to `client`

    :Parameters:
      - `client`: an :py:class:`ivy.ivy.IvyClient` object, as returned by
        :py:func:`IvyGetApplication()`
      - `num_id`: an additional integer to use. It may, or may not, be
        meaningful, this only depends on the usage your application makes of
        it, the Ivy protocol itself does not care and simply transmits it
        along with the message.
      - `error_msg`: the message to send
    """
    assert _IvyServer is not None
    client.send_error(num_id, error_msg)


@public_api
def IvyGetApplicationList() -> List[str]:
    """
    Returns the names of the applications that are currently connected
    """
    assert _IvyServer is not None
    return _IvyServer.get_clients()


@public_api
def IvyGetApplicationMessages(client: IvyClient) -> List[Tuple[int, str]]:
    """
    Returns all subscriptions for that client

    :param client: an :py:class:`ivy.ivy.IvyClient` object,  as returned by
      :py:func:`IvyGetApplication()`
    :return: list of tuples (idx, regexp)
    """
    assert _IvyServer is not None
    return _IvyServer.get_client_bindings(client)


@public_api
def IvyGetMessages() -> List[Tuple[int, str]]:
    """
    Returns our subscriptions

    :return: list of tuples (idx, regexp)
    """
    assert _IvyServer is not None
    return _IvyServer.get_subscriptions()


@public_api
def IvyGetApplication(name: str) -> Optional[IvyClient]:
    """
    Returns the Ivy client registered on the bus under the given name.

    .. warning:: if multiple applications are registered w/ the same name only
      one is returned

    :return: an :py:class:`ivy.ivy.IvyClient` object
    """
    assert _IvyServer is not None
    clients = _IvyServer.get_client_with_name(name)
    return clients and clients[0] or None


@public_api
def IvyGetApplicationName(client: IvyClient) -> Optional[str]:  # none si pas init.
    """
    Equivalent to ``client.agent_name``

    :param client: an :py:class:`ivy.ivy.IvyClient` object, as returned by
      :py:func:`IvyGetApplication()`
    """
    return client.agent_name


@public_api
def IvyGetApplicationHost(client: IvyClient) -> str:
    """
    Equivalent to ``client.fqdn``. IP address is stored under ``client.ip``,
    and port number under ``client.port``

    :param client: an :py:class:`ivy.ivy.IvyClient` object,  as returned by
      :py:func:`IvyGetApplication()`
    """
    return client.fqdn


_timers = {}


@public_api
def IvyTimerRepeatAfter(count: int, delay_ms: int, callback: Callable) -> int:
    """
    Creates and activates a new timer

    :Parameters:
      - `count`: nb of time to repeat the loop, ``0`` (zero) for an endless loop
      - `delay_ms`: the delay between ticks, in milliseconds
      - `callback`: the function to call on every tick. That function is
        called without any parameters.

    :return: the timer's id
    """
    assert _IvyServer is not None
    from .ivy import IvyTimer

    # The original python API relies on a callback called without any parameter
    def callback_wrapper(timer: IvyTimer, callback: Callable = callback) -> None:
        callback()

    timer = IvyTimer(_IvyServer, count, delay_ms, callback_wrapper)
    _timers[timer.id] = timer
    timer.start()
    return timer.id


@public_api
def IvyTimerModify(timer_id: int, delay_ms: int) -> None:
    """
    Modifies a timer's delay.  Note that the modification will happen after
    the next tick.

    :Parameters:
      - `timer_id`: id of the timer to modify, as returned by
        :py:func:`IvyTimerRepeatAfter()`
      - `delay`: the delay, in milliseconds, between ticks
    """
    _timers[timer_id].delay = delay_ms


@public_api
def IvyTimerRemove(timer_id: int) -> None:
    """
    Stops and removes a given timer.

    :param timer_id: id of the timer, as returned by :py:func:`IvyTimerRepeatAfter`
    """
    timer = _timers[timer_id]
    timer.abort = True
    del _timers[timer_id]


@public_api
def IvyBindPong(on_pong_fct: Callable) -> None:
    """
    Registers a method that should be called when we receive a PONG
    message.  When receiving a PONG message in replying of a PING
    message we sent (see :py:func:`IvySendPing`), this method is called with
    three arguments:

    - the first one is the IvyClient object sorresponding to the agent
      sending the message;

    - the second one is the time elapsed between the sending of the
      ping and the receiving of the pong.

    """
    assert _IvyServer is not None
    _IvyServer.bind_pong(on_pong_fct)


@public_api
def IvySetPongCallback(on_pong_fct: Callable) -> None:
    """
    alias for :py:func:`IvyBindPong` (``IvySetPongCallback`` is the name used
    in ivy-c)
    """
    IvyBindPong(on_pong_fct)


@public_api
def IvySendPing(client: IvyClient) -> None:
    """
    Sends a PING message to the client.
    See also: :py:func:`IvyBindPong()`
    """
    assert _IvyServer is not None
    client.send_ping()


# # copy/paste for quick tests w/ ivyprobe
# from ivy.std_api import *
# IvyInit('Test', 'test welcome', 0)
# IvyStart()
# def onmsgproc(*larg):
#    print larg
#
# IvyBindMsg(onmsgproc, '(.*)')
# IvyGetApplicationList()
# app=IvyGetApplication('IVYPROBE')
# IvyGetApplicationName(app)
# IvyGetApplicationHost(app)
# IvySendDirectMsg(app, 765, 'glop')
# IvySendDieMsg(app)
