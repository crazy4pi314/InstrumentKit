#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# tc200.py: class for the Thorlabs TC200 Temperature Controller
#
# © 2016 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# TC200 Class contributed by Catherine Holloway
#
"""
Provides the support for the Thorlabs TC200 temperature controller.

Class originally contributed by Catherine Holloway.
"""

# IMPORTS #####################################################################

from __future__ import absolute_import
from __future__ import division
from builtins import range, map

import quantities as pq
from enum import IntEnum, Enum

from instruments.abstract_instruments import Instrument
from instruments.util_fns import convert_temperature
from instruments.util_fns import enum_property, unitful_property, int_property

# CLASSES #####################################################################


class TC200(Instrument):

    """
    The TC200 is is a controller for the voltage across a heating element.
    It can also read in the temperature off of a thermistor and implements
    a PID control to keep the temperature at a set value.

    The user manual can be found here:
    http://www.thorlabs.com/thorcat/12500/TC200-Manual.pdf
    """

    def __init__(self, filelike):
        super(TC200, self).__init__(filelike)
        self.terminator = "\r"
        self.prompt = ">"

    def _ack_expected(self, msg=""):
        return msg

    # ENUMS #

    class Mode(IntEnum):

        """
        Enum containing valid output modes of the TC200.
        """
        normal = 0
        cycle = 1

    class Sensor(Enum):

        """
        Enum containing valid temperature sensor types for the TC200.
        """
        ptc100 = "ptc100"
        ptc1000 = "ptc1000"
        th10k = "th10k"
        ntc10k = "ntc10k"

    # PROPERTIES #

    def name(self):
        """
        Gets the name and version number of the device

        :return: the name string of the device
        :rtype: str
        """
        response = self.query("*idn?")
        return response

    @property
    def mode(self):
        """
        Gets/sets the output mode of the TC200

        :type: `TC200.Mode`
        """
        response = self.query("stat?")
        response_code = (int(response) >> 1) % 2
        return TC200.Mode(response_code)

    @mode.setter
    def mode(self, newval):
        if not isinstance(newval, TC200.Mode):
            raise TypeError("Mode setting must be a `TC200.Mode` value, "
                            "got {} instead.".format(type(newval)))
        out_query = "mode={}".format(newval.name)
        self.sendcmd(out_query)

    @property
    def enable(self):
        """
        Gets/sets the heater enable status.

        If output enable is on (`True`), there is a voltage on the output.

        :type: `bool`
        """
        response = self.query("stat?")
        return True if int(response) % 2 is 1 else False

    @enable.setter
    def enable(self, newval):
        if not isinstance(newval, bool):
            raise TypeError("TC200 enable property must be specified with a "
                            "boolean.")
        # the "ens" command is a toggle, we need to track two different cases,
        # when it should be on and it is off, and when it is off and
        # should be on
        if newval and not self.enable:
            self.sendcmd("ens")
        elif not newval and self.enable:
            self.sendcmd("ens")

    temperature = unitful_property(
        "tact",
        units=pq.degC,
        readonly=True,
        input_decoration=lambda x: x.replace(
            " C", "").replace(" F", "").replace(" K", ""),
        doc="""
        Gets the actual temperature of the sensor

        :units: As specified (if a `~quantities.quantity.Quantity`) or assumed
            to be of units degrees C.
        :type: `~quantities.quantity.Quantity` or `int`
        :return: the temperature (in degrees C)
        :rtype: `~quantities.quantity.Quantity`
        """
    )

    max_temperature = unitful_property(
        "tmax",
        units=pq.degC,
        format_code="{:.1f}",
        set_fmt="{}={}",
        valid_range=(20, 205),
        doc="""
        Gets/sets the maximum temperature

        :return: the maximum temperature (in deg C)
        :units: As specified or assumed to be degree Celsius. Returns with
            units degC.
        :rtype: `~quantities.quantity.Quantity`
        """
    )

    @property
    def temperature_set(self):
        """
        Gets/sets the actual temperature of the sensor

        :units: As specified (if a `~quantities.quantity.Quantity`) or assumed
            to be of units degrees C.
        :type: `~quantities.quantity.Quantity` or `int`
        :return: the temperature (in degrees C)
        :rtype: `~quantities.quantity.Quantity`
        """
        response = self.query("tset?").replace(
            " C", "").replace(" F", "").replace(" K", "")
        return float(response) * pq.degC

    @temperature_set.setter
    def temperature_set(self, newval):
        # the set temperature is always in celsius
        newval = convert_temperature(newval, pq.degC).magnitude
        if newval < 20.0 or newval > self.max_temperature:
            raise ValueError("Temperature set is out of range.")
        out_query = "tset={}".format(newval)
        self.sendcmd(out_query)

    @property
    def p(self):
        """
        Gets/sets the p-gain. Valid numbers are [1,250].

        :return: the p-gain (in nnn)
        :rtype: `int`
        """
        return self.pid[0]

    @p.setter
    def p(self, newval):
        if newval not in range(1, 251):
            raise ValueError("P-value not in [1, 250]")
        self.sendcmd("pgain={}".format(newval))

    @property
    def i(self):
        """
        Gets/sets the i-gain. Valid numbers are [1,250]

        :return: the i-gain (in nnn)
        :rtype: `int`
        """
        return self.pid[1]

    @i.setter
    def i(self, newval):
        if newval not in range(0, 251):
            raise ValueError("I-value not in [0, 250]")
        self.sendcmd("igain={}".format(newval))

    @property
    def d(self):
        """
        Gets/sets the d-gain. Valid numbers are [0, 250]

        :return: the d-gain (in nnn)
        :type: `int`
        """
        return self.pid[2]

    @d.setter
    def d(self, newval):
        if newval not in range(0, 251):
            raise ValueError("D-value not in [0, 250]")
        self.sendcmd("dgain={}".format(newval))

    @property
    def pid(self):
        """
        Gets/sets all three PID values at the same time. See `TC200.p`,
        `TC200.i`, and `TC200.d` for individual restrictions.

        If `None` is specified then the corresponding PID value is not changed.

        :return: List of integers of PID values. In order [P, I, D].
        :type: `list` or `tuple`
        :rtype: `list`
        """
        return list(map(int, self.query("pid?").split()))

    @pid.setter
    def pid(self, newval):
        if not isinstance(newval, list) and not isinstance(newval, tuple):
            raise TypeError("Setting PID must be specified as a list or tuple")
        if newval[0] is not None:
            self.p = newval[0]
        if newval[1] is not None:
            self.i = newval[1]
        if newval[2] is not None:
            self.d = newval[2]

    @property
    def degrees(self):
        """
        Gets/sets the units of the temperature measurement.

        :return: The temperature units (degC/F/K) the TC200 is measuring in
        :type: `~quantities.unitquantity.UnitTemperature`
        """
        response = self.query("stat?")
        response = int(response)
        if (response >> 4) % 2 and (response >> 5) % 2:
            return pq.degC
        elif (response >> 5) % 2:
            return pq.degK
        else:
            return pq.degF

    @degrees.setter
    def degrees(self, newval):
        if newval is pq.degC:
            self.sendcmd("unit=c")
        elif newval is pq.degF:
            self.sendcmd("unit=f")
        elif newval is pq.degK:
            self.sendcmd("unit=k")
        else:
            raise TypeError("Invalid temperature type")

    sensor = enum_property(
        "sns",
        Sensor,
        input_decoration=lambda x: x.split(
            ",")[0].split("=")[1].strip().lower(),
        set_fmt="{}={}",
        doc="""
        Gets/sets the current thermistor type. Used for converting resistances
        to temperatures.

        :return: The thermistor type
        :type: `TC200.Sensor`
        """
    )

    beta = int_property(
        "beta",
        valid_set=range(2000, 6001),
        set_fmt="{}={}",
        doc="""
        Gets/sets the beta value of the thermistor curve.

        Value within [2000, 6000]

        :return: the gain (in nnn)
        :type: `int`
        """
    )

    max_power = unitful_property(
        "pmax",
        units=pq.W,
        format_code="{:.1f}",
        set_fmt="{}={}",
        valid_range=(0.1, 18.0),
        doc="""
        Gets/sets the maximum power

        :return: The maximum power
        :units: Watts (linear units)
        :type: `~quantities.quantity.Quantity`
        """
    )