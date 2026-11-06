.. currentmodule:: pylabrobot.high_res

pylabrobot.high_res package
===========================

.. currentmodule:: pylabrobot.high_res.lid_valet

.. autosummary::
  :toctree: _autosummary
  :nosignatures:
  :recursive:

    HighResLidValet
    HighResLidValetError

.. currentmodule:: pylabrobot.high_res.microspin

.. autosummary::
  :toctree: _autosummary
  :nosignatures:

    MicroSpin
    MicroSpinDriver
    MicroSpinSimulator
    SimulatedMicroSpin
    MicroSpinStatus
    MicroSpinError
    DoorLockPinError
    NotHomedError
    AmplifierDisabledError
    QueueTimeoutError
    MicroSpinAbortedError
    MicroSpinTimeoutError
    MicroSpinProtocolError

.. currentmodule:: pylabrobot.high_res.microspin.server

.. autosummary::
  :toctree: _autosummary
  :nosignatures:

    ServedMicroSpin
    MicroSpinServer
    MicroSpinService
    microspin_server_app
    serve

.. currentmodule:: pylabrobot.high_res.sample_storage

.. autosummary::
  :toctree: _autosummary
  :nosignatures:

    AmbiStore
    EnvironmentControl
    SteriStore
    TundraStore
    UnresolvedPlateTransfer
    high_res_stacker
