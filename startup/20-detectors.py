print(f"Loading {__file__!r} ...")

from ophyd import (EpicsSignal, EpicsSignalRO)
from ophyd import (Device, Component as Cpt)

from ophyd.areadetector import (AreaDetector, PixiradDetectorCam, ImagePlugin,
                                TIFFPlugin, StatsPlugin, HDF5Plugin,
                                ProcessPlugin, ROIPlugin, TransformPlugin,
                                OverlayPlugin)
from ophyd.areadetector.base import ADComponent, EpicsSignalWithRBV

from ophyd import CamBase

from ophyd.areadetector.cam import AreaDetectorCam


import hxntools.handlers
from hxntools.detectors import (HxnTimepixDetector as _HTD,
                                HxnMerlinDetector as _HMD,
                                BeamStatusDetector, HxnMercuryDetector,
                                HxnDexelaDetector as _HDD)
#from hxntools.detectors.dexela import HDF5PluginWithFileStore as _dhdf
from hxntools.detectors.merlin import HDF5PluginWithFileStore as _mhdf
#from hxntools.detectors.timepix import HDF5PluginWithFileStore as _thdf
from hxntools.detectors.zebra import HxnZebra

from nslsii.ad33 import (SingleTriggerV33, StatsPluginV33, CamV33Mixin)



# - 2D pixel array detectors
# -- Timepix 1
#class HxnTimepixDetector(_HTD):
#    hdf5 = Cpt(_thdf, 'HDF1:',
#               read_attrs=[],
#               configuration_attrs=[],
#               write_path_template='/data/%Y/%m/%d/',
#               root='/data',
#               reg=db.reg)

#timepix1 = HxnTimepixDetector('XF:03IDC-ES{Tpx:1}', name='timepix1',
#                              image_name='timepix1',
#                              read_attrs=['hdf5', 'cam','stats1'])
#timepix1.hdf5.read_attrs = []

# -- Timepix 2
#timepix2 = HxnTimepixDetector('XF:03IDC-ES{Tpx:2}', name='timepix2',
#                              image_name='timepix2',
#                              read_attrs=['hdf5', 'cam'])
#timepix2.hdf5.read_attrs = []




# -- Merlin 1
class HxnMerlinDetector(_HMD):
    stats1 = Cpt(StatsPluginV33, 'Stats1:')
    stats2 = Cpt(StatsPluginV33, 'Stats2:')
    stats3 = Cpt(StatsPluginV33, 'Stats3:')
    stats4 = Cpt(StatsPluginV33, 'Stats4:')
    stats5 = Cpt(StatsPluginV33, 'Stats5:')

    hdf5 = Cpt(_mhdf, 'HDF1:',
               read_attrs=[],
               configuration_attrs=[],
               write_path_template='/data/%Y/%m/%d/',
               root='/data',
               reg=db.reg)

    total_points = Cpt(Signal,
                       value=1,
                       doc="The total number of points to be taken")

    def ensure_nonblocking(self):
        for c in self.component_names:
            cpt = getattr(self, c)
            if hasattr(cpt, 'ensure_nonblocking'):
                cpt.ensure_nonblocking()



merlin1 = HxnMerlinDetector('XF:03IDC-ES{Merlin:1}', name='merlin1',
                            image_name='merlin1',
                            read_attrs=['hdf5', 'cam', 'stats1'])
merlin1.hdf5.read_attrs = []

merlin1.ensure_nonblocking()

merlin1.hdf5.stage_sigs.update([(merlin1.hdf5.compression,'szip')])
merlin1.cam.acquire_period.put_complete = True


merlin2 = HxnMerlinDetector('XF:03IDC-ES{Merlin:2}', name='merlin2',
                            image_name='merlin2',
                            read_attrs=['hdf5', 'cam', 'stats1'])
merlin2.hdf5.read_attrs = []

merlin2.hdf5.stage_sigs.update([(merlin2.hdf5.compression,'szip')])

merlin2.ensure_nonblocking()

# -- Dexela 1 (Dexela 1512 GigE-V24)
class DexelaDetectorCam(CamBase):
    pass


class HxnDexelaDetector(AreaDetector):
    cam = Cpt(DexelaDetectorCam, 'cam1:')
    proc1 = Cpt(ProcessPlugin, 'Proc1:')
    transform1 = Cpt(TransformPlugin, 'Trans1:')
    image1 = Cpt(ImagePlugin, 'image1:')


dexela1 = HxnDexelaDetector('XF:03IDC-ES{Dexela:1}', name='dexela1')
'''


class HxnDexelaDetector(_HDD):
    hdf5 = Cpt(_dhdf, 'HDF1:',
               read_attrs=[],
               configuration_attrs=[],
               write_path_template='Z:\\%Y\\%m\\%d',
               read_path_template='/data/%Y/%m/%d/',
               root='/data',
               path_semantics='windows',
               reg=db.reg)

dexela1 = HxnDexelaDetector('XF:03IDC-ES{Dexela:1}', name='dexela1',
                            image_name='dexela1',
                            read_attrs=['hdf5', 'cam','stats1'])
dexela1.hdf5.read_attrs = []
'''
# - Other detectors and triggering devices
# -- DXP Mercury (1 channel)
#mercury1 = HxnMercuryDetector('XF:03IDC-ES{DXP:1}', name='mercury1')
#mercury1.read_attrs = ['dxp', 'mca']
#mercury1.dxp.read_attrs = []

# -- Quantum Detectors Zebra
zebra = HxnZebra('XF:03IDC-ES{Zeb:1}:', name='zebra')
zebra.read_attrs = []


# -- Lakeshores
class HxnLakeShore(Device):
    ch_a = Cpt(EpicsSignalRO, '-Ch:A}C:T-I')
    ch_b = Cpt(EpicsSignalRO, '-Ch:B}C:T-I')
    ch_c = Cpt(EpicsSignalRO, '-Ch:C}C:T-I')
    ch_d = Cpt(EpicsSignalRO, '-Ch:D}C:T-I')

    def set_names(self, cha, chb, chc, chd):
        '''Set names of all channels

        Returns channel signals
        '''
        self.ch_a.name = cha
        self.ch_b.name = chb
        self.ch_c.name = chc
        self.ch_d.name = chd
        return self.ch_a, self.ch_b, self.ch_c, self.ch_d


lakeshore2 = HxnLakeShore('XF:03IDC-ES{LS:2', name='lakeshore2')

# Name the lakeshore channels:
t_hlens, t_vlens, t_sample, t_base = lakeshore2.set_names(
    't_hlens', 't_vlens', 't_sample', 't_base')

# X-ray eye camera sigma X/sigma Y
sigx = EpicsSignalRO('XF:03IDB-BI{Xeye-CAM:1}Stats1:SigmaX_RBV', name='sigx')
sigy = EpicsSignalRO('XF:03IDB-BI{Xeye-CAM:1}Stats1:SigmaY_RBV', name='sigy')



# Front-end Xray BPMs and local bumps
class HxnBpm(Device):
    x = Cpt(EpicsSignalRO, 'Pos:X-I')
    y = Cpt(EpicsSignalRO, 'Pos:Y-I')


xbpm = HxnBpm('SR:C03-BI{XBPM:1}', name='xbpm')

angle_x = EpicsSignalRO('SR:C31-{AI}Aie3:Angle-x-Cal', name='angle_x')
angle_y = EpicsSignalRO('SR:C31-{AI}Aie3:Angle-y-Cal', name='angle_y')

xbpmc_yp =  EpicsSignalRO('XF:03ID-BI{EM:BPM2}PosY:MeanValue_RBV', name='xbpmc_yp')

xbpmb_xp =  EpicsSignalRO('XF:03ID-BI{EM:BPM1}PosX:MeanValue_RBV', name='xbpmb_xp')
xbpmb_yp =  EpicsSignalRO('XF:03ID-BI{EM:BPM1}PosY:MeanValue_RBV', name='xbpmb_yp')



# Diamond Quad BPMs in C hutch
quad = HxnBpm('XF:03ID{XBPM:17}', name='quad')


sr_shutter_status = EpicsSignalRO('SR-EPS{PLC:1}Sts:MstrSh-Sts',
                                  name='sr_shutter_status')
sr_beam_current = EpicsSignalRO('SR:C03-BI{DCCT:1}I:Real-I',
                                name='sr_beam_current')

det_beamstatus = BeamStatusDetector(min_current=100.0, name='det_beamstatus')

#Temporary EPICS PV  detectors
#dexela_roi1_tot = EpicsSignalRO('XF:03IDC-ES{Dexela:1}Stats1:Total_RBV', name='dexela_roi1_tot')
#roi1_tot = EpicsSignalRO('XF:03IDC-ES{Merlin:1}Stats1:Total_RBV', name='roi1_tot')
#roi1_tot = roi1_tot.value
