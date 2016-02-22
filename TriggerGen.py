# -*- coding: utf-8 -*-
"""
Created on Sat Feb 20 17:37:26 2016

@author: jan
"""


import abc
import time

import vxi11


class TriggerGen(metaclass=abc.ABCMeta):
    ''' Abstract class for function generator '''
    @abc.abstractmethod
    def set_output_enable(self, enable):
        ''' Enables and disables function generator output

        Args:
            enable: if true, output should be enabled
        '''
        pass

    @abc.abstractmethod
    def set_pulse(self, freq_hz, duration_s):
        ''' Sets pulse parameter (frequency and duration)

        Args:
            freq: in hertz
            duration: in seconds
        '''
        pass


class TriggerGenTektronix(TriggerGen):
    ''' Trigger generation with Tektronix AFG3022B

    manual:
        http://mmrc.caltech.edu/Tektronics/AFG3021B/
        AFG3021B%20Programmer%20Manual.pdf
    '''

    def __init__(self, ip_addr_str):
        self.instr = vxi11.Instrument(ip_addr_str)
        print('Trigger gen:' + self.instr.ask("*IDN?"))

        self.instr.write('*RST')

        self.instr.write('SOURCE1:FUNCTION PULSE')
        self.instr.write('SOURCE1:VOLTage:LEVel:HIGH 3.3V')
        self.instr.write('SOURCE1:VOLTage:LEVel:LOW 0V')

        self._check_levels()

    def __del__(self):
        self.instr.close()

    def _check_levels(self):
        ''' check once again to not cause any damage

        Raises:
            RuntimeError: if the output is not configured properly
        '''
        high_level_str = self.instr.ask('SOURCE1:VOLTage:LEVel:HIGH?')
        high_level = float(high_level_str)

        low_level_str = self.instr.ask('SOURCE1:VOLTage:LEVel:LOW?')
        low_level = float(low_level_str)

        if high_level != 3.3:
            raise RuntimeError('The func gen setting is incorrect (high={})'.
                               format(high_level))

        if low_level != 0.0:
            raise RuntimeError('The func gen setting is incorrect (low={})'.
                               format(low_level))

    def set_output_enable(self, enable):
        self.instr.write('OUTPUT1:STATE {0}'.format('ON' if enable else 'OFF'))

    def set_pulse(self, freq_hz, duration_s):
        self.instr.write('SOURCE1:FREQUENCY {freq}'.format(freq=freq_hz))
        self.instr.write('SOURce1:PULSe:WIDTh {dur_us}us'.
                         format(dur_us=duration_s*1e6))


class TriggerGenManual(TriggerGen):
    ''' Trigger generation with user input '''
    def set_output_enable(self, enable):
        print(' [USER] set output enable to {0}'.
              format('ON' if enable else 'OFF'))
        input(' [USER]     press any key to continue...')

    def set_pulse(self, freq_hz, duration_s):
        print(' [USER] set freq to {freq} Hz, duration to {dur}'.
              format(freq=freq_hz, dur=duration_s))
        input(' [USER]     press any key to continue...')


if __name__ == '__main__':
    for trg_gen in [TriggerGenTektronix('192.168.1.151'), TriggerGenManual()]:
        trg_gen.set_output_enable(False)
        trg_gen.set_pulse(5, 50e-6)
        trg_gen.set_output_enable(True)
        time.sleep(1)
        trg_gen.set_output_enable(False)
