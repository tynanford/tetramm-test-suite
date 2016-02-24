

TetrAMM Test Suite
==================

Collection of tests for TetrAMM picoammeter.


TestTetrAMMacq.py
-----------------
Tests free-running acquisiton at 20 kSPS.


TestTetrAMMtrigger.py
---------------------

Using an external function generator, this test provides different stimuli for
external trigger and gate modes.


Modules required:

  * python-vxi11: for communication with Tektronix function generator, to
    generate trigger waveforms

