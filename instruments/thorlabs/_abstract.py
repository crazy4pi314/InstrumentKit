#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines a generic Thorlabs instrument to define some common functionality.
"""

# IMPORTS #####################################################################

from __future__ import absolute_import
from __future__ import division
from collections import defaultdict

import time

from instruments.thorlabs import _packets
from instruments.abstract_instruments.instrument import Instrument
from instruments.util_fns import assume_units

from quantities import second


# CLASSES #####################################################################


class ThorLabsInstrument(Instrument):

    """
    Generic class for ThorLabs instruments which require wrapping of
    commands and queries in packets.
    """

    def __init__(self, filelike):
        super(ThorLabsInstrument, self).__init__(filelike)
        self.terminator = ''
        self._packet_queue = defaultdict(list)

    def sendpacket(self, packet):
        """
        Sends a packet to the connected APT instrument, and waits for a packet
        in response. Optionally, checks whether the received packet type is
        matches that the caller expects.

        :param packet: The thorlabs data packet that will be queried
        :type packet: `ThorLabsPacket`
        """
        self._file.write_raw(packet.pack())

    # pylint: disable=protected-access
    def readpacket(self, expect=None, timeout=None):
        """
        Reads packets from a device and filters them based on a optional
        expected value.
        
        :param expect: The expected message id from the response. If an
            an incorrect id is received then it is added to a buffer and
            it continues reading until either the right response is recieved
            or the timeout is hit. If left with the default value of `None` 
            then no checking occurs.
        :type expect: `str` or `None`

        :param timeout: Sets a timeout to wait before returning `None`, indicating
            no packet was received. If the timeout is set to `None`, then the
            timeout is inherited from the underlying communicator and no additional
            timeout is added. If timeout is set to `False`, then this method waits
            indefinitely. If timeout is set to a unitful quantity, then it is interpreted
            as a time and used as the timeout value. Finally, if the timeout is a unitless
            number (e.g. `float` or `int`), then seconds are assumed.

        :return: Returns the response back from the instrument wrapped up in
            a ThorLabs APT packet, or None if no packet was received.

        :rtype: `ThorLabsPacket`
        """
        if timeout:
            timeout = assume_units(timeout, second).rescale('second').magnitude
        t_start = time.time()

        while True:
            # read the next packet
            resp = self._file.read_raw()
            # if the packet is not empty, process it
            if resp != b"":
                # unpack the TL data format
                pkt = _packets.ThorLabsPacket.unpack(resp)
                resp_id = pkt._message_id
                if resp is None:
                    break
                # one shot/you got what you wanted
                elif (timeout is None) or (resp_id == expect):
                    break
                # if you didnt get the expected message, add it to a list.
                else:
                    self._packet_queue[resp_id].append(pkt)
            # the packet was empty so for error reporting its empty
            else:
                resp_id = "empty"

            # check to see if we have been reading long enough
            tic = time.time()
            if not (timeout == False):
                if tic - t_start > timeout:
                    raise TimeoutError("APT has faild to read the expected message"
                                    "ID within the device timeout. Last message"
                                    " was {}, was looking for {}".format(
                                        resp_id, expect))
        if resp is None:
            if expect is None:
                return None
            else:
                raise IOError("Expected packet {}, got nothing instead.".format(
                    expect
                ))
        if expect is not None and pkt._message_id != expect:
            raise IOError("APT returned message ID {}, expected {}".format(
                pkt._message_id, expect
            ))

        return pkt


    # pylint: disable=protected-access
    def querypacket(self, packet, expect=None, timeout=None):
        """
        Sends a packet to the connected APT instrument, and waits for a packet
        in response. Optionally, checks whether the received packet type is
        matches that the caller expects.

        :param packet: The thorlabs data packet that will be queried
        :type packet: `ThorLabsPacket`

        :param expect: The expected message id from the response. If an
            an incorrect id is received then an `IOError` is raised. If left
            with the default value of `None` then no checking occurs.
        :type expect: `str` or `None`

        :param timeout: Sets a timeout to wait before returning `None`, indicating
            no packet was received. If the timeout is set to `None`, then the
            timeout is inherited from the underlying communicator and no additional
            timeout is added. If timeout is set to `False`, then this method waits
            indefinitely. If timeout is set to a unitful quantity, then it is interpreted
            as a time and used as the timeout value. Finally, if the timeout is a unitless
            number (e.g. `float` or `int`), then seconds are assumed.

        :return: Returns the response back from the instrument wrapped up in
            a ThorLabs APT packet, or None if no packet was received.
        :rtype: `ThorLabsPacket`
        """
        self._file.write_raw(packet.pack())
        # print(["expect in querry", expect])
        read = self.readpacket(expect=expect, timeout=timeout)
        # print([type(read),read])
        return read
