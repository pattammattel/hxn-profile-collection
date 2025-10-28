print(f"Loading {__file__!r} ...")

from ophyd import (EpicsMotor, Component as Cpt,
                   MotorBundle, Device)
from hxntools.detectors.trigger_mixins import HxnModalBase

import time

class HxnFastShutter(HxnModalBase, Device):
    request_open = Cpt(EpicsSignal, '')

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)
        self.stage_sigs[self.request_open] = 1
        self.mode_settings.triggers.put([])

    def stage(self):
        print('** Opening fast shutter **')
        super().stage()

    def unstage(self):
        print('** Closing fast shutter **')
        super().unstage()


fs = HxnFastShutter('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', name='fs')

class HxnSlowShutter(HxnModalBase, Device):
    opn = Cpt(EpicsSignal, ':Opn-Cmd')
    cls = Cpt(EpicsSignal, ':Cls-Cmd')

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)

    def stage(self):
        self.opn.put(1)
        time.sleep(2)

    def unstage(self):
        self.cls.put(1)
        time.sleep(2)

bshutter = HxnSlowShutter('XF:03IDB-PPS{PSh}Cmd', name = 'bshutter')




class HxnSSAperture(MotorBundle):
    hgap = Cpt(EpicsMotor, '-Ax:XAp}Mtr')
    vgap = Cpt(EpicsMotor, '-Ax:YAp}Mtr')
    hcen = Cpt(EpicsMotor, '-Ax:X}Mtr')
    vcen = Cpt(EpicsMotor, '-Ax:Y}Mtr')


ssa1 = HxnSSAperture('XF:03IDB-OP{Slt:SSA1', name='ssa1')
ssa2 = HxnSSAperture('XF:03IDC-OP{Slt:SSA2', name='ssa2')

bpm6_y = EpicsMotor('XF:03IDB-OP{BPM:6-Ax:Y}Mtr', name='bpm6_y')

# idb_m1 = EpicsMotor('XF:03IDB-OP{Slt:SSA1-Ax:6}Mtr', name='idb_m1')
# idb_m2 = EpicsMotor('XF:03IDB-OP{Slt:SSA1-Ax:7}Mtr', name='idb_m2')
# idb_m3 = EpicsMotor('XF:03IDB-OP{Slt:SSA1-Ax:8}Mtr', name='idb_m3')

s3 = HxnSlitA('XF:03IDC-OP{Slt:3', name='s3')


class HxnTurboPmacController(MotorBundle):
    m1 = Cpt(EpicsMotor, '-Ax:1}Mtr')
    m2 = Cpt(EpicsMotor, '-Ax:2}Mtr')
    m3 = Cpt(EpicsMotor, '-Ax:3}Mtr')
    m4 = Cpt(EpicsMotor, '-Ax:4}Mtr')
    m5 = Cpt(EpicsMotor, '-Ax:5}Mtr')
    m6 = Cpt(EpicsMotor, '-Ax:6}Mtr')
    m7 = Cpt(EpicsMotor, '-Ax:7}Mtr')
    m8 = Cpt(EpicsMotor, '-Ax:8}Mtr')


# Unpopulated motor controllers:
mc2 = HxnTurboPmacController('XF:03IDC-ES{MC:2', name='mc2')
mc3 = HxnTurboPmacController('XF:03IDC-ES{MC:3', name='mc3')
mc4 = HxnTurboPmacController('XF:03IDC-ES{MC:4', name='mc4')


class HxnSlitB(MotorBundle):
    '''HXN slit device, with X/Y/Z/top'''
    vgap = Cpt(EpicsMotor, '-Ax:X}Mtr')
    vcen = Cpt(EpicsMotor, '-Ax:Y}Mtr')
    hgap = Cpt(EpicsMotor, '-Ax:Z}Mtr')
    hcen = Cpt(EpicsMotor, '-Ax:Top}Mtr')


s4 = HxnSlitB('XF:03IDC-ES{Slt:4', name='s4')

# mc6_m5 = EpicsMotor('XF:03IDC-ES{MC:6-Ax:5}Mtr', name='mc6_m5')
# mc6_m6 = EpicsMotor('XF:03IDC-ES{MC:6-Ax:6}Mtr', name='mc6_m6')
# mc6_m7 = EpicsMotor('XF:03IDC-ES{MC:6-Ax:7}Mtr', name='mc6_m7')

bpm7_y = EpicsMotor('XF:03IDC-ES{BPM:7-Ax:Y}Mtr', name='bpm7_y')

mc7 = HxnTurboPmacController('XF:03IDC-ES{MC:7', name='mc7')

# questar_f = EpicsMotor('XF:03IDC-ES{MC:8-Ax:1}Mtr', name='questar_f')

mc8 = HxnTurboPmacController('XF:03IDC-ES{MC:8', name='mc8')
# mc9 = HxnTurboPmacController('XF:03IDC-ES{MC:9', name='mc9')


class HxnSlitC(MotorBundle):
    '''HXN slit device, with vertical/horizontal gaps/centers'''
    vgap = Cpt(EpicsMotor, '-Ax:Vgap}Mtr')
    vcen = Cpt(EpicsMotor, '-Ax:Vcen}Mtr')
    hgap = Cpt(EpicsMotor, '-Ax:Hgap}Mtr')
    hcen = Cpt(EpicsMotor, '-Ax:Hcen}Mtr')


s5 = HxnSlitC('XF:03IDC-ES{Slt:5', name='s5')
s6 = HxnSlitC('XF:03IDC-ES{Slt:6', name='s6')


# mc10 = HxnTurboPmacController('XF:03IDC-ES{MC:10', name='mc10')


class HxnDetectorPositioner(MotorBundle):
    '''HXN X/Y positioner device'''
    x = Cpt(EpicsMotor, '-Ax:X}Mtr')
    y = Cpt(EpicsMotor, '-Ax:Y}Mtr')
    z = Cpt(EpicsMotor, '-Ax:Z}Mtr')


fdet1 = HxnDetectorPositioner('XF:03IDC-ES{Det:Vort', name='fdet1')
fdet2 = HxnDetectorPositioner('XF:03IDC-ES{Det:Bruk', name='fdet2')

bs_x = EpicsMotor('XF:03IDC-ES{MC:12-Ax:4}Mtr', name='bs_x')
bs_y = EpicsMotor('XF:03IDC-ES{MC:12-Ax:5}Mtr', name='bs_y')


difftrans_x = EpicsMotor('XF:03IDC-ES{MC:14-Ax:1}Mtr', name='DiffTransX')
difftrans_y = EpicsMotor('XF:03IDC-ES{MC:14-Ax:2}Mtr', name='DiffTransY')
difftrans_z = EpicsMotor('XF:03IDC-ES{MC:14-Ax:3}Mtr', name='DiffTransZ')


mc12 = HxnTurboPmacController('XF:03IDC-ES{MC:12', name='mc12')


class DetectorStation(PseudoPositioner):
    # Real axis
    z = Cpt(EpicsMotor, '-Ax:Z}Mtr')
    x = Cpt(EpicsMotor, '-Ax:X}Mtr')
    y1 = Cpt(EpicsMotor, '-Ax:Y1}Mtr')
    y2 = Cpt(EpicsMotor, '-Ax:Y2}Mtr')
    yaw = Cpt(EpicsMotor, '-Ax:Yaw}Mtr')
    cx = Cpt(EpicsMotor, '-Ax:C1}Mtr')
    cy = Cpt(EpicsMotor, '-Ax:C2}Mtr')
    cz = Cpt(EpicsMotor, '-Ax:C3}Mtr')

    # pseudo axis
    gamma = Cpt(PseudoSingle)
    delta = Cpt(PseudoSingle)
    r = Cpt(PseudoSingle)

    @pseudo_position_argument
    def forward(self, position):
        gamma = np.deg2rad(position.gamma)
        delta = np.deg2rad(position.delta)
        r = position.r

        beta = np.deg2rad(89.337)

        diff_z = self.z.position

        z_yaw = 574.668 + 581.20 + diff_z
        z1 = 574.668 + 395.2 + diff_z
        z2 = z1 + 380
        d = 395.2

        x_yaw = np.sin(gamma) * z_yaw / np.sin(beta + gamma)
        R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
        R1 = R_yaw - (z_yaw - z1)
        R2 = R_yaw - (z_yaw - z2)
        y1 = np.tan(delta) * R1
        y2 = np.tan(delta) * R2
        R_det = R1 / np.cos(delta) - d
        dz = r - R_det
        if x_yaw > 787 or x_yaw < -200:
            raise ValueError(f'diff_x = {-x_yaw}'
                              ' out of range, move diff_z '
                              'upstream and try again')
        elif dz < -250 or dz > 0:
            raise ValueError(f'diff_cz = {dz}'
                              ' out of range, move diff_z up or down stream and try again')
        elif y1 > 750:
            raise ValueError(f'diff_y1 = {y1} out of range, move diff_z upstream '
                  'and try again')
        elif y2 > 1000:
            raise ValueError(f'diff_y2 = {y2} out of range, move diff_z upstream '
                  'and try again')

        return self.RealPosition(z=diff_z,
                                 x=-x_yaw,
                                 y1=y1,
                                 y2=y2,
                                 yaw=np.rad2deg(gamma),
                                 cx=self.cx.position,
                                 cy=self.cy.position,
                                 cz=dz)

    @real_position_argument
    def inverse(self, position):
        diff_z = position.z
        diff_yaw = np.deg2rad(position.yaw)
        diff_cz = position.cz
        diff_x = position.x
        diff_y1 = position.y1
        diff_y2 = position.y2

        gamma = diff_yaw
        beta = 89.337 * np.pi / 180
        z_yaw = 574.668 + 581.20 + diff_z
        z1 = 574.668 + 395.2 + diff_z
        z2 = z1 + 380
        d = 395.2

        x_yaw = np.sin(gamma) * z_yaw / np.sin(beta + gamma)
        R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
        R1 = R_yaw - (z_yaw - z1)
        R2 = R_yaw - (z_yaw - z2)


        if abs(x_yaw + diff_x) > 3:
            gamma = delta = r = np.nan
        elif abs(diff_y1 / R1 - diff_y2 / R2) > 0.01:
            gamma = delta = r = np.nan
        else:
            delta = np.arctan(diff_y1 / R1)
            r = R1 / np.cos(delta) - d + diff_cz

        return self.PseudoPosition(gamma=np.rad2deg(gamma),
                                   delta=np.rad2deg(delta),
                                   r=r)


diff = DetectorStation('XF:03IDC-ES{Diff', name='diff')
s7 = HxnSlitC('XF:03IDC-ES{Slt:7', name='s7')
