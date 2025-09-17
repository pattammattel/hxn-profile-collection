print(f"Loading {__file__!r} ...")

import math

from ophyd import (PVPositionerPC, EpicsMotor, Signal, EpicsSignal,
                   EpicsSignalRO, Component as Cpt, FormattedComponent as FCpt,
                   PseudoSingle, PseudoPositioner,
                   )

from ophyd.pseudopos import (real_position_argument,
                             pseudo_position_argument)


from hxntools.device import NamedDevice


class SmarpodBase(PVPositionerPC):
    readback = FCpt(EpicsSignal, '')  # readback placeholder
    actuate = Cpt(EpicsSignal, 'XF:03IDC-ES{SPod:1}Move-Cmd.PROC')
    actuate_value = 1
    done = Cpt(EpicsSignalRO, 'XF:03IDC-ES{SPod:1}Moving-I')
    done_value = 1

    def __init__(self, prefix='', axis=0, **kwargs):
        self.axis = axis
        super().__init__(prefix='', **kwargs)


class SmarpodTranslationAxis(SmarpodBase):
    setpoint = FCpt(EpicsSignal,
                    'XF:03IDC-ES{{SPod:1-Ax:{self.axis}}}Pos-SP')
    readback = FCpt(EpicsSignal,
                    'XF:03IDC-ES{{SPod:1-Ax:{self.axis}}}Pos-I')


class SmarpodRotationAxis(SmarpodBase):
    setpoint = FCpt(EpicsSignal,
                    'XF:03IDC-ES{{SPod:1-Ax:{self.axis}}}Rot-SP')
    readback = FCpt(EpicsSignal,
                    'XF:03IDC-ES{{SPod:1-Ax:{self.axis}}}Rot-I')


class HxnZPSample(NamedDevice):
    # Zoneplate module fine sample stage axes (closed on cap
    # sensors/interferometer)
    zpssx = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-zpssx}Mtr', doc='fine x', timeout = 120)
    zpssy = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-zpssy}Mtr', doc='fine y', timeout = 120)
    zpssz = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-zpssz}Mtr', doc='fine z', timeout = 120)

    # rotary underneath sample
    zpsth = Cpt(EpicsMotor, 'XF:03IDC-ES{SC210:1-Ax:1}Mtr', doc='theta')
    # PI controller underneath smarpod
    zpsx = Cpt(EpicsMotor, 'XF:03IDC-ES{ZpPI:1-zpsx}Mtr', doc='coarse x')
    zpsz = Cpt(EpicsMotor, 'XF:03IDC-ES{ZpPI:1-zpsz}Mtr', doc='coarse z')

    smarx = Cpt(SmarpodTranslationAxis, axis=2, doc='smarpod x')
    smary = Cpt(SmarpodTranslationAxis, axis=3, doc='smarpod y')
    smarz = Cpt(SmarpodTranslationAxis, axis=1, doc='smarpod z')
    smarthx = Cpt(SmarpodRotationAxis, axis=2, doc='smarpod theta around x')
    smarthy = Cpt(SmarpodRotationAxis, axis=3, doc='smarpod theta around y')
    smarthz = Cpt(SmarpodRotationAxis, axis=1, doc='smarpod theta around z')

    kill = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1-ZP}Kill-Cmd.PROC', kind='omitted')
    zero = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1-ZP}Zero-Cmd.PROC', kind='omitted')
    mode = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1-ZP}Mode-I')


zps = HxnZPSample('', name='zps')
zpsth = zps.zpsth
zpssx = zps.zpssx
zpssy = zps.zpssy
zpssz = zps.zpssz

smarx = zps.smarx
smary = zps.smary
smarz = zps.smarz


#zps = remove_names_maybe(zps, ['kill', 'zero'])


class HxnZP_OSA(NamedDevice):
    zposax = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:5-Ax:0}Mtr', doc='coarse x')
    zposay = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:5-Ax:1}Mtr', doc='coarse y')
    zposaz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:5-Ax:2}Mtr', doc='coarse z')


zposa = HxnZP_OSA('', name='zposa')


class HxnZPBeamStop(NamedDevice):
    # The SmarAct MCS was previously used for the beamstop:
    # zpbsx = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:1}Mtr', doc='bs coarse x')
    # zpbsy = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:3}Mtr', doc='bs coarse y')
    # zpbsz = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:2}Mtr', doc='bs coarse z')
    # The MCS is now being used for ptycho (prototype) p_bsx/p_bsy/p_bsz
    zpbsx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:0}Mtr', doc='bs coarse x')
    zpbsy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:1}Mtr', doc='bs coarse y')
    zpbsz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:2}Mtr', doc='bs coarse z')


zpbs = HxnZPBeamStop('', name='zpbs')


class HxnZonePlate(NamedDevice):
    # TPA stage holding the ZP (underneath long travel range stage)
    zpx = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:2-Ax:zpx}Mtr', doc='coarse zp x')
    zpy = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:2-Ax:zpy}Mtr', doc='coarse zp y')
    zpz = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:2-Ax:zpz}Mtr', doc='coarse zp z')
    # zpsx = Cpt(EpicsMotor, 'XF:03IDC-ES{ZpPI:1-zpsx}Mtr', doc = 'base x')
    # zpsz = Cpt(EpicsMotor, 'XF:03IDC-ES{ZpPI:1-zpsz}Mtr', doc = 'base z')


    # long travel range z holding the ZP
    zpz1 = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:1-Ax:zpz1}Mtr', doc='long range z')


zp = HxnZonePlate('', name='zp')
# zpsx = zp.zpsx
# zpsz = zp.zpsz

class FineSampleLabX(PseudoPositioner, NamedDevice):
    '''Pseudo positioner definition for zoneplate fine sample positioner
    with angular correction
    '''
    # pseudo axes
    zpssx_lab = Cpt(PseudoSingle)
    zpssz_lab = Cpt(PseudoSingle)

    # real axes
    zpssx = Cpt(EpicsMotor, '{Ppmac:1-zpssx}Mtr')
    zpssz = Cpt(EpicsMotor, '{Ppmac:1-zpssz}Mtr')

    # configuration settings
    theta0 = Cpt(Signal, value=0.0, doc='theta offset')

    def __init__(self, prefix, **kwargs):
        self.zpsth = EpicsMotor(prefix + '{SC210:1-Ax:1}Mtr', name='zpsth')

        super().__init__(prefix, **kwargs)

        # if theta changes, update the pseudo position
        self.theta0.subscribe(self.parameter_updated)

    def parameter_updated(self, value=None, **kwargs):
        self._update_position()

    @property
    def radian_theta(self):
        return math.radians(self.zpsth.position + self.theta0.get())

    @pseudo_position_argument
    def forward(self, position):
        theta = self.radian_theta
        c = math.cos(theta)
        s = math.sin(theta)

        x = c * position.zpssx_lab + s * position.zpssz_lab
        z = -s * position.zpssx_lab + c * position.zpssz_lab
        return self.RealPosition(zpssx=x, zpssz=z)

    @real_position_argument
    def inverse(self, position):
        theta = self.radian_theta
        c = math.cos(theta)
        s = math.sin(theta)
        x = c * position.zpssx - s * position.zpssz
        z = s * position.zpssx + c * position.zpssz
        return self.PseudoPosition(zpssx_lab=x, zpssz_lab=z)


zplab = FineSampleLabX('XF:03IDC-ES', name='zplab')
zpssx_lab = zplab.zpssx_lab
zpssz_lab = zplab.zpssz_lab
