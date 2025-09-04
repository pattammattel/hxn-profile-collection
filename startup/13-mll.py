print(f"Loading {__file__!r} ...")

import math
from ophyd import (Device, EpicsMotor, Signal, Component as Cpt,
                   PseudoSingle, PseudoPositioner, EpicsSignal)

from ophyd.pseudopos import (real_position_argument,
                             pseudo_position_argument)

from hxntools.device import NamedDevice


def remove_names_maybe(obj, names):
    for n in names:
        try:
            obj.read_attrs.remove(n)
        except (ValueError, AttributeError, KeyError):
            pass
    return obj


# NOTE: NamedDevice will name components exactly as the 'name' argument
#       specifies. Normally, it would be named based on the parent

class HxnMLLSample(NamedDevice):
    ssx = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-ssx}Mtr', doc='fine_x')
    ssy = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-ssy}Mtr', doc='fine_y')
    ssz = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-ssz}Mtr', doc='fine_z')
    sth = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:1-Ax:0}Mtr', doc='theta')

    sxx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:5}Mtr', doc='coarse x')
    sy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:0}Mtr', doc='coarse y')
    sx1 = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:1}Mtr', doc='coarse x1')
    sz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:2}Mtr', doc='coarse z')

    kill = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1}KillAll-Cmd.PROC',
               doc='kill all piezos', kind='omitted')
    zero = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1}KillZero-Cmd.PROC',
               doc='zero all piezos', kind='omitted')
    # sz1 = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:3}Mtr', doc='coarse z1')
    # sz1 was replaced with vz when controller 2 died


smll = HxnMLLSample('', name='smll')
ssx = smll.ssx
ssy = smll.ssy
ssz = smll.ssz

sth = smll.sth

sx = smll.sxx
sy = smll.sy
sx1 = smll.sx1
sz = smll.sz
# sz1 = smll.sz1


smll = remove_names_maybe(smll, ['kill', 'zero'])


class HxnMLLDiffractionSample(NamedDevice):
    '''MLL diffraction sample scanning stages'''
    dsy = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:1-Ax:mlldiffy}Mtr', doc='dsy')
    dsx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:6-Ax:2}Mtr', doc='dsx')
    dsz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:6-Ax:3}Mtr', doc='dsz')
    dsth = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:diffsth}Mtr', doc='dsth')
    sbx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:5}Mtr', doc='sx')
    sbz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:2}Mtr', doc='sz')
    # dssx and dssz are swapped, due to the installation. (01/17/17, H. Yan)
    #dssx = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssz}Mtr', doc='fine_x')
    #dssy = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssy}Mtr', doc='fine_y')
    #dssz = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssx}Mtr', doc='fine_z')
    # swap back dssx and dssz (08/07/19, X. Huang)
    dssx = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssx}Mtr', doc='fine_x', timeout = 120)
    dssy = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssy}Mtr', doc='fine_y', timeout = 120)
    dssz = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-dssz}Mtr', doc='fine_z', timeout = 120)

    kill = Cpt(EpicsSignal, 'XF:03IDC-ES{Ppmac:1-Diff}Kill-Cmd.PROC',
               doc='kill all piezos', kind='omitted')


smlld = HxnMLLDiffractionSample('', name='smlld')
dssx = smlld.dssx
dssy = smlld.dssy
dssz = smlld.dssz
dsx = smlld.dsx
dsy = smlld.dsy
dsz = smlld.dsz
dsth = smlld.dsth
sbx = smlld.sbx
sbz = smlld.sbz

smlld = remove_names_maybe(smlld, ['kill', 'zero'])


class HxnAnc350_3(Device):
    '''3 axis ANC350'''
    ax0 = Cpt(EpicsMotor, '-Ax:0}Mtr')
    ax1 = Cpt(EpicsMotor, '-Ax:1}Mtr')
    ax2 = Cpt(EpicsMotor, '-Ax:2}Mtr')


class HxnAnc350_4(Device):
    '''4 axis ANC350'''
    ax0 = Cpt(EpicsMotor, '-Ax:0}Mtr')
    ax1 = Cpt(EpicsMotor, '-Ax:1}Mtr')
    ax2 = Cpt(EpicsMotor, '-Ax:2}Mtr')
    ax3 = Cpt(EpicsMotor, '-Ax:3}Mtr')


class HxnAnc350_6(Device):
    '''6 axis ANC350'''
    ax0 = Cpt(EpicsMotor, '-Ax:0}Mtr')
    ax1 = Cpt(EpicsMotor, '-Ax:1}Mtr')
    ax2 = Cpt(EpicsMotor, '-Ax:2}Mtr')
    ax3 = Cpt(EpicsMotor, '-Ax:3}Mtr')
    ax4 = Cpt(EpicsMotor, '-Ax:4}Mtr')
    ax5 = Cpt(EpicsMotor, '-Ax:5}Mtr')


# Note that different controllers have different axis counts:
anc350_1 = HxnAnc350_6('XF:03IDC-ES{ANC350:1', name='anc350_1')
# anc350 controller 2 is being sent for repairs
# anc350_2 = HxnAnc350_6('XF:03IDC-ES{ANC350:2', name='anc350_2')
anc350_3 = HxnAnc350_4('XF:03IDC-ES{ANC350:3', name='anc350_3')
anc350_4 = HxnAnc350_6('XF:03IDC-ES{ANC350:4', name='anc350_4')
anc350_5 = HxnAnc350_6('XF:03IDC-ES{ANC350:5', name='anc350_5')
anc350_6 = HxnAnc350_6('XF:03IDC-ES{ANC350:6', name='anc350_6')
anc350_7 = HxnAnc350_3('XF:03IDC-ES{ANC350:7', name='anc350_7')
anc350_8 = HxnAnc350_3('XF:03IDC-ES{ANC350:8', name='anc350_8')


class HxnVerticalMLL(NamedDevice):
    # vx, vy now on controller 5
    vx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:5-Ax:3}Mtr', doc='coarse x')
    vy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:5-Ax:4}Mtr', doc='coarse y')
    # vz is now on controller 3
    vz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:3}Mtr', doc='coarse z')
    # vchi, vth now on controller 8
    vchi = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:3}Mtr', doc='chi')
    vth = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:4}Mtr', doc='theta')


vmll = HxnVerticalMLL('', name='vmll')


class HxnHorizontalMLL(NamedDevice):
    # hx now on controller 8
    hx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:8-Ax:5}Mtr', doc='x')
    hy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:0}Mtr', doc='y')
    hz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:1}Mtr', doc='z')
    hth = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:6-Ax:4}Mtr', doc='theta')


hmll = HxnHorizontalMLL('', name='hmll')


class HxnMLL_OSA(NamedDevice):
    osax = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:2}Mtr')
    osay = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:3}Mtr')
    osaz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:4}Mtr')


mllosa = HxnMLL_OSA('', name='mllosa')


class HxnMLLBeamStop(NamedDevice):
    bsx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:6-Ax:0}Mtr')
    bsy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:6-Ax:1}Mtr')


mllbs = HxnMLLBeamStop('', name='mllbs')


class PseudoAngleCorrection(PseudoPositioner, NamedDevice):
    '''Pseudo positioner definition for MLL coarse and fine sample positioners
    with angular correction
    '''

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix, **kwargs)

        # if theta changes, update the pseudo position
        self.theta.subscribe(self.parameter_updated)

    def parameter_updated(self, value=None, **kwargs):
        self._update_position()

    @property
    def radian_theta(self):
        return math.radians(self.theta.get())

    @pseudo_position_argument
    def forward(self, position):
        theta = self.radian_theta
        c = math.cos(theta)
        s = math.sin(theta)

        x = c * position.px + s * position.pz
        z = -s * position.px + c * position.pz
        return self.RealPosition(x=x, z=z)

    @real_position_argument
    def inverse(self, position):
        theta = self.radian_theta
        c = math.cos(theta)
        s = math.sin(theta)
        x = c * position.x - s * position.z
        z = s * position.x + c * position.z
        return self.PseudoPosition(px=x, pz=z)


class PseudoMLLFineSample(PseudoAngleCorrection):
    # pseudo axes
    px = Cpt(PseudoSingle, name='pssx')
    pz = Cpt(PseudoSingle, name='pssz')

    # real axes
    x = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-ssx}Mtr', name='ssx')
    z = Cpt(EpicsMotor, 'XF:03IDC-ES{Ppmac:1-ssz}Mtr', name='ssz')

    # configuration settings
    theta = Cpt(Signal, value=15.0, name='pmllf_theta')


class PseudoMLLCoarseSample(PseudoAngleCorrection):
    # pseudo axes
    px = Cpt(PseudoSingle, name='psx')
    pz = Cpt(PseudoSingle, name='psz')

    # real axes
    x = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:4-Ax:5}Mtr', name='sx')
    z = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:3-Ax:2}Mtr', name='sz')

    # configuration settings
    theta = Cpt(Signal, value=15.0, name='pmllc_theta')


pmllf = PseudoMLLFineSample('', name='pmllf')
pssx = pmllf.px
pssz = pmllf.pz
# To tweak the angle, set pmllf.theta.put(15.1) for example


pmllc = PseudoMLLCoarseSample('', name='pmllc')
psx = pmllc.x
psz = pmllc.z


hz = hmll.hz
vz = vmll.vz

