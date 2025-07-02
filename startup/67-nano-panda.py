if not USE_RASMI:
    print(f"RASMI not used, skipping {__file__!r} ...")
    import sys
    sys.exit()

print(f"Loading {__file__!r} ...")
from collections import OrderedDict

from epics import caput, caget
import os
import threading
import h5py
import numpy as np
import time as ttime
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt
from hxntools.detectors.zebra import Zebra, EpicsSignalWithRBV
from databroker.assets.handlers import HandlerBase
from ophyd.areadetector.filestore_mixins import resource_factory


xs = None  # No Xspress3
# use_sclr = False  # Set this False to run zebra without 'sclr'
use_sclr = True



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

#class DATA(Device):
#    hdf_directory = Cpt(EpicsSignal, "HDFDirectory", string=True)
#    hdf_file_name = Cpt(EpicsSignal, "HDFFileName", string=True)
#    num_capture = Cpt(EpicsSignal, "NumCapture")
#    num_captured = Cpt(EpicsSignal, "NumCaptured")
#    flush_period = Cpt(EpicsSignal, "FlushPeriod")
#    capture = Cpt(EpicsSignal, "Capture")
#    capture_mode = Cpt(EpicsSignal, "CaptureMode", string=True)
#    status = Cpt(EpicsSignal, "Status", string=True)
#
#
#class PCOMP(Device):
#    pre_start = Cpt(EpicsSignal, "PRE_START")
#    start = Cpt(EpicsSignal, "START")
#    width = Cpt(EpicsSignal, "WIDTH")
#    step = Cpt(EpicsSignal, "STEP")
#    pulses = Cpt(EpicsSignal, "PULSES")
#
#
#class PCAP(Device):
#    arm = Cpt(EpicsSignal, "ARM")
#    active = Cpt(EpicsSignal, "ACTIVE")
#
#
#class CLOCK(Device):
#    period = Cpt(EpicsSignal, "PERIOD")
#    period_units = Cpt(EpicsSignal, "PERIOD:UNITS")
#
#
#class COUNTER(Device):
#    start = Cpt(EpicsSignal, "START")
#    step = Cpt(EpicsSignal, "STEP")
#    max = Cpt(EpicsSignal, "MAX")
#    min = Cpt(EpicsSignal, "MIN")
#
#
#class INENC(Device):
#    val = Cpt(EpicsSignal, "VAL")
#    setp = Cpt(EpicsSignal, "SETP")
#
#
#class POSITION(Device):
#    units = Cpt(EpicsSignal, "UNITS", string=True)
#    scale = Cpt(EpicsSignal, "SCALE")
#    offset = Cpt(EpicsSignal, "OFFSET")
#
#
#class POSITIONS(Device):
#    inenc1 = Cpt(POSITION, "12:")
#    inenc2 = Cpt(POSITION, "13:")
#
#
#class PULSE(Device):
#    delay_units = Cpt(EpicsSignal, "DELAY:UNITS", string=True)
#    delay = Cpt(EpicsSignal, "DELAY")
#    width_units = Cpt(EpicsSignal, "WIDTH:UNITS", string=True)
#    width = Cpt(EpicsSignal, "WIDTH")
#
#
#class BITS(Device):
#    A = Cpt(EpicsSignal, "A")
#    B = Cpt(EpicsSignal, "B")
#    C = Cpt(EpicsSignal, "C")
#    D = Cpt(EpicsSignal, "D")
#
#
#class PandA_Ophyd1(Device):
#    pcap = Cpt(PCAP, "PCAP:")
#    data = Cpt(DATA, "DATA:")
#    pcomp1 = Cpt(PCOMP, "PCOMP1:")
#    pcomp2 = Cpt(PCOMP, "PCOMP2:")
#    clock1 = Cpt(CLOCK, "CLOCK1:")
#    clock2 = Cpt(CLOCK, "CLOCK2:")
#    counter1 = Cpt(COUNTER, "COUNTER1:")
#    counter2 = Cpt(COUNTER, "COUNTER2:")
#    counter3 = Cpt(COUNTER, "COUNTER3:")
#    inenc1 = Cpt(INENC, "INENC1:")
#    inenc2 = Cpt(INENC, "INENC2:")
#    pulse2 = Cpt(PULSE, "PULSE2:")
#    pulse3 = Cpt(PULSE, "PULSE3:")
#    positions = Cpt(POSITIONS, "POSITIONS:")
#    bits = Cpt(BITS, "BITS:")
#
#
#panda1 = PandA_Ophyd1("XF03IDC-ES-PANDA-1:", name="panda1")
#
#
#class ExportSISDataPanda:
#    def __init__(self):
#        self._fp = None
#        self._filepath = None
#
#    def open(self, filepath, mca_names, ion, panda):
#        self.close()
#        self._filepath = filepath
#        self._fp = h5py.File(filepath, "w", libver="latest")
#
#        self._fp.swmr_mode = True
#
#        self._ion = ion
#        self._panda = panda
#        self._mca_names = mca_names
#
#        def create_ds(ds_name):
#            ds = self._fp.create_dataset(ds_name, data=np.array([], dtype="f"), maxshape=(None,), dtype="f")
#
#        for ds_name in self._mca_names:
#            create_ds(ds_name)
#
#        self._fp.flush()
#
#    def close(self):
#        if self._fp:
#            self._fp.close()
#            self._fp = None
#
#    def __del__(self):
#        self.close()
#
#    def export(self):
#
#        n_mcas = len(self._mca_names)
#
#        mca_data = []
#        for n in range(1, n_mcas + 1):
#            mca = self._ion.mca_by_index[n].spectrum.get(timeout=5.0)
#            mca_data.append(mca)
#
#        correct_length = int(self._panda.data.num_captured.get())
#
#        for n in range(len(mca_data)):
#            mca = mca_data[n]
#            # print(f"Number of mca points: {len(mca)}")
#            # mca = mca[1::2]
#            if len(mca) != correct_length:
#                print(f"Incorrect number of points ({len(mca)}) loaded from MCA{n + 1}: {correct_length} points are expected")
#                if len(mca > correct_length):
#                    mca = mca[:correct_length]
#                else:
#                    mca = np.append(mca, [1e10] * (correct_length - len(mca)))
#            mca_data[n] = mca
#
#        j = 0
#        while self._panda.data.capture.get() == 1:
#            print("Waiting for zebra...")
#            ttime.sleep(0.1)
#            j += 1
#            if j > 10:
#                print("THE ZEBRA IS BEHAVING BADLY CARRYING ON")
#                break
#
#        def add_data(ds_name, data):
#            ds = self._fp[ds_name]
#            n_ds = ds.shape[0]
#            ds.resize((n_ds + len(data),))
#            ds[n_ds:] = np.array(data)
#
#        for n, name in enumerate(self._mca_names):
#            add_data(name, np.asarray(mca_data[n]))
#
#        self._fp.flush()
#
#class HXNFlyerPanda(Device):
#    """
#    This is the Panda1.
#    """
#
#    LARGE_FILE_DIRECTORY_WRITE_PATH = LARGE_FILE_DIRECTORY_PATH
#    LARGE_FILE_DIRECTORY_READ_PATH = LARGE_FILE_DIRECTORY_PATH
#    LARGE_FILE_DIRECTORY_ROOT = LARGE_FILE_DIRECTORY_ROOT
#
#    KNOWN_DETS = {"eiger_mobile"}
#
#    @property
#    def detectors(self):
#        return tuple(self._dets)
#
#    @detectors.setter
#    def detectors(self, value):
#        dets = tuple(value)
#        if not all(d.name in self.KNOWN_DETS for d in dets):
#            raise ValueError(
#                f"One or more of {[d.name for d in dets]}"
#                f"is not known to the zebra. "
#                f"The known detectors are {self.KNOWN_DETS})"
#            )
#        self._dets = dets
#
#    @property
#    def sclr(self):
#        return self._sis
#
#    def __init__(self, panda,dets,sclr, motor=None, root_dir=None, **kwargs):
#        super().__init__("", parent=None, **kwargs)
#        self.name = "PandaFlyer"
#        if root_dir is None:
#            root_dir = self.LARGE_FILE_DIRECTORY_ROOT
#        self._mode = "idle"
#        self._dets = dets
#        self._sis = sclr
#        self._root_dir = root_dir
#        self._resource_document, self._datum_factory = None, None
#        self._document_cache = deque()
#        self._last_bulk = None
#
#        self._point_counter = None
#        self.frame_per_point = None
#
#        self.panda = panda
#        self.motor = motor
#
#        self._document_cache = []
#        self._resource_document = None
#        self._datum_factory = None
#
#        if self._sis is not None:
#            self._data_sis_exporter = ExportSISDataPanda()
#
#        type_map = {"int32": "<i4", "float32": "<f4", "float64": "<f8"}
#
#        self.fields = {
#            # "counter1_out": {
#            #     "value": "COUNTER1.OUT.Value",
#            #     "dtype_str": type_map["float64"],
#            # },
#            "inenc1_val": {
#                "value": "INENC1.VAL.Value",
#                "dtype_str": type_map["int32"],
#            },
#            "inenc2_val": {
#                "value": "INENC2.VAL.Value",
#                "dtype_str": type_map["int32"],
#            },
#            "inenc3_val": {
#                "value": "INENC3.VAL.Value",
#                "dtype_str": type_map["int32"],
#            },
#            "inenc4_val": {
#                "value": "INENC4.VAL.Value",
#                "dtype_str": type_map["int32"],
#            },
#            "pcap_ts_trig": {
#                "value": "PCAP.TS_TRIG.Value",
#                "dtype_str": type_map["float64"],
#            },
#        }
#        self.panda.data.hdf_directory.put_complete = True
#        self.panda.data.hdf_file_name.put_complete = True
#
#    def stage(self):
#        super().stage()
#
#    def unstage(self):
#        self._point_counter = None
#        if self._sis is not None:
#            self._data_sis_exporter.close()
#        super().unstage()
#
#    def kickoff(self, *, num, dwell):
#        """Kickoff the acquisition process."""
#        # Prepare parameters:
#        self._document_cache = deque()
#        self._datum_docs = {}
#        self._counter = itertools.count()
#        self._point_counter = 0
#
#        self.frame_per_point = int(num)
#        self._npts = int(num)
#        # Prepare 'resource' factory.
#        now = datetime.now()
#        self.fl_path = self.LARGE_FILE_DIRECTORY_WRITE_PATH
#        self.fl_name = f"panda_rbdata_{now.strftime('%Y%m%d_%H%M%S')}_{short_uid()}.h5"
#
#        resource_path = self.fl_name
#        self._resource_document, self._datum_factory, _ = compose_resource(
#            start={"uid": "needed for compose_resource() but will be discarded"},
#            spec="PANDA",
#            root=self.fl_path,
#            resource_path=resource_path,
#            resource_kwargs={},
#        )
#        # now discard the start uid, a real one will be added later
#        self._resource_document.pop("run_start")
#        self._document_cache.append(("resource", self._resource_document))
#
#        for key, value in self.fields.items():
#            datum_document = self._datum_factory(datum_kwargs={"field": value["value"]})
#            self._document_cache.append(("datum", datum_document))
#            self._datum_docs[key] = datum_document
#
#        if self._sis is not None:
#            # Put SIS3820 into single count (not autocount) mode
#            self.stage_sigs[self._sis.count_mode] = 0
#            self.stage_sigs[self._sis.count_on_start] = 1
#            # Stop the SIS3820
#            self._sis.stop_all.put(1)
#
#        self.__filename_sis = "{}.h5".format(uuid.uuid4())
#        print(self.__filename_sis)
#        self.__read_filepath_sis = os.path.join(
#            self.LARGE_FILE_DIRECTORY_READ_PATH, self.__filename_sis
#        )
#        self.__write_filepath_sis = os.path.realpath(os.path.join(
#            self.LARGE_FILE_DIRECTORY_WRITE_PATH, self.__filename_sis
#        ))
#
#        self.__filestore_resource_sis, self._datum_factory_sis = resource_factory(
#            SISHDF5Handler.HANDLER_NAME,
#            root=self.LARGE_FILE_DIRECTORY_ROOT,
#            resource_path=self.__read_filepath_sis,
#            resource_kwargs={"frame_per_point": self.frame_per_point},
#            path_semantics="posix",
#        )
#
#        resources = [self.__filestore_resource_sis]
#        if self._sis:
#            resources.append(self.__filestore_resource_sis)
#        self._document_cache.extend(("resource", _) for _ in resources)
#
#        if self._sis is not None:
#            sis_mca_names = self._sis_mca_names()
#            self._data_sis_exporter.open(
#                self.__write_filepath_sis, mca_names=sis_mca_names, ion=self._sis, panda=self.panda
#            )
#
#        # Kickoff panda process:
#        print(f"[Panda]Starting acquisition ...")
#
#        self.panda.data.hdf_directory.set(self.fl_path).wait()
#        self.panda.data.hdf_file_name.set(self.fl_name).wait()
#        self.panda.data.flush_period.set(1).wait()
#
#        self.panda.data.capture_mode.set("FIRST_N").wait()
#        self.panda.data.num_capture.set(self.frame_per_point).wait()
#
#        self.panda.pcap.arm.set(1).wait()
#
#        self.panda.data.capture.set(1).wait()
#
#        return NullStatus()
#
#    def complete(self):
#        print("[Panda]complete")
#        """Wait for the acquisition process started in kickoff to complete."""
#        # Wait until done
#        while (self.panda.data.capture.get() == 1):
#            time.sleep(0.01)
#
#        self.panda.pcap.arm.set(0).wait()
#
#        for d in self._dets:
#            d.stop(success=True)
#
#
#        if self._sis:
#            sis_mca_names = self._sis_mca_names()
#            sis_datum = []
#            for name in sis_mca_names:
#                sis_datum.append(self._datum_factory_sis({"column": name, "point_number": self._point_counter}))
#
#
#        if self._sis:
#            self._document_cache.extend(("datum", d) for d in sis_datum)
#
#        for d in self._dets:
#            self._document_cache.extend(d.collect_asset_docs())
#
#        # @timer_wrapper
#        def get_sis_data():
#            if self._sis is None:
#                return
#            self._data_sis_exporter.export()
#
#        get_sis_data()
#
#        print("[Panda]collect data")
#
#        data_dict = {
#            key: datum_doc["datum_id"] for key, datum_doc in self._datum_docs.items()
#        }
#
#        now = ttime.time()  # TODO: figure out how to get it from PandABox (maybe?)
#        self._last_bulk = {
#            "data": data_dict,
#            "timestamps": {key: now for key in self._datum_docs},
#            "time": now,
#            "filled": {key: False for key in self._datum_docs},
#        }
#
#        if self._sis:
#            self._last_bulk["data"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})
#            self._last_bulk["timestamps"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})
#
#        for d in self._dets:
#            reading = d.read()
#            self._last_bulk["data"].update(
#                {k: v["value"] for k, v in reading.items()}
#                )
#            self._last_bulk["timestamps"].update(
#                {k: v["timestamp"] for k, v in reading.items()}
#            )
#
#        return NullStatus()
#
#    def describe_collect(self):
#        """Describe the data structure."""
#        return_dict = {"primary": OrderedDict()}
#        desc = return_dict["primary"]
#
#        ext_spec = "FileStore:"
#
#        spec = {
#            "external": ext_spec,
#            "dtype": "array",
#            "shape": [self._npts],
#            "source": "",  # make this the PV of the array the det is writing
#        }
#
#        for key, value in self.fields.items():
#            desc.update(
#                {
#                    key: {
#                        "source": "PANDA",
#                        "dtype": "array",
#                        "dtype_str": value["dtype_str"],
#                        "shape": [
#                            self.frame_per_point
#                        ],  # TODO: figure out variable shape
#                        "external": "FILESTORE:",
#                    }
#                }
#            )
#
#        for d in self._dets:
#            desc.update(d.describe())
#
#        if self._sis is not None:
#            sis_mca_names = self._sis_mca_names()
#            for n, name in enumerate(sis_mca_names):
#                desc[name] = spec
#                desc[name]["source"] = self._sis.mca_by_index[n + 1].spectrum.pvname
#
#        return return_dict
#
#    def collect(self):
#        yield self._last_bulk
#        self._point_counter += 1
#
#    def collect_asset_docs(self):
#        """The method to collect resource/datum documents."""
#        items = list(self._document_cache)
#        self._document_cache.clear()
#        yield from items
#
#    def _sis_mca_names(self):
#        n_mcas = n_scaler_mca
#        return [getattr(self._sis.channels, f"chan{_}").name for _ in range(1, n_mcas + 1)]
#
#panda_flyer = HXNFlyerPanda(panda1,[],sclr3,name="PandaFlyer")
#
#class PandAHandlerHDF5(HandlerBase):
#    """The handler to read HDF5 files produced by PandABox."""
#
#    specs = {"PANDA"}
#
#    def __init__(self, filename):
#        self._name = filename
#
#    def __call__(self, field):
#        with h5py.File(self._name, "r") as f:
#            entry = f[f"/{field}"]
#            return entry[:]
#
#
#db.reg.register_handler("PANDA", PandAHandlerHDF5, overwrite=True)

def scan_and_fly_2dpd(detectors, xcenter, xrange, xnum, ystart, ystop, ynum, dwell, *,
                      panda_flyer, xmotor, ymotor, dead_time = 0,
                      delta=None, shutter=False, align=False, plot=False,
                      md=None, snake=False, verbose=False, wait_before_scan=None, position_supersample= 10):
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
    shutter : bool, optional, kwarg only
       If True, try to open the shutter
    """

    # t_setup = tic()

    # Check for negative number of points
    if xnum < 1 or ynum < 1:
        print('Error: Number of points is negative.')
        return

    num_total = int(xnum*ynum)

    # Set metadata
    if md is None:
        md = {}
    # md = get_stock_md(md)
    if wait_before_scan is None:
       wait_before_scan = short_uid('before_scan')

    # Assign detectors to flying_zebra, this may fail
    panda_flyer.detectors = detectors
    panda_flyer.position_supersample = position_supersample
    panda_flyer.frame_per_point = num_total * panda_flyer.position_supersample

    # Setup detectors, combine the zebra, sclr, and the just set detector list
    detectors = (panda_flyer.panda, panda_flyer.sclr) + panda_flyer.detectors
    detectors = [_ for _ in detectors if _ is not None]

    names_stage_once = ("merlin2", "eiger2", "eiger_mobile")

    # print(f"detectors_stage_once={detectors_stage_once}")
    # print(f"detectors_stage_every_row={detectors_stage_every_row}")

    dets_by_name = {d.name : d for d in detectors}

    panda_flyer.frame_per_point = num_total

    if verbose:
        print("Set up detectors")
        t_detset = tic()

    # Set up the merlin
    for det_name in ("merlin2", "eiger2", "eiger_mobile"):
        if det_name in dets_by_name:
            dpc = dets_by_name[det_name]

            if det_name == "merlin2":
                # # Settings for 'Trigger start rising' trigger mode of Merlin
                # acquire_period = 0.75 * dwell
                # acquire_time = 0.50 * dwell
                # acquire_time = min(acquire_time, acquire_period - 0.0016392)
                # if acquire_time <= 0:
                #     raise ValueError("Acquistion period is too small. Increase dwell time")

                # Settings for 'Trigger enable' mode
                acquire_time = 0.0001
                acquire_period = acquire_time
                # acquire_period = acquire_time + 0.0016392

            elif det_name == "eiger2":
                acquire_time = dwell - dead_time
                acquire_period = dwell
            elif det_name == "eiger_mobile":
                acquire_time = dwell - dead_time
                acquire_period = dwell
            else:
                raise ValueError(f"Unsupported detector: {det_name!r}")
            if verbose:
                toc(t_detset,'Dwell time set')

            if det_name == "eiger2":
                # Acquire one frame with the computed acquire time to avoid 'Invalid frame'
                #   errors in HDF5 plugin. This may be needed because Eiger is using
                #  'autosummation' for longer exposure times, which may result in different
                #  data representation for short and long exposures (just an assumption).
                #dpc.hdf5.warmup(acquire_time=acquire_time)
                pass

            if det_name == "eiger_mobile":
                # Acquire one frame with the computed acquire time to avoid 'Invalid frame'
                #   errors in HDF5 plugin. This may be needed because Eiger is using
                #  'autosummation' for longer exposure times, which may result in different
                #  data representation for short and long exposures (just an assumption).
                #dpc.hdf5.warmup(acquire_time=acquire_time)
                if acquire_time < 0.02:
                    image_bitdepth = 16
                else:
                    image_bitdepth = 32
                if 'UInt'+str(image_bitdepth) != dpc.hdf5.data_type.get():
                    print("Adjusting eiger output bitdepth")
                    dpc.cam.acquire.set(0)
                    dpc.hdf5.warmup(acquire_time)
                pass

                pass
            if verbose:
                toc(t_detset,'hdf5 warmup')

            dpc.stage_sigs[dpc.cam.acquire_time] = acquire_time
            dpc.stage_sigs[dpc.cam.acquire_period] = acquire_period
            #dpc.stage_sigs[dpc.cam.num_images] = num_total
            #dpc.stage_sigs[dpc.cam.wait_for_plugins] = 'No'
            dpc.stage_sigs['total_points'] = num_total
            dpc.hdf5.stage_sigs['num_capture'] = num_total
            dpc.hdf5.frame_per_point = num_total
            del dpc

    if verbose:
        toc(t_detset,'Detectors initialized')
    print('[Panda]Detectors initialized')

    export_scan_header(hxntools.scans.get_last_scan_id()+1,xmotor,xrange,xnum,ymotor,np.abs(ystop-ystart),ynum,\
            [d for d in detectors if d.name.startswith('eiger')][0])

    # If delta is None, set delta based on time for acceleration
    if delta is None:
        # MIN_DELTA = 0.5  # old default value
        # v = (ystop - ystart) / num_total / dwell  # compute "stage speed"
        # t_acc = 0.5
        # # t_acc = xmotor.acceleration.get()  # acceleration time
        # delta = t_acc * v  # distance the stage will travel in t_acc
        # # delta = np.amax((delta, MIN_DELTA))
        # delta = min(0.5, delta + 0.1)
        delta = 1
    delta = delta * np.sign(ystop - ystart)


    scan_start, scan_stop = ystart, ystop

    # row_start, row_stop = xstart - 0.3, xstop + 0.3

    # Run a peakup before the map?
    if (align):
        yield from peakup_fine(shutter=shutter)

    # This is added for consistency with existing HXN plans. Requires custom
    #   setup of RE:   hxntools.scans.setup(RE=RE)

    yield Msg('hxn_next_scan_id')

    if "scan" not in md:
        md["scan"] = {}
    # Scan metadata
    md['motors'] = [xmotor.name, ymotor.name]
    md['motor1'] = xmotor.name
    md['motor2'] = ymotor.name
    md['scan']['type'] = 'FIP_2D_FLY'
    md['scan']['scan_input'] = [float(xcenter),float(xrange),xnum,ystart,ystop,ynum,dwell]
    md['scan']['sample_name'] = ''
    try:
        md['scan']['theta'] = pt_tomo.th.position
        md['scan']['picoy'] = pt_tomo.p1_pos1.get()/1e6
    except:
        pass
    md['scan']['detectors'] = [d.name for d in detectors]
    md['scan']['detector_distance'] = 1.00
    md['scan']['dwell'] = dwell
    md['scan']['fast_axis'] = {'motor_name' : xmotor.name,
                               'units' : xmotor.motor_egu.get()}
    md['scan']['slow_axis'] = {'motor_name' : ymotor.name,
                               'units' : ymotor.motor_egu.get()}
    md['scan']['theta'] = {'val' : pt_tomo.th.user_readback.get(),
                           'units' : pt_tomo.th.motor_egu.get()}
    md['scan']['delta'] = {'val' : delta,
                           'units' : ymotor.motor_egu.get()}
    md['scan']['snake'] = snake
    md['scan']['shape'] = (xnum, ynum)
    md['shape'] = (xnum, ynum)

    time_start_scan = time.time()

    # Synchronize encoders
    # flying_zebra._encoder.pc.enc_pos1_sync.put(1)
    # flying_zebra._encoder.pc.enc_pos2_sync.put(1)
    # flying_zebra._encoder.pc.enc_pos3_sync.put(1)

    # # Somewhere sync_todo
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos1_sync, 1)
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos2_sync, 1)
    # yield from bps.mv(flying_zebra_2d._encoder.pc.enc_pos3_sync, 1)
    # yield from bps.sleep(1)

    yield from bps.mov(ymotor.velocity,5)

    # Select PV for monitoring
    d_names = [_.name for _ in detectors]
    #ts_monitor_dec = ts_monitor_during_decorator
    #if "merlin2" in d_names:
    #    roi_pv = merlin2.stats1.ts_total
    #    roi_pv_force_update = merlin2.stats1.ts.ts_read_proc
    #elif "eiger2" in d_names:
    #    roi_pv = eiger2.stats1.ts_total
    #    roi_pv_force_update = eiger2.stats1.ts.ts_read_proc
    #elif "eiger_mobile" in d_names:
    #    roi_pv = eiger_mobile.stats1.ts_total
    #    roi_pv_force_update = eiger_mobile.stats1.ts.ts_read_proc
    #else:
    roi_pv = None
    roi_pv_force_update = None
    ts_monitor_dec = ts_monitor_during_decorator_disabled

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
        if d.name == 'eiger2' or d.name == 'eiger_mobile':
            yield from bps.mov(d.fly_next, True)
            yield from bps.mov(d.internal_trigger, True)
    #@subs_decorator(livepopup)
    @subs_decorator({'start': at_scan})
    @subs_decorator({'stop': finalize_scan})
    @ts_monitor_dec([roi_pv])
    # @monitor_during_decorator([xs.channel1.rois.roi01.value])  ## Uncomment this
    # @monitor_during_decorator([xs.channel1.rois.roi01.value, xs.array_counter])
    @stage_decorator([panda_flyer])  # Below, 'scan' stage ymotor.
    @stage_decorator(panda_flyer.detectors)
    @run_decorator(md=md)
    def plan():
        if verbose:
            print("Starting the plan ...")
            print(f"flying_zebra.detectors={panda_flyer.detectors}")

        # print(f"Plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
        # print(f"Plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")

        # TODO move this to stage sigs
        for d in panda_flyer.detectors:
            if d.name == "eiger2" or d.name == "eiger_mobile":
                yield from bps.mov(d.total_points, num_total)

        ystep = 0
        print(f"Scanning 2D fly")
        # yield from bps.sleep(10)

        direction = np.sign(scan_stop - scan_start)
        start = scan_start
        stop = scan_stop


        if verbose:
            print(f'Direction = {direction}')
            print(f'Start = {start}')
            print(f'Stop  = {stop}')
        v = (np.abs(scan_stop - scan_start) / num_total) / dwell  # compute "stage speed"


        def move_to_start_fly():
            "See http://nsls-ii.github.io/bluesky/plans.html#the-per-step-hook"

            # print(f"Start moving to beginning of the row")
            row_mv_to_start = short_uid('row')
            yield from bps.checkpoint()
            yield from bps.abs_set(ymotor, scan_start-delta/2.0*v, group=wait_before_scan)
            # yield from bps.trigger_and_read([temp_nanoKB, motor])  ## Uncomment this
            # print(f"Finished moving to the beginning of the row")
            # print(f"Fast axis: {xmotor.read()} Slow axis: {motor.read()}")

        if verbose:
            t_startfly = tic()
            toc(t_startfly, "TIMER (STEP) - STARTING TIMER")

        yield from move_to_start_fly()

        if verbose:
            toc(t_startfly, "TIMER (STEP) - MOTOR IS MOVED TO STARTING POINT")

        # x_set = row_start
        # x_dial = xmotor.user_readbac k.get()

        # Get retry deadband value and check against that
        # i = 0
        # DEADBAND = 0.050  # retry deadband of nPoint scanner
        # while (np.abs(x_set - x_dial) > DEADBAND):
        #     if (i == 0):
        #         print('Waiting for motor to reach starting position...',
        #               end='', flush=True)
        #     i = i + 1
        #     yield from mv(xmotor, row_start)
        #     yield from bps.sleep(0.1)
        #     x_dial = xmotor.user_readback.get()
        # if (i != 0):
        #     print('done')

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - MOTOR POSITION IS CHECKED')

        # Set the scan speed
        if verbose:
            print(f"FORWARD SPEED FOR SCAN AXIS: {v} (num={num_total} dwell={dwell})")
        if v<5:
            yield from mv(ymotor.velocity, v)
        else:
            raise RuntimeError(f"Ymotor speed too fast, check your input")

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - FORWARD VELOCITY IS SET')

        # set up all of the detectors
        # TODO we should be able to move this out of the per-line call?!
        # if ('xs' in dets_by_name):
        #     xs = dets_by_name['xs']
        #     yield from abs_set(xs.hdf5.num_capture, xnum, group='set')
        #     yield from abs_set(xs.settings.num_images, xnum, group='set')
        #     yield from bps.wait(group='set')
        #     # yield from mv(xs.hdf5.num_capture, xnum,
        #     #               xs.settings.num_images, xnum)
        #     # xs.hdf5.num_capture.put(xnum)
        #     # xs.settings.num_images.put(xnum)

        # if ('xs2' in dets_by_name):
        #     xs2 = dets_by_name['xs2']
        #     # yield from abs_set(xs2.hdf5.num_capture, xnum, wait=True)
        #     # yield from abs_set(xs2.settings.num_images, xnum, wait=True)
        #     yield from mv(xs2.hdf5.num_capture, xnum,
        #                   xs2.settings.num_images, xnum)

        # # Merlin code from the original SRX plan
        if "merlin2" in dets_by_name:
            # print(f"Configuring 'merlin2' ...")
            dpc = dets_by_name["merlin2"]
            yield from abs_set(dpc.cam.num_images, num_total, wait=True)
        if "eiger2" in dets_by_name:
            # print(f"Configuring 'eiger2' ...")
            dpc = dets_by_name["eiger2"]
            yield from abs_set(dpc.cam.num_triggers, 1, wait=True)
            yield from abs_set(dpc.cam.num_images, num_total, wait=True)
            yield from abs_set(dpc.cam.wait_for_plugins, 'No', wait=True)
        if "eiger_mobile" in dets_by_name:
            # print(f"Configuring 'eiger_mobile' ...")
            dpc = dets_by_name["eiger_mobile"]
            yield from abs_set(dpc.cam.num_triggers, 1, group=wait_before_scan)
            yield from abs_set(dpc.cam.num_images, num_total, group=wait_before_scan)
            yield from abs_set(dpc.cam.wait_for_plugins, 'No', group=wait_before_scan)

        ion = panda_flyer.sclr
        if ion:
            yield from abs_set(ion.nuse_all, num_total, wait=True)
            #yield from abs_set(ion.nuse_all, 2*xnum, wait=True)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - DETECTORS ARE CONFIGURED')

        def panda_kickoff():
            # start_zebra, stop_zebra = xstart * 1000000, xstop * 1000000
            start_zebra, stop_zebra = scan_start, scan_stop
            yield from kickoff(panda_flyer,
                                num=num_total*panda_flyer.position_supersample,
                                wait=True)
        yield from panda_kickoff()

        # panda_h5_path = os.path.realpath(os.path.join(panda_flyer.panda.data.hdf_directory.get(),panda_flyer.panda.data.hdf_file_name.get()))
        # panda_h5_link = '/nsls2/data2/hxn/legacy/users/startup_parameters/panda_data.h5'

        # try:
        #     if os.path.exists(panda_h5_link):
        #         os.remove(panda_h5_link)

        #     os.symlink(panda_h5_path,panda_h5_link)
        # except:
        #     pass

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

        # start the 'fly'
        def print_watch(*args, **kwargs):
            with open('~/bluesky_output.txt', 'a') as f:
                f.write(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f\n'))
                # print(args)
                f.write(json.dumps(kwargs))
                f.write('\n')
        yield from bps.wait(group=wait_before_scan)


        # Start Scan!

        st = yield from abs_set(ymotor, scan_stop+delta/2.0*v,group=row_scan)
        if verbose:
            st.add_callback(lambda x: toc(t_startfly, str=f"  MOTOR  {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')}"))

        yield from bps.sleep(np.abs(delta/2))
        for d in panda_flyer.detectors:
            print(f'  triggering {d.name}')
            st = yield from bps.trigger(d)
            st.add_callback(lambda x: toc(t_startfly, str=f"  DETECTOR  {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')}"))

        # st = yield from abs_set(xmotor, row_stop)
        # st.watch(print_watch)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - MOTOR STARTED')

        # print("Waiting for motor to stop")
        # st.wait()
        # if verbose:
        #     toc(t_startfly, str='Total time: Motor stopped')

        # wait for the motor and detectors to all agree they are done
        if verbose:
            print("Waiting for the row scan to complete ...")
        yield from bps.wait(group=row_scan)
        if verbose:
            print("Row scan is completed")
        counter = 0
        while dpc.cam.num_images_counter.get()<num_total:
            counter +=0.5
            print("Eiger processing not finished, waiting")
            yield from bps.sleep(0.5)
            if counter>3:
                break
        yield from abs_set(dpc._acquisition_signal,0,wait=True)

        # yield from bps.sleep(1)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - MOTOR STOPPED. ACQUISITION_COMPLETED.')

        # we still know about ion from above
        if ion:
            yield from abs_set(ion.stop_all, 1)  # stop acquiring scaler

        # print(f"Resetting scanner velocity")
        # set speed back
        yield from bps.mov(ymotor.velocity,5)
        # print(f"Completed resetting scanner velocity")

        # @timer_wrapper
        def panda_complete():
            yield from complete(panda_flyer)  # tell the Zebra we are done
        if verbose:
            t_pdcomplete = tic()
        yield from panda_complete()
        if verbose:
            toc(t_pdcomplete, str='Panda complete')

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - ZEBRA ACQUISITION COMPLETED.')

        # @timer_wrapper
        def panda_collect():
            yield from collect(panda_flyer)  # extract data from Zebra
        if verbose:
            t_pdcollect = tic()
        yield from panda_collect()
        if verbose:
            toc(t_pdcollect, str='Zebra collect')

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - ZEBRA COLLECTION COMPLETED.')

        # Force update of the respective PV so that all collected monitoring data for the row
        #   is loaded before the plugin is reset. Otherwise data in monitoring stream will not
        #   contain last points of rows.
        #if roi_pv_force_update:
        #    yield from bps.mv(roi_pv_force_update, 1)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - STEP COMPLETED.')

        if verbose:
            print(f"Step is completed")

    # Setup the final scan plan
    if shutter:
        final_plan = finalize_wrapper(plan(), check_shutters(shutter, 'Close'))
    else:
        final_plan = plan()

    # Open the shutter
    if verbose:
        t_open = tic()
    # yield from check_shutters(shutter, 'Open')  ## Uncomment this
    if verbose:
        toc(t_open, str='Open shutter (dt)')

    # print(f"Before plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
    # print(f"Before plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")

    # Run the scan
    uid = yield from final_plan

    print(f"SCAN TOTAL TIME: {time.time() - time_start_scan}")

    return uid


def pt_fly2dcontpd(dets, motor1, scan_start1, scan_end1, num1, motor2, scan_start2, scan_end2, num2, exposure_time, pos_return = True, apply_tomo_drift = False, tomo_angle = None, auto_rescan = False,position_supersample= 10, **kwargs):
    """
    Relative scan
    """
    do_scan = True
    while do_scan:
        m1_pos = motor1.position
        m2_pos = motor2.position
        print(f"Initial positions: m1_pos={m1_pos}  m2_pos={m2_pos}")
        do_scan = False
        try:
            center1, range1 =(scan_start1+scan_end1)/2, np.abs(scan_end1-scan_start1)
            if apply_tomo_drift:
               # if tomo_angle is None:
               #     tomo_angle = pt_tomo.th.user_setpoint.get()
               # center1 = center1 + get_tomo_drift(tomo_angle)
               # ydrift_tomo = get_tomo_drift_y(tomo_angle)
               tomo_angle = pt_tomo.th.user_setpoint.get()
               print("drift %.2f"%((rasmi_x_ref() - get_tomo_ref(tomo_angle))*0.6))
               center1 = center1 + (rasmi_x_ref() - get_tomo_ref(tomo_angle))*0.6
               ydrift_tomo = 0
            else:
               ydrift_tomo = 0
            start2, end2 = m2_pos + scan_start2 + ydrift_tomo, m2_pos + scan_end2 + ydrift_tomo
            range_min, range_max = -30, 30
            for v in [center1-range1/2, center1+range1/2, start2, end2]:
                if v < range_min or v > range_max:
                    raise ValueError(
                        f"Scan range exceed limits for the motors: "
                        f"start1={scan_start1} end1={scan_end1} start2={scan_start2} end2={scan_end2}"
                    )

            # RE(pt_fly2d([eiger2], pt_tomo.ssx, -10, 10, 101, pt_tomo.ssy, -1, 1, 5, 0.01, plot=True))
            kwargs.setdefault('xmotor', motor1)  # Fast motor
            kwargs.setdefault('ymotor', motor2)  # Slow motor
            kwargs.setdefault('panda_flyer', panda_flyer_fip)

            fg_volt = range1/6.0
            fg_offset = -center1/6.0
            fg_freq = 1/(2.0*num1*exposure_time)

            if fg_volt < 5 and fg_offset < 1 and fg_freq < 10:
                yield from abs_set(pt_fg.func,"RAMP")
                yield from abs_set(pt_fg.volt,f"{fg_volt:.{4}f}")
                yield from abs_set(pt_fg.offset,f"{fg_offset:.{4}f}")
                yield from abs_set(pt_fg.freq,f"{fg_freq:.{4}f}")
                yield from pt_fg.on()
            else:
                raise RuntimeError(f"Xmotor voltage or frequency too high, check your input")

            if exposure_time < 1:
                dead_time = 3.8e-6
            else:
                dead_time = np.maximum(0.001,exposure_time * 0.1)

            yield from bps.abs_set(panda1.pulse1.width,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda1.pulse1.width_units,'s')
            yield from bps.abs_set(panda1.pulse1.step,(exposure_time-dead_time)/position_supersample)
            yield from bps.abs_set(panda1.pulse1.step_units,'s')
            yield from bps.abs_set(panda1.pulse1.delay,(exposure_time-dead_time)/2.0/position_supersample)
            yield from bps.abs_set(panda1.pulse1.delay_units,'s')
            yield from bps.abs_set(panda1.pulse1.pulses,position_supersample)

            yield from bps.abs_set(panda1.pulse2.width_units,'s')
            yield from bps.abs_set(panda1.pulse2.width,exposure_time-dead_time)

            yield from bps.abs_set(panda1.pulse2.delay,0.0016)
            yield from bps.abs_set(panda1.pulse2.delay_units,'s')
            yield from bps.abs_set(panda1.pulse2.pulses,1)


            yield from scan_and_fly_2dpd(dets, center1, range1, num1, start2, end2, num2, exposure_time, dead_time = dead_time, position_supersample = position_supersample, **kwargs)

            if auto_rescan and eiger_mobile.cam.num_images_counter.get() < (num1*num2):
                do_scan = True

        finally:
            yield from pt_fg.off()
            if not pos_return and apply_tomo_drift:
                yield from bps.movr(motor2,-ydrift_tomo)
            if pos_return or do_scan:
                mv_back = short_uid('back')
                yield from bps.mov(motor2.velocity,5)
                yield from bps.mov(motor1.velocity,5)
                yield from abs_set(motor1,m1_pos,group=mv_back)
                yield from abs_set(motor2,m2_pos,group=mv_back)
                yield from bps.wait(group=mv_back)
