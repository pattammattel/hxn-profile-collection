print(f"Loading {__file__!r} ...")

import math
from ophyd import (EpicsMotor, Device, Component as Cpt,
                   EpicsSignalRO, PseudoPositioner, PseudoSingle,
                   EpicsSignal, MotorBundle)
from ophyd.device import FormattedComponent as FCpt
from ophyd.pseudopos import (real_position_argument,
                             pseudo_position_argument)
from hxntools.device import NamedDevice


class BeamlineStatus(Device):
    shutter_status = Cpt(EpicsSignalRO, 'SR-EPS{PLC:1}Sts:MstrSh-Sts')
    beam_current = Cpt(EpicsSignalRO, 'SR:C03-BI{DCCT:1}I:Real-I')
    beamline_enabled = Cpt(EpicsSignalRO,
                           'SR:C03-EPS{PLC:1}Sts:ID_BE_Enbl-Sts')
    cryo_filling = Cpt(EpicsSignalRO,
                           'XF:03IDA-OP{CC:1}V3_STS')


beamline_status = BeamlineStatus('', name='beamline_status')


class PseudoEnergyCal(PseudoPositioner, NamedDevice):
    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)

        # if theta changes, update the pseudo position
        self.mono_angle.subscribe(self.parameter_updated)
        # self.energy.subscribe(self.parameter_updated)

    def parameter_updated(self, value=None, **kwargs):
        self._update_position()

    @pseudo_position_argument
    def forward(self, position):
        angle = math.asin((12.39842)/(2 * 3.1355893 * position.energy)) * (180/math.pi)
        return self.RealPosition(mono_angle=angle)

    @real_position_argument
    def inverse(self, position):
        energy_kev = 12.39842 / (2. * 3.1355893 * math.sin(position.mono_angle*math.pi/180.))
        return self.PseudoPosition(energy=energy_kev)


class PseudoEnergyMotor(PseudoEnergyCal):
    energy = Cpt(PseudoSingle, name='energy')
    energy_setting = Cpt(EpicsSignal, 'XF:03ID{}Energy-SP')

    mono_angle = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:Bragg}Mtr')


monoe = PseudoEnergyMotor('', name='monoe')
e = monoe.energy
e_angle = monoe.mono_angle


class HxnDCM(MotorBundle):
    '''HXN DCM Device'''
    th = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:Bragg}Mtr')
    x = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:X}Mtr')
    p = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:P}Mtr')
    r = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:R}Mtr')
    # pf = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:PF}Mtr')
    # rf = Cpt(EpicsMotor, 'XF:03IDA-OP{Mon:1-Ax:RF}Mtr')


dcm = HxnDCM('', name='dcm')
# dcmth = dcm.th


class HxnMirror1(MotorBundle):
    '''HXN Mirror 1 device (HCM)'''
    x = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:1-Ax:X}Mtr')
    y = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:1-Ax:Y}Mtr')
    p = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:1-Ax:P}Mtr')
    b = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:1-Ax:Bend}Mtr')
    #pf = Cpt(EpicsMotor, 'XF:03IDA-OP{HCM:1-Ax:PF}Mtr')


m1 = HxnMirror1('', name='m1')


class HxnMirror2(MotorBundle):
    '''HXN Mirror 2 device (HFM)'''
    x = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:2-Ax:X}Mtr')
    y = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:2-Ax:Y}Mtr')
    p = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:2-Ax:P}Mtr')
    b = Cpt(EpicsMotor, 'XF:03IDA-OP{Mir:2-Ax:Bend}Mtr')
    pf = Cpt(EpicsMotor, 'XF:03IDA-OP{HFM:1-Ax:PF}Mtr')


m2 = HxnMirror2('', name='m2')


class HxnVMS(MotorBundle):
    '''HXN DCM Device'''
    y = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:Y}Mtr')
    p = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:P}Mtr')
    yu = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:YU}Mtr')
    yd = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:YD}Mtr')
    tx = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:TX}Mtr')
    ys = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:YS}Mtr')
    #p_rdbk = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:PRbk}Mtr}')
    #p_rdbk was disconnected
    pf = Cpt(EpicsMotor, 'XF:03IDA-OP{VMS:1-Ax:PF}Mtr')



vms = HxnVMS('', name='vms')
# dcmth = dcm.th


class HxnSlitA(Device):
    '''HXN slit device, with top/bottom/inboard/outboard'''
    bot = Cpt(EpicsMotor, '-Ax:Btm}Mtr')
    top = Cpt(EpicsMotor, '-Ax:Top}Mtr')
    inb = Cpt(EpicsMotor, '-Ax:Inb}Mtr')
    outb = Cpt(EpicsMotor, '-Ax:Outb}Mtr')


class HxnSlitA1(HxnSlitA):
    #           ^^^^^^^^ means it includes 'bot, top, inb, outb' too
    # x, y position from the i400 IOC:
    xpos = FCpt(EpicsSignalRO, 'XF:03IDA-BI{{Slt:1}}PosX-I')
    ypos = FCpt(EpicsSignalRO, 'XF:03IDA-BI{{Slt:1}}PosY-I')


s1 = HxnSlitA1('XF:03IDA-OP{Slt:1', name='s1')
s2 = HxnSlitA('XF:03IDA-OP{Slt:2', name='s2')


class HxnI400(Device):
    '''HXN I400 BPM current readout'''
    # raw currents
    i_top = Cpt(EpicsSignalRO, 'I:Raw1-I')
    i_bottom = Cpt(EpicsSignalRO, 'I:Raw2-I')
    i_right = Cpt(EpicsSignalRO, 'I:Raw3-I')
    i_left = Cpt(EpicsSignalRO, 'I:Raw4-I')

    # x/y position
    x = Cpt(EpicsSignalRO, 'PosX-I')
    y = Cpt(EpicsSignalRO, 'PosY-I')


# Slit 1 BPM (drain current from I400)
s1_bpm = HxnI400('XF:03IDA-BI{Slt:1}', name='s1_bpm')


class HxnXYPositioner(MotorBundle):
    '''HXN X/Y positioner device'''
    x = Cpt(EpicsMotor, '-Ax:X}Mtr')
    y = Cpt(EpicsMotor, '-Ax:Y}Mtr')


class HxnXYPitchPositioner(MotorBundle):
    '''HXN X/Y/Pitch positioner'''
    x = Cpt(EpicsMotor, '-Ax:X}Mtr')
    y = Cpt(EpicsMotor, '-Ax:Y}Mtr')
    p = Cpt(EpicsMotor, '-Ax:P}Mtr')


cam6 = HxnXYPositioner('XF:03IDC-OP{Stg:CAM6', name='cam6')
FPDet = HxnXYPositioner('XF:03IDC-ES{Stg:FPDet', name='cam6')
fs1_y = EpicsMotor('XF:03IDA-OP{FS:1-Ax:Y}Mtr', name='fs1_y')

bpm1 = HxnXYPositioner('XF:03IDA-OP{BPM:1', name='bpm1')
bpm2 = HxnXYPositioner('XF:03IDA-OP{BPM:2', name='bpm2')
bpm3_x = EpicsMotor('XF:03IDA-OP{BPM:3-Ax:X}Mtr', name='bpm3_x')
bpm4_y = EpicsMotor('XF:03IDA-OP{BPM:4-Ax:Y}Mtr', name='bpm4_y')
bpm5_y = EpicsMotor('XF:03IDA-OP{BPM:5-Ax:Y}Mtr', name='bpm5_y')

# Diagnostic Manipulators
fl1_y = EpicsMotor('XF:03IDA-OP{Flr:1-Ax:Y}Mtr', name='fl1_y')
fl2_y = EpicsMotor('XF:03IDA-OP{Flr:2-Ax:Y}Mtr', name='fl2_y')

crl = HxnXYPitchPositioner('XF:03IDA-OP{Lens:CRL', name='crl')


# # nanoBPM2@SSA1
# nano2y = EpicsMotor('XF:03IDB-OP{BPM:6-Ax:Y}Mtr', name='nano2y')
#
# # nanoBPM3@SSA2
# nano3y = EpicsMotor('XF:03IDC-OP{BPM:7-Ax:Y}Mtr', name='nano3y')

qbpm_x = EpicsMotor('XF:03IDB-OP{Slt:SSA1-Ax:8}Mtr', name='qbpm_x')
qbpm_y = EpicsMotor('XF:03IDB-OP{Slt:SSA1-Ax:7}Mtr', name='qbpm_y')

#bpm_set_y = EpicsSignalRO('XF:03ID-BI{EM:BPM1}fast_pidY')


    

