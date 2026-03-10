print(f"Loading {__file__!r} ...")
from collections import OrderedDict

from epics import caput, caget
import os
import tqdm
import threading
import h5py
import numpy as np
import time as ttime
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt
from hxntools.detectors.zebra import Zebra, EpicsSignalWithRBV
from databroker.assets.handlers import HandlerBase
from ophyd.areadetector.filestore_mixins import resource_factory

from bluesky.utils import short_uid

xs = None  # No Xspress3
# use_sclr = False  # Set this False to run zebra without 'sclr'
use_sclr = True

## PPMAC
from ppmac.pp_comm import PPComm
ppmac = PPComm(host='xf03idc-ppmac1',fast_gather=True)

import time as ttime
from datetime import datetime
from threading import Thread

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky import RunEngine
from bluesky.utils import ProgressBarManager
from epics import caget, caput
from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor, EpicsPathSignal, EpicsSignal, EpicsSignalWithRBV

from event_model import compose_resource

class DATA(Device):
    hdf_directory = Cpt(EpicsSignal, "HDFDirectory", string=True)
    hdf_file_name = Cpt(EpicsSignal, "HDFFileName", string=True)
    num_capture = Cpt(EpicsSignal, "NumCapture")
    num_captured = Cpt(EpicsSignal, "NumCaptured")
    flush_period = Cpt(EpicsSignal, "FlushPeriod")
    capture = Cpt(EpicsSignal, "Capture")
    capture_mode = Cpt(EpicsSignal, "CaptureMode", string=True)
    status = Cpt(EpicsSignal, "Status", string=True)


class PCOMP(Device):
    pre_start = Cpt(EpicsSignal, "PRE_START")
    start = Cpt(EpicsSignal, "START")
    width = Cpt(EpicsSignal, "WIDTH")
    step = Cpt(EpicsSignal, "STEP")
    pulses = Cpt(EpicsSignal, "PULSES")


class PCAP(Device):
    arm = Cpt(EpicsSignal, "ARM")
    active = Cpt(EpicsSignal, "ACTIVE")


class CLOCK(Device):
    enable = Cpt(EpicsSignal, "ENABLE")
    period = Cpt(EpicsSignal, "PERIOD")
    period_units = Cpt(EpicsSignal, "PERIOD:UNITS")


class COUNTER(Device):
    enable = Cpt(EpicsSignal, "ENABLE")
    start = Cpt(EpicsSignal, "START")
    step = Cpt(EpicsSignal, "STEP")
    max = Cpt(EpicsSignal, "MAX")
    min = Cpt(EpicsSignal, "MIN")


class INENC(Device):
    val = Cpt(EpicsSignal, "VAL")
    setp = Cpt(EpicsSignal, "SETP")


class POSITION(Device):
    units = Cpt(EpicsSignal, "UNITS", string=True)
    scale = Cpt(EpicsSignal, "SCALE")
    offset = Cpt(EpicsSignal, "OFFSET")


class POSITIONS(Device):
    inenc1 = Cpt(POSITION, "12:")
    inenc2 = Cpt(POSITION, "13:")


class PULSE(Device):
    delay_units = Cpt(EpicsSignal, "DELAY:UNITS", string=True)
    delay = Cpt(EpicsSignal, "DELAY")
    width_units = Cpt(EpicsSignal, "WIDTH:UNITS", string=True)
    width = Cpt(EpicsSignal, "WIDTH")
    pulses = Cpt(EpicsSignal, "PULSES")
    step_units = Cpt(EpicsSignal, "STEP:UNITS", string=True)
    step = Cpt(EpicsSignal, "STEP")
    trig_edge = Cpt(EpicsSignal, "TRIG_EDGE", string=True)


class BITS(Device):
    A = Cpt(EpicsSignal, "A")
    B = Cpt(EpicsSignal, "B")
    C = Cpt(EpicsSignal, "C")
    D = Cpt(EpicsSignal, "D")


class PandA_Ophyd1(Device):
    pcap = Cpt(PCAP, "PCAP:")
    data = Cpt(DATA, "DATA:")
    pcomp1 = Cpt(PCOMP, "PCOMP1:")
    pcomp2 = Cpt(PCOMP, "PCOMP2:")
    clock1 = Cpt(CLOCK, "CLOCK1:")
    clock2 = Cpt(CLOCK, "CLOCK2:")
    counter1 = Cpt(COUNTER, "COUNTER1:")
    counter2 = Cpt(COUNTER, "COUNTER2:")
    counter3 = Cpt(COUNTER, "COUNTER3:")
    inenc1 = Cpt(INENC, "INENC1:")
    inenc2 = Cpt(INENC, "INENC2:")
    inenc3 = Cpt(INENC, "INENC3:")
    inenc4 = Cpt(INENC, "INENC4:")
    pulse1 = Cpt(PULSE, "PULSE1:")
    pulse2 = Cpt(PULSE, "PULSE2:")
    pulse3 = Cpt(PULSE, "PULSE3:")
    pulse4 = Cpt(PULSE, "PULSE4:")
    positions = Cpt(POSITIONS, "POSITIONS:")
    bits = Cpt(BITS, "BITS:")


panda1 = PandA_Ophyd1("XF03IDC-ES-PANDA-1:", name="panda1")
panda1.pulse2.width.put_complete = True

panda2 = PandA_Ophyd1("XF03IDC-ES-PANDA-2:", name="panda2")

# panda2 = PandA_Ophyd1("XF03IDC-ES-PANDA-2:", name="panda2")


# class ExportSISDataPanda:
#     def __init__(self):
#         self._fp = None
#         self._filepath = None

#     def open(self, filepath, mca_names, ion, panda):
#         self.close()
#         self._filepath = filepath
#         self._fp = h5py.File(filepath, "w", libver="latest")

#     pulse1 = Cpt(PULSE, "PULSE1:")
#     pulse2 = Cpt(PULSE, "PULSE2:")
#     pulse3 = Cpt(PULSE, "PULSE3:")
#     pulse4 = Cpt(PULSE, "PULSE4:")
#     positions = Cpt(POSITIONS, "POSITIONS:")
#     bits = Cpt(BITS, "BITS:")


# panda1 = PandA_Ophyd1("XF03IDC-ES-PANDA-1:", name="panda1")
# panda1.pulse2.width.put_complete = True


# class ExportSISDataPanda:
#     def __init__(self):
#         self._fp = None
#         self._filepath = None

#     def open(self, filepath, mca_names, ion, panda):
#         self.close()
#         self._filepath = filepath
#         self._fp = h5py.File(filepath, "w", libver="latest")

#     pulse1 = Cpt(PULSE, "PULSE1:")
#     pulse2 = Cpt(PULSE, "PULSE2:")
#     pulse3 = Cpt(PULSE, "PULSE3:")
#     pulse4 = Cpt(PULSE, "PULSE4:")
#     positions = Cpt(POSITIONS, "POSITIONS:")
#     bits = Cpt(BITS, "BITS:")


# panda1 = PandA_Ophyd1("XF03IDC-ES-PANDA-1:", name="panda1")
# panda1.pulse2.width.put_complete = True


class ExportSISDataPanda:
    def __init__(self):
        self._fp = None
        self._filepath = None

    def open(self, filepath, mca_names, ion, panda):
        self.close()
        self._filepath = filepath
        self._fp = h5py.File(filepath, "w", libver="latest")

        self._fp.swmr_mode = True

        self._ion = ion
        self._panda = panda
        self._mca_names = mca_names

        def create_ds(ds_name):
            ds = self._fp.create_dataset(ds_name, data=np.array([], dtype="f"), maxshape=(None,), dtype="f")

        for ds_name in self._mca_names:
            create_ds(ds_name)

        self._fp.flush()

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def __del__(self):
        self.close()

    def export(self):

        n_mcas = len(self._mca_names)

        mca_data = []
        for n in range(1, n_mcas + 1):
            mca = self._ion.mca_by_index[n].spectrum.get(timeout=5.0)
            mca_data.append(mca)

        correct_length = int(self._panda.data.num_captured.get()/self._panda.position_supersample)

        for n in range(len(mca_data)):
            mca = mca_data[n]
            # print(f"Number of mca points: {len(mca)}")
            # mca = mca[1::2]
            if len(mca) != correct_length:
                print(f"Incorrect number of points ({len(mca)}) loaded from MCA{n + 1}: {correct_length} points are expected")
                if len(mca > correct_length):
                    mca = mca[:correct_length]
                else:
                    mca = np.append(mca, [1e10] * (correct_length - len(mca)))
            mca_data[n] = mca

        j = 0
        while self._panda.data.capture.get() == 1:
            print("Waiting for pandabox data...")
            ttime.sleep(0.1)
            j += 1
            if j > 10:
                print("PANDABOX IS BEHAVING BADLY CARRYING ON")
                break

        def add_data(ds_name, data):
            ds = self._fp[ds_name]
            n_ds = ds.shape[0]
            ds.resize((n_ds + len(data),))
            ds[n_ds:] = np.array(data)

        for n, name in enumerate(self._mca_names):
            add_data(name, np.asarray(mca_data[n]))

        self._fp.flush()

class HXNFlyerPanda(Device):
    """
    This is the Panda1.
    """

    LARGE_FILE_DIRECTORY_WRITE_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_READ_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_ROOT = LARGE_FILE_DIRECTORY_ROOT

    @property
    def detectors(self):
        return tuple(self._dets)

    @detectors.setter
    def detectors(self, value):
        dets = tuple(value)
        # if not all([d.name in self.KNOWN_DETS for d in dets]):
        #     raise ValueError(
        #         f"One or more of {[d.name for d in dets]}"
        #         f"is not known to the panda. "
        #         f"The known detectors are {self.KNOWN_DETS})"
        #     )
        self._dets = dets

    @property
    def sclr(self):
        return self._sis

    def __init__(self, panda,dets,sclr, motor=None, root_dir=None, **kwargs):
        super().__init__("", parent=None, **kwargs)
        self.name = "PandaFlyer"
        if root_dir is None:
            root_dir = self.LARGE_FILE_DIRECTORY_ROOT
        self._mode = "idle"
        self._dets = dets
        self._sis = sclr
        self._root_dir = root_dir
        self._resource_document, self._datum_factory = None, None
        self._document_cache = deque()
        self._last_bulk = None

        self._point_counter = None
        self.frame_per_point = None

        self.panda = panda
        self.motor = motor

        self._document_cache = []
        self._resource_document = None
        self._datum_factory = None

        if self._sis is not None:
            self._data_sis_exporter = ExportSISDataPanda()

        self._xsp_roi_exporter = None

        type_map = {"int32": "<i4", "float32": "<f4", "float64": "<f8"}

        self.fields = {
            # "counter1_out": {
            #     "value": "COUNTER1.OUT.Value",
            #     "dtype_str": type_map["float64"],
            # },
            "inenc1_val": {
                "value": "INENC1.VAL.Value",
                "dtype_str": type_map["int32"],
            },
            "inenc2_val": {
                "value": "INENC2.VAL.Value",
                "dtype_str": type_map["int32"],
            },
            "inenc3_val": {
                "value": "INENC3.VAL.Value",
                "dtype_str": type_map["int32"],
            },
            "inenc4_val": {
                "value": "INENC4.VAL.Value",
                "dtype_str": type_map["int32"],
            },
            "pcap_ts_trig": {
                "value": "PCAP.TS_TRIG.Value",
                "dtype_str": type_map["float64"],
            },
        }
        self.panda.data.hdf_directory.put_complete = True
        self.panda.data.hdf_file_name.put_complete = True

    def stage(self):
        super().stage()

    def unstage(self):
        self._point_counter = None
        if self._sis is not None:
            self._data_sis_exporter.close()
        if self._xsp_roi_exporter is not None:
            self._xsp_roi_exporter.close()
        super().unstage()

    def kickoff(self, *, num):
        """Kickoff the acquisition process."""
        # Prepare parameters:
        self._document_cache = deque()
        self._datum_docs = {}
        self._counter = itertools.count()
        self._point_counter = 0

        self.frame_per_point = int(num)
        self._npts = int(num)
        # Prepare 'resource' factory.
        now = datetime.now()
        self.fl_path = self.LARGE_FILE_DIRECTORY_WRITE_PATH
        self.fl_name = f"panda_rbdata_{now.strftime('%Y%m%d_%H%M%S')}_{short_uid()}.h5"

        resource_path = self.fl_name
        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec="PANDA",
            root=self.fl_path,
            resource_path=resource_path,
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._document_cache.append(("resource", self._resource_document))

        for key, value in self.fields.items():
            datum_document = self._datum_factory(datum_kwargs={"field": value["value"]})
            self._document_cache.append(("datum", datum_document))
            self._datum_docs[key] = datum_document


        ## Scaler
        if self._sis is not None:
            # Stop the SIS3820
            self._sis.stop_all.put(1)

        self.__filename_sis = "{}.h5".format(uuid.uuid4())
        self.__read_filepath_sis = os.path.join(
            self.LARGE_FILE_DIRECTORY_READ_PATH, self.__filename_sis
        )
        self.__write_filepath_sis = os.path.join(
            self.LARGE_FILE_DIRECTORY_WRITE_PATH, self.__filename_sis
        )

        self.__filestore_resource_sis, self._datum_factory_sis = resource_factory(
            SISHDF5Handler.HANDLER_NAME,
            root=self.LARGE_FILE_DIRECTORY_ROOT,
            resource_path=self.__read_filepath_sis,
            resource_kwargs={"frame_per_point": self.frame_per_point},
            path_semantics="posix",
        )

        resources = [self.__filestore_resource_sis]

        self._xsp_roi_exporter = None
        ## Xspress3 ROIs
        for d in self._dets:
            if d.name == 'xspress3' or d.name == 'xspress3_det2':

                self.xsp = d

                self.__filename_xsp_roi = "ROI0_{}.h5".format(uuid.uuid4())
                self.__read_filepath_xsp_roi = os.path.join(
                    self.LARGE_FILE_DIRECTORY_READ_PATH, self.__filename_xsp_roi
                )
                self.__write_filepath_xsp_roi = os.path.join(
                    self.LARGE_FILE_DIRECTORY_WRITE_PATH, self.__filename_xsp_roi
                )

                self._xsp_roi_exporter = ExportXpsROI()
                self._xsp_roi_exporter.open(
                    self. __write_filepath_xsp_roi, d
                )

                self.__filestore_resource_xsp_roi, self._datum_factory_xsp_roi = resource_factory(
                    'ROI_HDF5_FLY',
                    root=self.LARGE_FILE_DIRECTORY_ROOT,
                    resource_path=self.__read_filepath_xsp_roi,
                    resource_kwargs={},
                    path_semantics="posix",
                )


                resources.append(self.__filestore_resource_xsp_roi)

        # if self._sis:
        #     resources.append(self.__filestore_resource_sis)

        self._document_cache.extend(("resource", _) for _ in resources)

        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            self._data_sis_exporter.open(
                self.__write_filepath_sis, mca_names=sis_mca_names, ion=self._sis, panda=self.panda
            )


        # Kickoff panda process:
        print(f"[Panda]Starting acquisition ...")

        self.panda.position_supersample = self.position_supersample

        self.panda.data.hdf_directory.set(self.fl_path).wait()
        self.panda.data.hdf_file_name.set(self.fl_name).wait()
        #self.panda.data.flush_period.set(1).wait()

        self.panda.data.capture_mode.set("FIRST_N").wait()
        self.panda.data.num_capture.set(self.frame_per_point).wait()

        self.panda.pcap.arm.set(1).wait()

        self.panda.data.capture.set(1).wait()

        print(f"[Panda]Panda kickoff complete ...")

        return NullStatus()

    def complete(self):
        print("[Panda]complete")
        """Wait for the acquisition process started in kickoff to complete."""
        # Wait until done
        timeout = 60
        counter = 0
        while (self.panda.data.capture.get() == 1) and (counter<timeout):
            time.sleep(0.1)
            counter+=1

        self.panda.pcap.arm.set(0).wait()
        self.panda.data.capture.put(0)

        for d in self._dets:
            d.stop(success=True)

        now = ttime.time()  # TODO: figure out how to get it from PandABox (maybe?)

        data_dict = {
            key: datum_doc["datum_id"] for key, datum_doc in self._datum_docs.items()
        }

        self._last_bulk = {
            "data": data_dict,
            "timestamps": {key: now for key in self._datum_docs},
            "time": now,
            "filled": {key: False for key in self._datum_docs},
        }

        if self._sis:
            sis_mca_names = self._sis_mca_names()
            sis_datum = []
            for name in sis_mca_names:
                sis_datum.append(self._datum_factory_sis({"column": name, "point_number": self._point_counter}))
            self._document_cache.extend(("datum", d) for d in sis_datum)

        # @timer_wrapper
        def get_sis_data():
            if self._sis is None:
                return
            self._data_sis_exporter.export()

        get_sis_data()

        if self._xsp_roi_exporter is not None:
            self._xsp_roi_exporter.export(int(self.frame_per_point/self.position_supersample))

            panda_live_plot.update_plot(True)

            roi_datum = []
            for roi in self.xsp.enabled_rois:
                roi_datum.append(self._datum_factory_xsp_roi({"det_elem": roi.name}))
            self._last_bulk["data"].update({k: v["datum_id"] for k, v in zip([roi.name for roi in self.xsp.enabled_rois], roi_datum)})
            self._last_bulk["timestamps"].update({k: v["datum_id"] for k, v in zip([roi.name for roi in self.xsp.enabled_rois], roi_datum)})
            self._document_cache.extend(("datum", d) for d in roi_datum)

        for d in self._dets:
            if d.name != 'fs' and d.name != 'bshutter' and d.name != 'xspress3':
                self._document_cache.extend(d.collect_asset_docs())
            if d.name == 'xspress3':
                doc_cnt = 0
                for doc in d.collect_asset_docs():
                    self._document_cache.append(doc)
                    doc_cnt += 1
                    if doc_cnt == 4:
                        break

        print("[Panda]collect data")

        if self._sis:
            self._last_bulk["data"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})
            self._last_bulk["timestamps"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})

        for d in self._dets:
            if d.name == 'merlin1' or d.name == 'merlin2':
                reading = d.read()
                self._last_bulk["data"].update(
                    {k: v["value"] for k, v in reading.items()}
                    )
                self._last_bulk["timestamps"].update(
                    {k: v["timestamp"] for k, v in reading.items()}
                )
            if d.name.startswith('eiger'):
                reading = d.read()
                self._last_bulk["data"].update(
                    {k: v["value"] for k, v in reading.items()}
                    )
                self._last_bulk["timestamps"].update(
                    {k: v["timestamp"] for k, v in reading.items()}
                )
            if d.name == 'xspress3':
                reading = d.read()
                self._last_bulk["data"].update(
                    {k: v["value"] for k, v in reading.items() if k.startswith('xspress3')}
                )
                self._last_bulk["timestamps"].update(
                    {k: v["timestamp"] for k, v in reading.items() if k.startswith('xspress3')}
                )
            if d.name == 'xspress3_det2':
                reading = d.read()
                self._last_bulk["data"].update(
                    {k: v["value"] for k, v in reading.items()}
                )
                self._last_bulk["timestamps"].update(
                    {k: time.time() for k, v in reading.items()}
                )

        return NullStatus()

    def describe_collect(self):
        """Describe the data structure."""
        return_dict = {"primary": OrderedDict()}
        desc = return_dict["primary"]

        ext_spec = "FileStore:"

        spec = {
            "external": ext_spec,
            "dtype": "array",
            "shape": [self._npts],
            "source": "",  # make this the PV of the array the det is writing
        }

        for key, value in self.fields.items():
            desc.update(
                {
                    key: {
                        "source": "PANDA",
                        "dtype": "array",
                        "dtype_str": value["dtype_str"],
                        "shape": [
                            self.frame_per_point
                        ],  # TODO: figure out variable shape
                        "external": "FILESTORE:",
                    }
                }
            )

        for d in self._dets:
            if d.name == 'merlin1' or d.name == 'merlin2':
                desc.update(d.describe())
            if d.name.startswith('eiger'):
                desc.update(d.describe())
            if d.name == 'xspress3':
                desc.update([(k, v) for k,v in d.describe().items() if k.startswith('xspress3')])
            if d.name == 'xspress3_det2':
                desc.update(d.describe())

        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            for n, name in enumerate(sis_mca_names):
                desc[name] = spec
                desc[name]["source"] = self._sis.mca_by_index[n + 1].spectrum.pvname

        if self._xsp_roi_exporter is not None:
            for roi in self.xsp.enabled_rois:
                desc[roi.name] = spec
                if hasattr(roi,'settings'):
                    desc[roi.name]["source"] = roi.settings.array_data.pvname
                else:
                    desc[roi.name]["source"] = roi.ts_total.pvname


        return return_dict

    def collect(self):
        yield self._last_bulk
        self._point_counter += 1

    def collect_asset_docs(self):
        """The method to collect resource/datum documents."""
        items = list(self._document_cache)
        self._document_cache.clear()
        yield from items

    def _sis_mca_names(self):
        n_mcas = n_scaler_mca
        return [getattr(self._sis.channels, f"chan{_}").name for _ in range(1, n_mcas + 1)]

panda_flyer = HXNFlyerPanda(panda2,[],sclr1,name="PandaFlyer")
panda_flyer_fip = HXNFlyerPanda(panda1,[],sclr1,name="PandaFlyer_FIP")

def flyscan_pd(detectors, start_signal, total_points, dwell, *,
                      panda_flyer,
                      delta=None, shutter=False, align=False, plot=False, dead_time = 0, scan_dim = None,
                      md=None, snake=False, verbose=False, wait_before_scan=None, position_supersample = 1,
                      merlin_cont_mode=False, wait_for_start_input = False, trigger_funcgen = False, scan_header = None):
    """Read IO from SIS3820.
    Zebra buffers x(t) points as a flyer.
    Xpress3 is our detector.
    The aerotech has the x and y positioners.
    delta should be chosen so that it takes about 0.5 sec to reach the gate??
    ymotor  slow axis
    xmotor  fast axis

    Parameters
    ----------
    Detectors : List[Device]
       These detectors must be known to the zebra

    xstart, xstop : float
    xnum : int
    ystart, ystop : float
    ynum : int
    dwell : float
       Dwell time in seconds

    flying_zebra : SRXFlyer2D

    xmotor, ymotor : EpicsMotor, kwarg only
        These should be known to the zebra
        # TODO sort out how to check this

    delta : float, optional, kwarg only
       offset on the ystage start position.  If not given, derive from
       dwell + pixel size
    align : bool, optional, kwarg only
       If True, try to align the beamline
    """

    t_scan = tic()

    if wait_before_scan is None:
       wait_before_scan = short_uid('before_scan')

    # Assign detectors to flying_zebra, this may fail
    panda_flyer.detectors = detectors
    # Setup detectors, combine the zebra, sclr, and the just set detector list
    detectors = (panda_flyer.panda, panda_flyer.sclr) + panda_flyer.detectors
    detectors = [_ for _ in detectors if _ is not None]


    # print(f"detectors_stage_once={detectors_stage_once}")
    # print(f"detectors_stage_every_row={detectors_stage_every_row}")

    dets_by_name = {d.name : d for d in detectors}

    panda_flyer.frame_per_point = total_points * position_supersample
    panda_flyer.position_supersample = position_supersample

    if verbose:
        print("Set up detectors")
        t_detset = tic()

    # Set up the detectors
    for det_name in ("merlin1", "merlin2", "eiger2", "eiger3", "eiger_mobile"):
        if det_name in dets_by_name:
            dpc = dets_by_name[det_name]
            acquire_time = dwell - dead_time
            acquire_period = dwell
            if verbose:
                toc(t_detset,'Dwell time set')

            if det_name == "eiger2" or det_name == "eiger3":
                # Acquire one frame with the computed acquire time to avoid 'Invalid frame'
                #   errors in HDF5 plugin. This may be needed because Eiger is using
                #  'autosummation' for longer exposure times, which may result in different
                #  data representation for short and long exposures (just an assumption).
                # dpc.hdf5.warmup(acquire_time=acquire_time)
                if acquire_time < 0.006666:
                    image_bitdepth = 16
                else:
                    image_bitdepth = 32
                if 'UInt'+str(image_bitdepth) != dpc.hdf5.data_type.get():
                    print("Adjusting eiger output bitdepth")
                    dpc.cam.acquire.set(0)
                    dpc.hdf5.warmup(acquire_time)
                pass

            if verbose:
                toc(t_detset,'hdf5 warmup')

            dpc.stage_sigs[dpc.cam.acquire_time] = acquire_time
            dpc.stage_sigs[dpc.cam.acquire_period] = acquire_period
            #dpc.stage_sigs[dpc.cam.num_images] = num_total
            #dpc.stage_sigs[dpc.cam.wait_for_plugins] = 'No'
            dpc.stage_sigs['total_points'] = total_points
            dpc.hdf5.stage_sigs['num_capture'] = total_points
            dpc.hdf5.frame_per_point = total_points
            del dpc

    for det_name in ('merlin1', 'merlin2'):
        if det_name in dets_by_name:
            dpc = dets_by_name[det_name]

            dpc._external_acquire_at_stage = False
            dpc.mode_external()
            dpc.mode_settings.mode.set('external')
            dpc.mode_settings.total_points.set(total_points)

            dpc.hdf5.frame_per_point = total_points
            dpc.hdf5.filestore_spec_restore = dpc.hdf5.filestore_spec
            dpc.hdf5.filestore_spec = 'MERLIN_HDF5_BULK'
            # acquire_period = dwell
            # acquire_period = acquire_time + 0.0016392

    if "xspress3" in dets_by_name:
        dpc = dets_by_name["xspress3"]
        dpc.total_points.set(total_points)
        dpc.mode_settings.total_points.set(total_points)
        dpc.mode_settings.mode.set('external')
        dpc.hdf5.filestore_spec_restore = dpc.hdf5.filestore_spec
        dpc.hdf5.filestore_spec = 'XSP3_BULK'
        del dpc

    if "xspress3_det2" in dets_by_name:
        dpc = dets_by_name["xspress3_det2"]
        dpc.total_points.set(total_points)
        del dpc

    if verbose:
        toc(t_detset,'Detectors initialized')
    print('[Panda]Detectors initialized')

    if scan_header:
        export_scan_header(hxntools.scans.get_last_scan_id()+1,\
                scan_header[0],scan_header[1],scan_header[2],scan_header[3],scan_header[4],scan_header[5],scan_header[6],\
                [d for d in detectors if d.name.startswith('eiger')])

    if panda_flyer._sis is not None:
        # Put SIS3820 into single count (not autocount) mode
        panda_flyer.stage_sigs[panda_flyer._sis.count_mode] = 0
        panda_flyer.stage_sigs[panda_flyer._sis.count_on_start] = 1

    # If delta is None, set delta based on time for acceleration

    yield Msg('hxn_next_scan_id')

    try:
        panda_live_plot.scan_id = RE.md['scan_id'] + 1
    except:
        pass



    # Synchronize encoders
    # flying_zebra._encoder.pc.enc_pos1_sync.put(1)
    # flying_zebra._encoder.pc.enc_pos2_sync.put(1)
    # flying_zebra._encoder.pc.enc_pos3_sync.put(1)

    # # Somewhere sync_todo
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos1_sync, 1)
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos2_sync, 1)
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos3_sync, 1)
    # yield from bps.sleep(1)


    # print(f"Ready to start the scan !!!")  ##

    def at_scan(name, doc):
        # scanrecord.current_scan.put(doc['uid'][:6])
        # scanrecord.current_scan_id.put(str(doc['scan_id']))
        # scanrecord.current_type.put(md['scan']['type'])
        # scanrecord.scanning.put(True)
        # scanrecord.time_remaining.put((dwell*xnum + 3.8)/3600)
        pass

    def finalize_scan(name, doc):
        # logscan_detailed('XRF_FLY')
        # scanrecord.scanning.put(False)
        # scanrecord.time_remaining.put(0)
        pass

    # TODO remove this eventually?
    # xs = dets_by_name['xs']
    # xs = dets_by_name['xs2']
    # Not sure if this is always true
    # xs = dets_by_name[flying_zebra.detectors[0].name]  ## Uncomment this

    # yield from mv(xs.erase, 0)  ## Uncomment this

    # Setup LivePlot todo
    # if plot:
    #     livepopup = [
    #         SRX1DTSFlyerPlot(
    #             roi_pv.name,
    #             xstart=0,
    #             xstep=xrange*ynum,
    #             xlabel=xmotor.name
    #         )
    #     ]
    # else:
    #     livepopup = []

    for d in panda_flyer.detectors:
        if d.name.startswith('eiger'):
            yield from bps.mov(d.fly_next, True)
            yield from bps.mov(d.internal_trigger, False)

    #@subs_decorator(livepopup)
    @subs_decorator({'start': at_scan})
    @subs_decorator({'stop': finalize_scan})
    # @monitor_during_decorator([xs.channel1.rois.roi01.value])  ## Uncomment this
    # @monitor_during_decorator([xs.channel1.rois.roi01.value, xs.array_counter])
    @stage_decorator([panda_flyer])  # Below, 'scan' stage ymotor.
    @stage_decorator(panda_flyer.detectors)
    @run_decorator(md=md)
    def plan():
        if verbose:
            t_startfly = tic()
            print("Starting the plan ...")
            print(f"flying_zebra.detectors={panda_flyer.detectors}")

        # print(f"Plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
        # print(f"Plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")

        # TODO move this to stage sigs
        for d in panda_flyer.detectors:
            if d.name.startswith('eiger'):
                yield from bps.mov(d.total_points, total_points)

        print(f"Scanning fly")

        scan_counter = [];

        # # Merlin code from the original SRX plan
        if "merlin1" in dets_by_name:
            # print(f"Configuring 'merlin2' ...")
            dpc = dets_by_name["merlin1"]
            if merlin_cont_mode:
                yield from abs_set(dpc.cam.num_images, total_points, wait=True)
                yield from abs_set(dpc.cam.acquire_time, dwell * 0.5, wait=True)
                yield from abs_set(dpc.cam.num_exposures, total_points, wait=True)
                yield from abs_set(dpc.cam.trigger_mode, 4, wait=True)
            else:
                yield from abs_set(dpc.cam.num_images, total_points, wait=True)
                yield from abs_set(dpc.cam.acquire_time, 0.001, wait=True)
                yield from abs_set(dpc.cam.num_exposures, 1, wait=True)
                yield from abs_set(dpc.cam.acquire_period, 0.001822, wait=True)
            dpc._external_acquire_at_stage = True
            dpc.hdf5.filestore_spec = dpc.hdf5.filestore_spec_restore
            scan_counter.append(dpc.cam.num_images_counter)

            # Merlin needs to be triggered manually
            yield from abs_set(dpc.cam.acquire,1)
            del dpc

        if "merlin2" in dets_by_name:
            # print(f"Configuring 'merlin2' ...")
            dpc = dets_by_name["merlin2"]
            yield from abs_set(dpc.cam.num_images, total_points, wait=True)
            yield from abs_set(dpc.cam.acquire_time, 0.001, wait=True)
            yield from abs_set(dpc.cam.acquire_period, 0.002642, wait=True)
            dpc._external_acquire_at_stage = True
            dpc.hdf5.filestore_spec = dpc.hdf5.filestore_spec_restore
            scan_counter.append(dpc.cam.num_images_counter)

            # Merlin needs to be triggered manually
            yield from abs_set(dpc.cam.acquire,1)
            del dpc

        if "eiger2" in dets_by_name:
            # print(f"Configuring 'eiger2' ...")
            dpc = dets_by_name["eiger2"]
            yield from abs_set(dpc.cam.num_triggers, total_points, wait=True)
            yield from abs_set(dpc.cam.num_images, 1, wait=True)
            yield from abs_set(dpc.cam.wait_for_plugins, 'No', wait=True)
            scan_counter.append(dpc.cam.num_images_counter)
            del dpc
        if "eiger3" in dets_by_name:
            # print(f"Configuring 'eiger3' ...")
            dpc = dets_by_name["eiger3"]
            yield from abs_set(dpc.cam.num_triggers, total_points, wait=True)
            yield from abs_set(dpc.cam.num_images, 1, wait=True)
            yield from abs_set(dpc.cam.wait_for_plugins, 'No', wait=True)
            scan_counter.append(dpc.cam.num_images_counter)
            del dpc
        if "eiger_mobile" in dets_by_name:
            # print(f"Configuring 'eiger_mobile' ...")
            dpc = dets_by_name["eiger_mobile"]
            yield from abs_set(dpc.cam.num_triggers, total_points, group=wait_before_scan)
            yield from abs_set(dpc.cam.num_images, 1, group=wait_before_scan)
            yield from abs_set(dpc.cam.wait_for_plugins, 'No', group=wait_before_scan)
            scan_counter.append(dpc.cam.num_images_counter)
            del dpc
        if "xspress3" in dets_by_name:
            dpc = dets_by_name["xspress3"]
            dpc.hdf5.filestore_spec = dpc.hdf5.filestore_spec_restore
            dpc.mode_settings.scan_type.put('step') # Do not change this, needs to be in step mode for correct batched dataset description.
            scan_counter.append(dpc.hdf5.num_captured)
            del dpc
        if "xspress3_det2" in dets_by_name:
            dpc = dets_by_name["xspress3_det2"]
            scan_counter.append(dpc.cam.array_counter)
            del dpc


        ion = panda_flyer.sclr
        if ion:
            yield from abs_set(ion.nuse_all, total_points, wait=True)
            yield from abs_set(ion.input_mode, 2, wait=True)
            #yield from abs_set(ion.nuse_all, 2*xnum, wait=True)

        def panda_kickoff():
            yield from kickoff(panda_flyer,
                                num=total_points*position_supersample,
                                wait=True)
        yield from panda_kickoff()

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - PANDA STARTED')

        # arm SIS3820, note that there is a 1 sec delay in setting X
        # into motion so the first point *in each row* won't
        # normalize...
        if ion:
            yield from abs_set(ion.erase_start, 1)
            if verbose:
                toc(t_startfly, str='TIMER (STEP) - SCALAR STARTED')


        row_scan = short_uid('row')
        if verbose:
            print('Data collection:')

        #if roi_pv_force_update:
        #    yield from bps.mv(roi_pv_force_update, 1)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - DETECTORS TRIGGERED')

        yield from bps.wait(group=wait_before_scan)


        for d in panda_flyer.detectors:
            print(f'  triggering {d.name}')
            st = yield from bps.trigger(d)
            #st.add_callback(lambda x: toc(t_startfly, str=f"  DETECTOR  {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')}"))

        ## Wait a bit for detectors
        yield from bps.sleep(np.minimum(np.maximum(0.5,0.001*total_points),2))
        # st = yield from abs_set(xmotor, row_stop)
        progress_bar = tqdm.tqdm(total = total_points,unit='points')

        if wait_for_start_input:
            input("Waiting for start scan input...Hit Enter when ready.")
        # Scan!
        if trigger_funcgen:
            print("Sending manual trigger to function generator......")
            pt_fg_ch1.trig.put(1)
        ppmac.gpascii.send_line(start_signal)

        counter = 0
        while(scan_counter[0].get()<total_points):
            progress_bar.update(scan_counter[0].get() - progress_bar.n)
            counter +=1
            yield from bps.sleep(0.5)
            if 'xspress3' in dets_by_name:# or 'xspress3_det2' in dets_by_name:
                panda_live_plot.update_plot()

            # if counter>3600:
            #     break

        progress_bar.close()
        #yield from abs_set(dpc._acquisition_signal,0,wait=True)
        #del dpc

        while not all([counter.get() >= total_points for counter in scan_counter]):
            print('Waiting for detector(s) to finish all frames...')
            yield from bps.sleep(1)
            if 'xspress3' in dets_by_name:# or 'xspress3_det2' in dets_by_name:
                panda_live_plot.update_plot()
        # we still know about ion from above
        if ion:
            yield from abs_set(ion.stop_all, 1)  # stop acquiring scaler

        # @timer_wrapper
        def panda_complete():
            yield from complete(panda_flyer)  # tell the Zebra we are done
        if verbose:
            t_pdcomplete = tic()

        yield from panda_complete()

        if verbose:
            toc(t_pdcomplete, str='Panda complete')

        # @timer_wrapper
        def panda_collect():
            yield from collect(panda_flyer)  # extract data from Zebra
        if verbose:
            t_pdcollect = tic()

        yield from panda_collect()
        if verbose:
            toc(t_pdcollect, str='Panda collect')

        # Force update of the respective PV so that all collected monitoring data for the row
        #   is loaded before the plugin is reset. Otherwise data in monitoring stream will not
        #   contain last points of rows.
        #if roi_pv_force_update:
        #    yield from bps.mv(roi_pv_force_update, 1)

        if verbose:
            print(f"Step is completed")


    # print(f"Before plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
    # print(f"Before plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")
    final_plan = plan()
    uid = yield from final_plan
    # Run the scan

    toc(t_scan, 'scan_finished')
    return uid


def fly2dpd(dets, motor1, scan_start1, scan_end1, num1, motor2, scan_start2, scan_end2, num2, exposure_time, panda_flyer = panda_flyer, pos_return = True, apply_tomo_drift = False,
                tomo_angle = None, auto_rescan = False, dead_time = 0.0005, line_overhead = [0.01,0.01], line_dwell = 0.1, return_speed = 100.0, position_supersample = 10,
                md = None, merlin_cont_mode = False, num_sclr_ch = None, **kwargs):
    """
    Relative scan
    """

    # PPMAC control signal
    sl = ppmac.gpascii.send_line

    # Motor numbers
    motor_numbers = {'ssx':3,
                     'ssy':4,
                     'ssz':5,
                     'zpssx':6,
                     'zpssy':7,
                     'zpssz':8,
                     'dssx':9,
                     'dssy':10,
                     'dssz':11}


    do_scan = True
    while do_scan:

        if num1*num2>64000:
            raise ValueError("total number of points cannot exceed 64k")


        try:
            m1_num = motor_numbers[motor1.name]
            m2_num = motor_numbers[motor2.name]
        except:
            raise ValueError('Undefined motor for fly scan')
        m1_pos = motor1.position
        m2_pos = motor2.position
        print(f"Initial positions: m1_pos={m1_pos}  m2_pos={m2_pos}")
        do_scan = False
        try:
            start1, range1 = m1_pos + scan_start1, scan_end1 - scan_start1
            start2, range2 = m2_pos + scan_start2, scan_end2 - scan_start2

            vx = range1/(exposure_time*num1)

            print(f"{vx = }")
            if (('merlin1' in [d.name for d in dets])):
                yield from bps.abs_set(merlin1.cam.acquire,0)

            if (('merlin1' in [d.name for d in dets])) and not merlin_cont_mode:

                yield from bps.abs_set(merlin1.cam.quad_merlin_mode,1) # 0-12 bit; 1-24bit;
                
                min_dead_time = 0.005
                if dead_time<min_dead_time:
                    print('Dead time set to %.1f ms for Merlin response time'%(min_dead_time*1000))
                    dead_time = min_dead_time

            if np.abs(vx)>200:
                raise ValueError('Stage scan speed too fast, check your input')

            return_speed = np.abs(return_speed)

            if return_speed>200:
                raise ValueError('Stage return speed too fast, check your input')

            start1_scan = float(start1) - vx*line_overhead[0]
            range1_scan = float(range1) + vx*(line_overhead[0] + line_overhead[1])
            step2 = float(range2)/num2

            # if apply_tomo_drift:
            #     if tomo_angle is None:
            #         tomo_angle = pt_tomo.th.user_setpoint.get()
            #     center1 = center1 + get_tomo_drift(tomo_angle)


            range_min, range_max = -16, 16
                
            for pos in [start1_scan, start1_scan + range1_scan, start2, start2 + range2]:
                if pos < range_min or pos > range_max:

                    raise ValueError(
                        f"Scan range exceed limits for the motors: "
                        f"start1={scan_start1} end1={scan_end1} start2={scan_start2} end2={scan_end2}"
                    )
                


            scan_input = [float(x) for x in [start1, start1+range1, num1, start2, start2+range2, num2]]
            # Metadata
            if md is None:
                md = {}
            if "scan" not in md:
                md["scan"] = {}
            # Scan metadata
            md['motors'] = [motor1.name, motor2.name]
            md['motor1'] = motor1.name
            md['motor2'] = motor2.name

            md['shape'] = [num1, num2]
            md['fly_type'] = 'grid'

            md['scan']['type'] = '2D_FLY_PANDA'
            md['scan']['scan_input'] = scan_input
            md['scan']['sample_name'] = ''

            md['scan']['detectors'] = [d.name for d in dets] + [panda_flyer.panda.name, panda_flyer.sclr.name]
            md['scan']['detector_distance'] = 2.05
            md['scan']['dwell'] = exposure_time
            md['scan']['fast_axis'] = {'motor_name' : motor1.name,
                                    'units' : motor1.motor_egu.get()}
            md['scan']['slow_axis'] = {'motor_name' : motor2.name,
                                    'units' : motor2.motor_egu.get()}
            md['scan']['shape'] = (num1, num2)

            kwargs.setdefault('panda_flyer', panda_flyer)

            ## Zebra is used to copy trigger pulses from panda to detectors and scaler
            yield from bps.abs_set(zebra.output[1].ttl.addr,4)
            yield from bps.abs_set(zebra.output[2].ttl.addr,4)
            if merlin_cont_mode:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            else:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            yield from bps.abs_set(zebra.output[4].ttl.addr,4)

            # Wait for Zebra
            yield from bps.sleep(0.1)

            panda = panda_flyer.panda

            ## Setup panda
            yield from bps.abs_set(panda.data.capture,0)

            yield from bps.abs_set(panda.pulse2.delay,line_overhead[0])
            yield from bps.abs_set(panda.pulse2.delay_units,'s')
            yield from bps.abs_set(panda.pulse2.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse2.width_units,'s')
            yield from bps.abs_set(panda.pulse2.step,exposure_time)
            yield from bps.abs_set(panda.pulse2.step_units,'s')
            yield from bps.abs_set(panda.pulse2.pulses,num1)

            yield from bps.abs_set(panda.pulse3.width,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.width_units,'s')
            yield from bps.abs_set(panda.pulse3.step,(exposure_time-dead_time)/position_supersample)
            yield from bps.abs_set(panda.pulse3.step_units,'s')
            yield from bps.abs_set(panda.pulse3.delay,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.delay_units,'s')
            yield from bps.abs_set(panda.pulse3.pulses,position_supersample)

            # PULSE 1 and PULSE 4 is modified on PandABox to read Zebra output pulse and add a delay to that for triggering scalers
            yield from bps.abs_set(panda.pulse1.width,0.00001000)
            yield from bps.abs_set(panda.pulse1.width_units,'s')
            yield from bps.abs_set(panda.pulse1.pulses,1)
            yield from bps.abs_set(panda.pulse1.trig_edge,'Rising')
            # yield from bps.abs_set(panda.pulse1.step,0)
            # yield from bps.abs_set(panda.pulse1.step_units,'s')
            yield from bps.abs_set(panda.pulse4.width,0.00001000)
            yield from bps.abs_set(panda.pulse4.width_units,'s')
            yield from bps.abs_set(panda.pulse4.pulses,1)
            yield from bps.abs_set(panda.pulse4.trig_edge,'Falling')

            # yield from bps.abs_set(panda.pulse4.step,0)
            # yield from bps.abs_set(panda.pulse4.step_units,'s')
            ## Move to start
            sl('#%djog=%f'%(m1_num,start1_scan))
            sl('#%djog=%f'%(m2_num,start2))

            ## Trigger to low
            sl('M100=0')

            if motor2.name == 'zpssy':
                # Wait for zpssy motor
                yield from bps.sleep(1)

            ## Wait for stages in bluesky
            count = 0
            while np.abs(motor1.position-start1_scan) + np.abs(motor2.position-start2) > 0.02:
                count += 1
                if count % 10 == 0:
                    print("Motors didn't reach starting position, moving again...")
                    sl('#%djog=%f'%(m1_num,start1_scan))
                    sl('#%djog=%f'%(m2_num,start2))

                    if count>50:
                        raise ValueError("Motors failed to reach start position, exiting the plan. Check scan range.")
                        

                    #may avoid when scan stucks if user had a non-zero strat position or motor is stuck 
                    #may need improvent if intial piezo positions are important  
                    # if motor2.name.startswith('zp'):
                    #    yield from piezos_to_zero(zp_flag = True)
                    # elif motor2.name.startswith('ds'):
                    #    yield from piezos_to_zero(zp_flag = False)
                    # else:
                    #    pass
                yield from bps.sleep(0.2)

            if motor2.name == 'zpssy':
                # Wait for zpssy motor
                yield from bps.sleep(1)

            ## Setup scanning program
            # if m1_num == 3:
            #     vx *= 20
            #     return_speed *=10
            sl('open prog 41;inc;linear;L1=0;')
            sl('while (L1<%d) {'%(num2-1))
            sl('M100=1;F(%.5f);x(%.5f);dwell 0;M100=0;F(%.5f);x(%.5f)y(%.5f);L1=L1+1;dwell %.2f;}'%(np.abs(vx),range1_scan,return_speed,-range1_scan,step2,line_dwell*1000))
            sl('M100=1;F(%.5f);x(%.5f);dwell 0;M100=0;'%(np.abs(vx),range1_scan))
            sl('dwell 0; close;')

            ## Define motors
            sl('&5abort;undefine;&6abort;undefine;&7abort;undefine;')
            sl('&6;#%d->x;#%d->y;'%(m1_num,m2_num))

            # print(f"dets={dets} args={args} kwargs={kwargs}")

            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            for d in dets:
                if d.name == 'xspress3' or d.name == 'xspress3_det2':
                    panda_live_plot.setup_plot(scan_input,d,panda_flyer.sclr)
            
            if motor1.name == 'dssx' or motor1.name == 'dssz':
                angle = dsth.user_readback.get()
            elif motor1.name == 'zpssx' or motor1.name == 'zpssz':
                angle = zpsth.user_readback.get()
            else:
                angle = 0

            scan_header = [motor1,range1,num1,motor2,range2,num2,angle]

            yield from flyscan_pd(dets, '&6begin41r', num1*num2, exposure_time, dead_time = dead_time, md=md, scan_dim = [num1,num2], position_supersample = position_supersample, merlin_cont_mode=merlin_cont_mode, scan_header = scan_header, **kwargs)

            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            # Undefine motors
            sl('&6abort;undefine;')
            if pos_return:
                mv_back = short_uid('back')
                if True: #motor1.name.startswith('zp'):
                    sl('#%djog=%f'%(m1_num,m1_pos))
                    sl('#%djog=%f'%(m2_num,m2_pos))

                    ## Wait for stages in bluesky
                    count = 0
                    while np.abs(motor1.position-m1_pos) + np.abs(motor2.position-m2_pos) > 0.02:
                        count += 1
                        if count % 10 == 0:
                            print("Motors didn't go back to starting position, moving again...")
                            sl('#%djog=%f'%(m1_num,m1_pos))
                            sl('#%djog=%f'%(m2_num,m2_pos))
                        yield from bps.sleep(0.2)
                else:
                    yield from bps.abs_set(motor1,m1_pos,group=mv_back)
                    yield from bps.abs_set(motor2,m2_pos,group=mv_back)
                    yield from bps.wait(group=mv_back)


def fly2dpd_repeat(dets, motor1, scan_start1, scan_end1, num1, motor2, scan_start2, scan_end2, num2,  exposure_time,panda_flyer = panda_flyer, repeat = 10, pos_return = True, apply_tomo_drift = False,
                tomo_angle = None, auto_rescan = False, dead_time = 0.0005, line_overhead = [0.01,0.01], line_dwell = 0.005, return_speed = 150.0, position_supersample = 10,
                md = None, merlin_cont_mode = False, **kwargs):
    """
    Relative scan
    """

    # PPMAC control signal
    sl = ppmac.gpascii.send_line

    # Motor numbers
    motor_numbers = {'ssx':3,
                     'ssy':4,
                     'ssz':5,
                     'zpssx':6,
                     'zpssy':7,
                     'zpssz':8,
                     'dssx':9,
                     'dssy':10,
                     'dssz':11}


    do_scan = True
    while do_scan:
        try:
            m1_num = motor_numbers[motor1.name]
            m2_num = motor_numbers[motor2.name]
        except:
            raise ValueError('Undefined motor for fly scan')
        m1_pos = motor1.position
        m2_pos = motor2.position
        print(f"Initial positions: m1_pos={m1_pos}  m2_pos={m2_pos}")
        do_scan = False
        try:
            start1, range1 = m1_pos + scan_start1, scan_end1 - scan_start1
            start2, range2 = m2_pos + scan_start2, scan_end2 - scan_start2

            vx = range1/(exposure_time*num1)

            if (('merlin1' in [d.name for d in dets])) and not merlin_cont_mode:
                yield from bps.abs_set(merlin1.cam.quad_merlin_mode,1) # 0-12 bit; 1-24bit;
                min_dead_time = 0.003
                if dead_time<min_dead_time:
                    print('Dead time set to %.1f ms for Merlin response time'%(min_dead_time*1000))
                    dead_time = min_dead_time

            if np.abs(vx)>200:
                raise ValueError('Stage scan speed too fast, check your input')

            return_speed = np.abs(return_speed)

            if return_speed>200:
                raise ValueError('Stage return speed too fast, check your input')

            start1_scan = float(start1) - vx*line_overhead[0]
            range1_scan = float(range1) + vx*(line_overhead[0] + line_overhead[1])
            step2 = float(range2)/num2

            # if apply_tomo_drift:
            #     if tomo_angle is None:
            #         tomo_angle = pt_tomo.th.user_setpoint.get()
            #     center1 = center1 + get_tomo_drift(tomo_angle)


            range_min, range_max = -16, 16
            for pos in [start1_scan, start1_scan + range1_scan, start2, start2 + range2]:
                if pos < range_min or pos > range_max:
                    raise ValueError(
                        f"Scan range exceed limits for the motors: "
                        f"start1={scan_start1} end1={scan_end1} start2={scan_start2} end2={scan_end2}"
                    )
            scan_input = [float(x) for x in [start1, start1+range1, num1, start2, start2+range2*repeat, num2*repeat]]
            # Metadata
            if md is None:
                md = {}
            if "scan" not in md:
                md["scan"] = {}
            # Scan metadata
            md['motors'] = [motor1.name, motor2.name]
            md['motor1'] = motor1.name
            md['motor2'] = motor2.name

            md['shape'] = [num1, num2*repeat]
            md['fly_type'] = 'grid'

            md['scan']['type'] = '2D_FLY_PANDA'
            md['scan']['scan_input'] = scan_input
            md['scan']['sample_name'] = ''

            md['scan']['detectors'] = [d.name for d in dets] + [panda_flyer.panda.name, panda_flyer.sclr.name]
            md['scan']['detector_distance'] = 2.05
            md['scan']['dwell'] = exposure_time
            md['scan']['fast_axis'] = {'motor_name' : motor1.name,
                                    'units' : motor1.motor_egu.get()}
            md['scan']['slow_axis'] = {'motor_name' : motor2.name,
                                    'units' : motor2.motor_egu.get()}
            md['scan']['shape'] = (num1, num2*repeat)

            kwargs.setdefault('panda_flyer', panda_flyer)

            ## Zebra is used to copy trigger pulses from panda to detectors and scaler
            yield from bps.abs_set(zebra.output[1].ttl.addr,4)
            yield from bps.abs_set(zebra.output[2].ttl.addr,4)
            if merlin_cont_mode:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            else:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            yield from bps.abs_set(zebra.output[4].ttl.addr,4)

            # Wait for Zebra
            yield from bps.sleep(0.1)

            panda = panda_flyer.panda

            ## Setup panda
            yield from bps.abs_set(panda.data.capture,0)

            yield from bps.abs_set(panda.pulse2.delay,line_overhead[0])
            yield from bps.abs_set(panda.pulse2.delay_units,'s')
            yield from bps.abs_set(panda.pulse2.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse2.width_units,'s')
            yield from bps.abs_set(panda.pulse2.step,exposure_time)
            yield from bps.abs_set(panda.pulse2.step_units,'s')
            yield from bps.abs_set(panda.pulse2.pulses,num1)

            yield from bps.abs_set(panda.pulse3.width,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.width_units,'s')
            yield from bps.abs_set(panda.pulse3.step,(exposure_time-dead_time)/position_supersample)
            yield from bps.abs_set(panda.pulse3.step_units,'s')
            yield from bps.abs_set(panda.pulse3.delay,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.delay_units,'s')
            yield from bps.abs_set(panda.pulse3.pulses,position_supersample)

            # PULSE 4 is modified on PandABox to read Zebra output pulse and add a delay to that for triggering scalers
            # yield from bps.abs_set(panda.pulse4.width,exposure_time-dead_time)
            # yield from bps.abs_set(panda.pulse4.width_units,'s')
            # yield from bps.abs_set(panda.pulse4.step,exposure_time)
            # yield from bps.abs_set(panda.pulse4.step_units,'s')
            # yield from bps.abs_set(panda.pulse4.pulses,1)

            ## Move to start
            sl('#%djog=%f'%(m1_num,start1_scan))
            sl('#%djog=%f'%(m2_num,start2))

            ## Trigger to low
            sl('M100=0')

            if motor2.name == 'zpssy':
                # Wait for zpssy motor
                yield from bps.sleep(1)

            ## Wait for stages in bluesky
            count = 0
            while np.abs(motor1.position-start1_scan) + np.abs(motor2.position-start2) > 0.02:
                count += 1
                if count % 10 == 0:
                    print("Motors didn't reach starting position, moving again...")
                    sl('#%djog=%f'%(m1_num,start1_scan))
                    sl('#%djog=%f'%(m2_num,start2))
                yield from bps.sleep(0.2)

            if motor2.name == 'zpssy':
                # Wait for zpssy motor
                yield from bps.sleep(1)

            ## Setup scanning program
            sl('open prog 41;inc;linear;L1=0;L2=0;')
            sl('while (L2<%d) { L1=0; while (L1<%d) {'%(repeat, num2-1))
            sl('M100=1;F(%.5f);x(%.5f);dwell 0;M100=0;F(%.5f);x(%.5f)y(%.5f);L1=L1+1;dwell %.2f;}'%(np.abs(vx),range1_scan,return_speed,-range1_scan,step2,line_dwell*1000))
            sl('M100=1;F(%.5f);x(%.5f);dwell 0;M100=0;F(%.5f);x(%.5f)y(%.5f);L2=L2+1;dwell %.2f;}'%(np.abs(vx),range1_scan,return_speed,-range1_scan,-range2+step2,line_dwell*1000))
            sl('dwell 0; close;')

            ## Define motors
            sl('&6abort;undefine;&7abort;undefine;')
            sl('&6;#%d->x;#%d->y;'%(m1_num,m2_num))

            # print(f"dets={dets} args={args} kwargs={kwargs}")

            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            for d in dets:
                if d.name == 'xspress3' or d.name == 'xspress3_det2':
                    panda_live_plot.setup_plot(scan_input,d,panda_flyer.sclr)

            yield from flyscan_pd(dets, '&6begin41r', num1*num2*repeat, exposure_time, dead_time = dead_time, md=md, scan_dim = [num1,num2*repeat], position_supersample = position_supersample, merlin_cont_mode=merlin_cont_mode, **kwargs)

            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            # Undefine motors
            sl('&5abort;undefine;&6abort;undefine;&7abort;undefine;')
            if pos_return:
                mv_back = short_uid('back')
                if motor1.name.startswith('zp'):
                    sl('#%djog=%f'%(m1_num,m1_pos))
                    sl('#%djog=%f'%(m2_num,m2_pos))

                    ## Wait for stages in bluesky
                    count = 0
                    while np.abs(motor1.position-m1_pos) + np.abs(motor2.position-m2_pos) > 0.02:
                        count += 1
                        if count % 10 == 0:
                            print("Motors didn't go back to starting position, moving again...")
                            sl('#%djog=%f'%(m1_num,m1_pos))
                            sl('#%djog=%f'%(m2_num,m2_pos))
                        yield from bps.sleep(0.2)
                else:
                    yield from bps.abs_set(motor1,m1_pos,group=mv_back)
                    yield from bps.abs_set(motor2,m2_pos,group=mv_back)
                    yield from bps.wait(group=mv_back)

def fly1dpd(dets, motor1, scan_start1, scan_end1, num1, exposure_time, panda_flyer = panda_flyer, pos_return = True, apply_tomo_drift = False,
                tomo_angle = None, auto_rescan = False, dead_time = 0.0005, line_overhead = [0.01,0.01], line_dwell = 0.1, return_speed = 100.0, position_supersample = 10,
                md = None, merlin_cont_mode = False, **kwargs):
    """
    Relative scan
    """

    # PPMAC control signal
    sl = ppmac.gpascii.send_line

    # Motor numbers
    motor_numbers = {'ssx':3,
                     'ssy':4,
                     'ssz':5,
                     'zpssx':6,
                     'zpssy':7,
                     'zpssz':8,
                     'dssx':9,
                     'dssy':10,
                     'dssz':11}


    do_scan = True
    while do_scan:
        try:
            m1_num = motor_numbers[motor1.name]
        except:
            raise ValueError('Undefined motor for fly scan')
        m1_pos = motor1.position
        print(f"Initial positions: m1_pos={m1_pos}")
        do_scan = False
        try:
            start1, range1 = m1_pos + scan_start1, scan_end1 - scan_start1

            vx = range1/(exposure_time*num1)
            num2 = 1

            if (('merlin1' in [d.name for d in dets]) or ('merlin2' in [d.name for d in dets])) and not merlin_cont_mode:
                if dead_time<0.003:
                    print('Dead time set to 3 ms for Merlin response time')
                    dead_time = 0.003

            if np.abs(vx)>200:
                raise ValueError('Stage scan speed too fast, check your input')

            return_speed = np.abs(return_speed)

            if return_speed>200:
                raise ValueError('Stage return speed too fast, check your input')

            start1_scan = float(start1) - vx*line_overhead[0]
            range1_scan = float(range1) + vx*(line_overhead[0] + line_overhead[1])

            # if apply_tomo_drift:
            #     if tomo_angle is None:
            #         tomo_angle = pt_tomo.th.user_setpoint.get()
            #     center1 = center1 + get_tomo_drift(tomo_angle)


            range_min, range_max = -16, 16
            for pos in [start1_scan, start1_scan + range1_scan]:
                if pos < range_min or pos > range_max:
                    raise ValueError(
                        f"Scan range exceed limits for the motors: "
                        f"start1={scan_start1} end1={scan_end1}"
                    )
            scan_input = [float(x) for x in [start1, start1+range1, num1]]
            # Metadata
            if md is None:
                md = {}
            if "scan" not in md:
                md["scan"] = {}
            # Scan metadata
            md['motors'] = [motor1.name]
            md['motor1'] = motor1.name

            md['shape'] = [num1, num2]
            md['fly_type'] = 'grid'

            md['scan']['type'] = '1D_FLY_PANDA'
            md['scan']['scan_input'] = scan_input
            md['scan']['sample_name'] = ''

            md['scan']['detectors'] = [d.name for d in dets] + [panda_flyer.panda.name, panda_flyer.sclr.name]
            md['scan']['detector_distance'] = 2.05
            md['scan']['dwell'] = exposure_time
            md['scan']['fast_axis'] = {'motor_name' : motor1.name,
                                    'units' : motor1.motor_egu.get()}
            md['scan']['shape'] = (num1, num2)

            kwargs.setdefault('panda_flyer', panda_flyer)

            ## Zebra is used to copy trigger pulses from panda to detectors and scaler
            yield from bps.abs_set(zebra.output[1].ttl.addr,4)
            yield from bps.abs_set(zebra.output[2].ttl.addr,4)
            if merlin_cont_mode:
                yield from bps.abs_set(zebra.output[3].ttl.addr,55)
            else:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            yield from bps.abs_set(zebra.output[4].ttl.addr,4)

            # Wait for Zebra
            yield from bps.sleep(0.1)

            panda = panda_flyer.panda

            ## Setup panda
            yield from bps.abs_set(panda.data.capture,0)

            yield from bps.abs_set(panda.pulse2.delay,line_overhead[0])
            yield from bps.abs_set(panda.pulse2.delay_units,'s')
            yield from bps.abs_set(panda.pulse2.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse2.width_units,'s')
            yield from bps.abs_set(panda.pulse2.step,exposure_time)
            yield from bps.abs_set(panda.pulse2.step_units,'s')
            yield from bps.abs_set(panda.pulse2.pulses,num1)

            yield from bps.abs_set(panda.pulse3.width,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.width_units,'s')
            yield from bps.abs_set(panda.pulse3.step,(exposure_time-dead_time)/position_supersample)
            yield from bps.abs_set(panda.pulse3.step_units,'s')
            yield from bps.abs_set(panda.pulse3.delay,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.delay_units,'s')
            yield from bps.abs_set(panda.pulse3.pulses,position_supersample)

            # PULSE 4 is modified on PandABox to read Zebra output pulse and add a delay to that for triggering scalers
            # yield from bps.abs_set(panda.pulse4.width,exposure_time-dead_time)
            # yield from bps.abs_set(panda.pulse4.width_units,'s')
            # yield from bps.abs_set(panda.pulse4.step,exposure_time)
            # yield from bps.abs_set(panda.pulse4.step_units,'s')
            # yield from bps.abs_set(panda.pulse4.pulses,1)

            ## Move to start
            sl('#%djog=%f'%(m1_num,start1_scan))

            ## Trigger to low
            sl('M100=0')

            ## Wait for stages in bluesky
            count = 0
            while np.abs(motor1.position-start1_scan)> 0.02:
                count += 1
                if count % 10 == 0:
                    print("Motors didn't reach starting position, moving again...")
                    sl('#%djog=%f'%(m1_num,start1_scan))
                yield from bps.sleep(0.2)

            ## Setup scanning program
            sl('open prog 41;inc;linear;L1=0;')
            sl('dwell %.2f;M100=1;F(%.5f);x(%.5f);dwell 0;M100=0;'%(line_dwell*1000,np.abs(vx),range1_scan))
            sl('dwell 0; close;')

            ## Define motors
            sl('&6abort;undefine;&7abort;undefine;')
            sl('&6;#%d->x;'%(m1_num))

            # print(f"dets={dets} args={args} kwargs={kwargs}")

            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            for d in dets:
                if d.name == 'xspress3' or d.name == 'xspress3_det2':
                    panda_live_plot.setup_plot(scan_input,d,panda_flyer.sclr)
            yield from flyscan_pd(dets, '&6begin41r', num1*num2, exposure_time, dead_time = dead_time, md=md, scan_dim = [num1,num2], position_supersample = position_supersample, merlin_cont_mode=merlin_cont_mode, **kwargs)


            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            # Undefine motors
            sl('&6abort;undefine;')
            if pos_return:
                mv_back = short_uid('back')
                if motor1.name.startswith('zp'):
                    sl('#%djog=%f'%(m1_num,m1_pos))

                    ## Wait for stages in bluesky
                    count = 0
                    while np.abs(motor1.position-m1_pos)> 0.02:
                        count += 1
                        if count % 10 == 0:
                            print("Motors didn't go back to starting position, moving again...")
                            sl('#%djog=%f'%(m1_num,m1_pos))
                        yield from bps.sleep(0.2)
                else:
                    yield from bps.abs_set(motor1,m1_pos,group=mv_back)
                    yield from bps.wait(group=mv_back)

def fly2dcontpd(dets, motor1, scan_start1, scan_end1, num1, motor2, scan_start2, scan_end2, num2, exposure_time,panda_flyer = panda_flyer,  pos_return = True, apply_tomo_drift = False,
                tomo_angle = None, auto_rescan = False, dead_time = 0.0002, scan_overhead = [0.1,0.05],
                md = None, merlin_cont_mode = False, **kwargs):
    """
    Relative scan
    """

    # PPMAC control signal
    sl = ppmac.gpascii.send_line

    # Motor numbers
    motor_numbers = {'ssx':3,
                     'ssy':4,
                     'ssz':5,
                     'zpssx':6,
                     'zpssy':7,
                     'zpssz':8,
                     'dssx':9,
                     'dssy':10,
                     'dssz':11}

    do_scan = True
    while do_scan:
        try:
            m1_num = motor_numbers[motor1.name]
            m2_num = motor_numbers[motor2.name]
        except:
            raise ValueError('Undefined motor for fly scan')
        m1_pos = motor1.position
        m2_pos = motor2.position
        print(f"Initial positions: m1_pos={m1_pos}  m2_pos={m2_pos}")
        do_scan = False
        try:
            start1, range1 = m1_pos + scan_start1, scan_end1 - scan_start1
            start2, range2 = m2_pos + scan_start2, scan_end2 - scan_start2

            vx = range1/(exposure_time*num1)
            vy = range2/(exposure_time*num1*num2)

            if np.abs(vx)>200:
                raise ValueError('Stage scan speed too fast, check your input')

            start1_scan = float(start1)
            range1_scan = float(range1)
            start2_scan = float(start2) - vy*scan_overhead[0]
            range2_scan = float(range2) + vy*(scan_overhead[0] + scan_overhead[1])

            # if apply_tomo_drift:
            #     if tomo_angle is None:
            #         tomo_angle = pt_tomo.th.user_setpoint.get()
            #     center1 = center1 + get_tomo_drift(tomo_angle)


            range_min, range_max = -16, 16
            for pos in [start1_scan, start1_scan + range1_scan, start2_scan, start2_scan + range2_scan]:
                if pos < range_min or pos > range_max:
                    raise ValueError(
                        f"Scan range exceed limits for the motors: "
                        f"start1={scan_start1} end1={scan_end1} start2={scan_start2} end2={scan_end2}"
                    )
            scan_input = [float(x) for x in [start1, start1+range1, num1, start2, start2+range2, num2]]
            # Metadata
            if md is None:
                md = {}
            if "scan" not in md:
                md["scan"] = {}
            # Scan metadata
            md['motors'] = [motor1.name, motor2.name]
            md['motor1'] = motor1.name
            md['motor2'] = motor2.name

            md['shape'] = [num1, num2]
            md['fly_type'] = 'pyramid'

            md['scan']['type'] = '2D_FLY_CONT_PANDA'
            md['scan']['scan_input'] = scan_input
            md['scan']['sample_name'] = ''

            md['scan']['detectors'] = [d.name for d in dets] + [panda_flyer.panda.name, panda_flyer.sclr.name]
            md['scan']['detector_distance'] = 2.05
            md['scan']['dwell'] = exposure_time
            md['scan']['fast_axis'] = {'motor_name' : motor1.name,
                                    'units' : motor1.motor_egu.get()}
            md['scan']['slow_axis'] = {'motor_name' : motor2.name,
                                    'units' : motor2.motor_egu.get()}
            md['scan']['shape'] = (num1, num2)

            kwargs.setdefault('panda_flyer', panda_flyer)

            ## Zebra is used to copy trigger pulses from panda to detectors and scaler
            yield from bps.abs_set(zebra.output[1].ttl.addr,4)
            yield from bps.abs_set(zebra.output[2].ttl.addr,4)
            if merlin_cont_mode:
                yield from bps.abs_set(zebra.output[3].ttl.addr,55)
            else:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            yield from bps.abs_set(zebra.output[4].ttl.addr,4)


            # Wait for Zebra
            yield from bps.sleep(0.1)
            panda = panda_flyer.panda

            ## Setup panda
            yield from bps.abs_set(panda.data.capture,0)

            yield from bps.abs_set(panda.pulse2.delay,scan_overhead[0])
            yield from bps.abs_set(panda.pulse2.delay_units,'s')
            yield from bps.abs_set(panda.pulse2.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse2.width_units,'s')
            yield from bps.abs_set(panda.pulse2.step,exposure_time)
            yield from bps.abs_set(panda.pulse2.step_units,'s')
            yield from bps.abs_set(panda.pulse2.pulses,num1*num2)

            yield from bps.abs_set(panda.pulse3.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse3.width_units,'s')
            yield from bps.abs_set(panda.pulse3.step,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse3.step_units,'s')
            yield from bps.abs_set(panda.pulse3.pulses,1)

            # PULSE 4 is modified on PandABox to read Zebra output pulse and add a delay to that for triggering scalers
            # yield from bps.abs_set(panda.pulse4.width,exposure_time-dead_time)
            # yield from bps.abs_set(panda.pulse4.width_units,'s')
            # yield from bps.abs_set(panda.pulse4.step,exposure_time-dead_time)
            # yield from bps.abs_set(panda.pulse4.step_units,'s')
            # yield from bps.abs_set(panda.pulse4.pulses,1)

            ## Move to start
            sl('#%djog=%f'%(m1_num,start1_scan))
            sl('#%djog=%f'%(m2_num,start2))

            ## Trigger to low
            sl('M100=0')

            ## Wait for stages in bluesky
            while np.abs(motor1.position-start1_scan) + np.abs(motor2.position-start2) > 0.02:
                yield from bps.sleep(0.2)

            ## Setup scanning program
            sl('open prog 41;inc;linear;L1=0;M100=1;F(%.5f);'%(np.abs(vx)))
            sl('while (L1<%d) {'%(num2+2))
            sl('x(%.5f);dwell 0;x(%.5f);L1=L1+1;dwell 0;}'%(range1_scan,-range1_scan))
            sl('dwell 0; close;')
            sl('open prog 42;inc;linear;')
            sl('F(%.5f);y(%.5f);dwell 0;close;'%(np.abs(vy),range2_scan))

            ## Define motors
            sl('&6abort;undefine;&7abort;undefine;')
            sl('&6;#%d->x;&7;#%d->y;'%(m1_num,m2_num))

            start_signal = '&6begin41r;&7begin42r'

            # print(f"dets={dets} args={args} kwargs={kwargs}")

            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            #if xspress3 in dets:
            #    panda_live_plot.setup_plot(scan_input)
            yield from flyscan_pd(dets, start_signal, num1*num2, exposure_time, dead_time = dead_time, md=md, scan_dim = [num1,num2], merlin_cont_mode = merlin_cont_mode, **kwargs)


            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            # Undefine motors
            sl('&6abort;undefine;&7abort;undefine;')
            if pos_return:
                mv_back = short_uid('back')
                yield from abs_set(motor1,m1_pos,group=mv_back)
                yield from abs_set(motor2,m2_pos,group=mv_back)
                yield from bps.wait(group=mv_back)


def timescanpd(dets, num, exposure_time, panda_flyer = panda_flyer, pos_return = True, apply_tomo_drift = False,
                tomo_angle = None, auto_rescan = False, dead_time = 0.0005, line_overhead = [0.01,0.01], line_dwell = 0.1, return_speed = 100.0, position_supersample = 10,
                md = None, merlin_cont_mode = False, wait_for_start_input = True, **kwargs):
    """
    Relative scan
    """

    # PPMAC control signal
    sl = ppmac.gpascii.send_line

    # Motor numbers
    motor_numbers = {'ssx':3,
                     'ssy':4,
                     'ssz':5,
                     'zpssx':6,
                     'zpssy':7,
                     'zpssz':8,
                     'dssx':9,
                     'dssy':10,
                     'dssz':11}


    do_scan = True
    while do_scan:
        do_scan = False
        try:

            if (('merlin1' in [d.name for d in dets])) and not merlin_cont_mode:
                yield from bps.abs_set(merlin1.cam.quad_merlin_mode,1) # 0-12 bit; 1-24bit;
                min_dead_time = 0.003
                if dead_time<min_dead_time:
                    print('Dead time set to %.1f ms for Merlin response time'%(min_dead_time*1000))
                    dead_time = min_dead_time

            scan_input = [float(x) for x in [num]]
            # Metadata
            if md is None:
                md = {}
            if "scan" not in md:
                md["scan"] = {}
            # Scan metadata
            md['shape'] = [num, 1]
            md['fly_type'] = 'grid'

            md['scan']['type'] = 'TIME_FLY_PANDA'
            md['scan']['scan_input'] = scan_input
            md['scan']['sample_name'] = ''

            md['scan']['detectors'] = [d.name for d in dets] + [panda_flyer.panda.name, panda_flyer.sclr.name]
            md['scan']['detector_distance'] = 2.05
            md['scan']['dwell'] = exposure_time
            md['scan']['shape'] = (num, 1)

            kwargs.setdefault('panda_flyer', panda_flyer)

            ## Zebra is used to copy trigger pulses from panda to detectors and scaler
            yield from bps.abs_set(zebra.output[1].ttl.addr,4)
            yield from bps.abs_set(zebra.output[2].ttl.addr,4)
            if merlin_cont_mode:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            else:
                yield from bps.abs_set(zebra.output[3].ttl.addr,4)
            yield from bps.abs_set(zebra.output[4].ttl.addr,4)

            # Wait for Zebra
            yield from bps.sleep(0.1)
            panda = panda_flyer.panda

            ## Setup panda
            yield from bps.abs_set(panda.data.capture,0)

            yield from bps.abs_set(panda.pulse2.delay,line_overhead[0])
            yield from bps.abs_set(panda.pulse2.delay_units,'s')
            yield from bps.abs_set(panda.pulse2.width,exposure_time-dead_time)
            yield from bps.abs_set(panda.pulse2.width_units,'s')
            yield from bps.abs_set(panda.pulse2.step,exposure_time)
            yield from bps.abs_set(panda.pulse2.step_units,'s')
            yield from bps.abs_set(panda.pulse2.pulses,num)

            yield from bps.abs_set(panda.pulse3.width,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.width_units,'s')
            yield from bps.abs_set(panda.pulse3.step,(exposure_time-dead_time)/position_supersample)
            yield from bps.abs_set(panda.pulse3.step_units,'s')
            yield from bps.abs_set(panda.pulse3.delay,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda.pulse3.delay_units,'s')
            yield from bps.abs_set(panda.pulse3.pulses,position_supersample)

            # PULSE 4 is modified on PandABox to read Zebra output pulse and add a delay to that for triggering scalers
            # yield from bps.abs_set(panda.pulse4.width,exposure_time-dead_time)
            # yield from bps.abs_set(panda.pulse4.width_units,'s')
            # yield from bps.abs_set(panda.pulse4.step,exposure_time)
            # yield from bps.abs_set(panda.pulse4.step_units,'s')
            # yield from bps.abs_set(panda.pulse4.pulses,1)

            ## Trigger to low
            sl('M100=0')

            ## Setup scanning program
            sl('open prog 41; M100=1; dwell %.2f; M100=0;'%(num*exposure_time))
            sl('dwell 0; close;')

            ## Define motors
            sl('&6abort;undefine;&7abort;undefine;')

            # print(f"dets={dets} args={args} kwargs={kwargs}")

            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            for d in dets:
                if d.name == 'xspress3' or d.name == 'xspress3_det2':
                    panda_live_plot.setup_plot(scan_input,d,panda_flyer.sclr)
            yield from flyscan_pd(dets, '&6begin41r', num, exposure_time, dead_time = dead_time, md=md, scan_dim = [num,1], position_supersample = position_supersample, merlin_cont_mode=merlin_cont_mode, wait_for_start_input = wait_for_start_input, **kwargs)


            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            pass

