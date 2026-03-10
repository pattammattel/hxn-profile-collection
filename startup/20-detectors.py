print(f"Loading {__file__!r} ...")

from ophyd import (Signal, EpicsSignal, EpicsSignalRO)
from ophyd import (Device, Component as Cpt)

from ophyd.areadetector import (AreaDetector, PixiradDetectorCam, ImagePlugin,
                                TIFFPlugin, StatsPlugin, HDF5Plugin,
                                ProcessPlugin, ROIPlugin, TransformPlugin,
                                OverlayPlugin)
from ophyd.areadetector.base import ADBase
from ophyd.areadetector.base import ADComponent, EpicsSignalWithRBV
from ophyd.areadetector.filestore_mixins import FileStorePluginBase

from ophyd import CamBase

from ophyd.areadetector.cam import AreaDetectorCam
from collections import OrderedDict, deque

import time
from hxntools.detectors import (HxnTimepixDetector as _HTD,
                                HxnMerlinDetector as _HMD,
                                BeamStatusDetector, HxnMercuryDetector,
                                HxnDexelaDetector as _HDD)
# from hxntools.detectors.dexela import HDF5PluginWithFileStore as _dhdf
from hxntools.detectors.merlin import HDF5PluginWithFileStore as _mhdf
#from hxntools.detectors.timepix import HDF5PluginWithFileStore as _thdf
from hxntools.detectors.zebra import HxnZebra

from hxntools.detectors.trigger_mixins import HxnModalBase

from nslsii.ad33 import (SingleTriggerV33, StatsPluginV33, CamV33Mixin)

import h5py,os
import numpy as np


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

class DexelaSimulatedHDF5Plugin(FileStorePluginBase,ADBase):
    file_write_mode = Cpt(Signal,name='',value='Single')
    file_name = Cpt(Signal,name='',value='')
    file_path = Cpt(Signal,name='',value='')
    file_template = Cpt(Signal,name='',value='%s%s_%2.2d.h5')
    file_path_exists = Cpt(Signal,name='',value=True)
    file_number = Cpt(Signal,name='',value=1)
    auto_increment = Cpt(Signal,name='',value=0)
    array_counter = Cpt(Signal,name='',value=0)
    auto_save = Cpt(Signal,name='',value=0)
    num_capture = Cpt(Signal,name='',value=0)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.filestore_spec = 'DEX_HDF5'
        self._asset_docs_cache = deque()
        self.h5_handle = None
        # self.file_write_mode = Signal(name='',value='Single')
        # self.file_name = Signal(name='',value='')
        # self.file_path = Signal(name='',value='')
        # self.file_number = Signal(name='',value=0)
    
    def stage(self):
        super().stage()
        self._fn = self.file_template.get() % (
            self._fp,
            self.file_name.get(),
            0,
        )
        self.h5_handle = h5py.File(os.path.join(self.file_path.get(),self._fn),'a')
        xsize = self.parent.cam.array_size.array_size_x.get()
        ysize = self.parent.cam.array_size.array_size_y.get()

        maxshape = (None,xsize,ysize)
        chunks = (16,xsize,ysize)

        self.ds = self.h5_handle.create_dataset(
            'entry/instrument/detector/data',
            shape=(0,xsize,ysize),
            dtype=np.int16,
            maxshape=maxshape,
            chunks=chunks
        )
        self.n_frame = 0

        self._generate_resource({})
    
    def unstage(self):
        if self.h5_handle:
            self.h5_handle.close()
        return super().unstage()
    
    def insert_frame(self):
        if self.n_frame >=0:
            self.ds.resize(self.n_frame+1,axis=0)
            self.ds[self.n_frame,:,:] = self.parent.image1.array_data.get().reshape(self.ds.shape[1],self.ds.shape[2])
        self.n_frame += 1
    
    
class HxnDexelaDetector(AreaDetector,HxnModalBase):
    cam = Cpt(DexelaDetectorCam, 'cam1:')
    proc1 = Cpt(ProcessPlugin, 'Proc1:')
    transform1 = Cpt(TransformPlugin, 'Trans1:')
    image1 = Cpt(ImagePlugin, 'image1:')

    fs = Cpt(DexelaSimulatedHDF5Plugin,'',
               write_path_template='/data/%Y/%m/%d/',
               root='/data',
               reg=db.reg)
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fs._parent = self
    
    def mode_external(self):
        raise NotImplementedError('Dexela detector cannot be external triggered.')
    
    def mode_internal(self):
        super().mode_internal()

        cam = self.cam
        cam.stage_sigs[cam.num_images] = 1
        cam.stage_sigs[cam.image_mode] = 'Multiple'
        cam.stage_sigs[cam.trigger_mode] = 'Int. Fixed Rate'

        count_time = self.count_time.get()
        if count_time is not None:
            self.stage_sigs[self.cam.acquire_time] = count_time
            self.stage_sigs[self.cam.acquire_period] = count_time
    
    def unstage(self):
        # self.fs.insert_frame() #insert last frame
        return super().unstage()

    def read(self):
        return self.fs.read()
    
    def describe(self):
        return self.fs.describe()
        
    def trigger(self):
        self.cam.acquire.put(1,wait=True)
        time.sleep(0.2)
        self.fs.insert_frame() #insert previous frame
        self.fs.generate_datum('dexela1_image',time.time(),{'frame':self.fs.n_frame-1})

        return super().trigger()




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
