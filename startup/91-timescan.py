print(f"Loading {__file__!r} ...")
from collections import OrderedDict

from epics import caput, caget
import os
import threading
import h5py
from ophyd.sim import NullStatus
import numpy as np
import time as ttime
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt
from bluesky.plan_stubs import (kickoff, collect,
                                complete, abs_set, mv, checkpoint)
from hxntools.detectors.zebra import Zebra, EpicsSignalWithRBV
from hxntools.handlers.rasmi2 import SISHDF5Handler
from databroker.assets.handlers import HandlerBase
from ophyd.areadetector.filestore_mixins import resource_factory
from bluesky.preprocessors import (stage_decorator,
                                   run_decorator, subs_decorator,
                                   monitor_during_decorator, finalize_wrapper)


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

class ExportSISDataTime:
    def __init__(self):
        self._fp = None
        self._filepath = None

    def open(self, filepath, mca_names, ion):
        self.close()
        self._filepath = filepath
        self._fp = h5py.File(filepath, "w", libver="latest")

        self._fp.swmr_mode = True

        self._ion = ion
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

        correct_length = len(mca)

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

        def add_data(ds_name, data):
            ds = self._fp[ds_name]
            n_ds = ds.shape[0]
            ds.resize((n_ds + len(data),))
            ds[n_ds:] = np.array(data)

        for n, name in enumerate(self._mca_names):
            add_data(name, np.asarray(mca_data[n]))

        self._fp.flush()

class HXNTimeScan(Device):

    LARGE_FILE_DIRECTORY_WRITE_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_READ_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_ROOT = LARGE_FILE_DIRECTORY_ROOT

    KNOWN_DETS = {"eiger_mobile"}

    @property
    def detectors(self):
        return tuple(self._dets)

    @detectors.setter
    def detectors(self, value):
        dets = tuple(value)
        if not all(d.name in self.KNOWN_DETS for d in dets):
            raise ValueError(
                f"One or more of {[d.name for d in dets]}"
                f"is not known to the zebra. "
                f"The known detectors are {self.KNOWN_DETS})"
            )
        self._dets = dets

    @property
    def sclr(self):
        return self._sis

    def __init__(self,dets,sclr, motor=None, root_dir=None, **kwargs):
        super().__init__("", parent=None, **kwargs)
        self.name = "TimeFlyer"
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

        self.motor = motor

        self._document_cache = []
        self._resource_document = None
        self._datum_factory = None

        if self._sis is not None:
            self._data_sis_exporter = ExportSISDataTime()

        type_map = {"int32": "<i4", "float32": "<f4", "float64": "<f8"}

    def stage(self):
        super().stage()

    def unstage(self):
        self._point_counter = None
        if self._sis is not None:
            self._data_sis_exporter.close()
        super().unstage()

    def kickoff(self, *, num, dwell):
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

        if self._sis is not None:
            # Put SIS3820 into single count (not autocount) mode
            self.stage_sigs[self._sis.count_mode] = 0
            self.stage_sigs[self._sis.count_on_start] = 1
            # Stop the SIS3820
            self._sis.stop_all.put(1)

        self.__filename_sis = "{}.h5".format(uuid.uuid4())
        print(self.__filename_sis)
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
        if self._sis:
            resources.append(self.__filestore_resource_sis)
        self._document_cache.extend(("resource", _) for _ in resources)

        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            self._data_sis_exporter.open(
                self.__write_filepath_sis, mca_names=sis_mca_names, ion=self._sis
            )

        return NullStatus()

    def complete(self):
        for d in self._dets:
            d.stop(success=True)


        if self._sis:
            sis_mca_names = self._sis_mca_names()
            sis_datum = []
            for name in sis_mca_names:
                sis_datum.append(self._datum_factory_sis({"column": name, "point_number": self._point_counter}))


        if self._sis:
            self._document_cache.extend(("datum", d) for d in sis_datum)

        for d in self._dets:
            if d.name != "fs":
                self._document_cache.extend(d.collect_asset_docs())

        # @timer_wrapper
        def get_sis_data():
            if self._sis is None:
                return
            self._data_sis_exporter.export()

        get_sis_data()

        data_dict = {
            key: datum_doc["datum_id"] for key, datum_doc in self._datum_docs.items()
        }

        now = ttime.time()  # TODO: figure out how to get it from PandABox (maybe?)
        self._last_bulk = {
            "data": data_dict,
            "timestamps": {key: now for key in self._datum_docs},
            "time": now,
            "filled": {key: False for key in self._datum_docs},
        }

        if self._sis:
            self._last_bulk["data"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})
            self._last_bulk["timestamps"].update({k: v["datum_id"] for k, v in zip(sis_mca_names, sis_datum)})

        for d in self._dets:
            reading = d.read()
            self._last_bulk["data"].update(
                {k: v["value"] for k, v in reading.items()}
                )
            self._last_bulk["timestamps"].update(
                {k: v["timestamp"] for k, v in reading.items()}
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

        for d in self._dets:
            desc.update(d.describe())

        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            for n, name in enumerate(sis_mca_names):
                desc[name] = spec
                desc[name]["source"] = self._sis.mca_by_index[n + 1].spectrum.pvname

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

time_flyer = HXNTimeScan([],sclr1,name="TimeFlyer")

def time_scan(detectors, num, dwell, *,
                      flyer, delta=None, shutter=False, align=False, plot=False,
                      md=None, snake=False, verbose=False, wait_before_scan=None):
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
    if num < 1:
        print('Error: Number of points is negative.')
        return

    num_total = int(num)

    # Set metadata
    if md is None:
        md = {}
    # md = get_stock_md(md)
    if wait_before_scan is None:
       wait_before_scan = short_uid('before_scan')

    # Assign detectors to flying_zebra, this may fail
    flyer.detectors = detectors
    # Setup detectors, combine the zebra, sclr, and the just set detector list
    detectors = (flyer.sclr,) + flyer.detectors
    detectors = [_ for _ in detectors if _ is not None]

    names_stage_once = ("merlin2", "eiger2", "eiger_mobile")

    # print(f"detectors_stage_once={detectors_stage_once}")
    # print(f"detectors_stage_every_row={detectors_stage_every_row}")

    dets_by_name = {d.name : d for d in detectors}

    flyer.frame_per_point = num_total

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
                acquire_time = dwell
                acquire_period = dwell
            elif det_name == "eiger_mobile":
                acquire_time = dwell
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
                dpc.hdf5.warmup(acquire_time=acquire_time)
                # pass

            if det_name == "eiger_mobile":
                # Acquire one frame with the computed acquire time to avoid 'Invalid frame'
                #   errors in HDF5 plugin. This may be needed because Eiger is using
                #  'autosummation' for longer exposure times, which may result in different
                #  data representation for short and long exposures (just an assumption).
                #dpc.hdf5.warmup(acquire_time=acquire_time)
                pass
            if verbose:
                toc(t_detset,'hdf5 warmup')

            if det_name != 'fs':
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
    print('[TimeScan]Detectors initialized')

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
    md['scan']['type'] = 'TIME_SCAN'
    md['scan']['scan_input'] = [num,dwell]
    md['scan']['sample_name'] = ''
    md['scan']['detectors'] = [d.name for d in detectors]
    md['scan']['detector_distance'] = 2.05
    md['scan']['dwell'] = dwell
    # md['scan']['theta'] = {'val' : pt_tomo.th.user_readback.get(),
    #                        'units' : pt_tomo.th.motor_egu.get()}
    md['scan']['shape'] = (num)

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

    # Select PV for monitoring
    d_names = [_.name for _ in detectors]
    if "merlin2" in d_names:
        roi_pv = merlin2.stats1.ts_total
        roi_pv_force_update = merlin2.stats1.ts.ts_read_proc
    #elif "eiger2" in d_names:
    #    roi_pv = eiger2.stats1.ts_total
    #    roi_pv_force_update = eiger2.stats1.ts.ts_read_proc
    #elif "eiger_mobile" in d_names:
    #    roi_pv = eiger_mobile.stats1.ts_total
    #    roi_pv_force_update = eiger_mobile.stats1.ts.ts_read_proc
    else:
        roi_pv = None
        roi_pv_force_update = None

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

    for d in flyer.detectors:
        if d.name == "eiger2":
            yield from bps.mov(d.fly_next, True)
            yield from bps.mov(d.internal_trigger, True)

    #@subs_decorator(livepopup)
    @subs_decorator({'start': at_scan})
    @subs_decorator({'stop': finalize_scan})
    # @monitor_during_decorator([xs.channel1.rois.roi01.value])  ## Uncomment this
    # @monitor_during_decorator([xs.channel1.rois.roi01.value, xs.array_counter])
    @stage_decorator([flyer])  # Below, 'scan' stage ymotor.
    @stage_decorator(flyer.detectors)
    @run_decorator(md=md)
    def plan():
        if verbose:
            print("Starting the plan ...")
            print(f"flying_zebra.detectors={flyer.detectors}")

        # print(f"Plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
        # print(f"Plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")

        # TODO move this to stage sigs
        for d in flyer.detectors:
            if d.name != "merlin2" and d.name!="fs":
                yield from bps.mov(d.total_points, num_total)

        ystep = 0
        print(f"Scanning 2D fly")
        # yield from bps.sleep(10)

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

        # set up all of the detectors
        # TODO we should be able to move this out of the per-line call?!
        # if ('xs' in dets_by_name):
        #     xs = dets_by_name['xs']
        #     yield from bps.abs_set(xs.hdf5.num_capture, xnum, group='set')
        #     yield from bps.abs_set(xs.settings.num_images, xnum, group='set')
        #     yield from bps.wait(group='set')
        #     # yield from mv(xs.hdf5.num_capture, xnum,
        #     #               xs.settings.num_images, xnum)
        #     # xs.hdf5.num_capture.put(xnum)
        #     # xs.settings.num_images.put(xnum)

        # if ('xs2' in dets_by_name):
        #     xs2 = dets_by_name['xs2']
        #     # yield from bps.abs_set(xs2.hdf5.num_capture, xnum, wait=True)
        #     # yield from bps.abs_set(xs2.settings.num_images, xnum, wait=True)
        #     yield from mv(xs2.hdf5.num_capture, xnum,
        #                   xs2.settings.num_images, xnum)

        # # Merlin code from the original SRX plan
        if "merlin2" in dets_by_name:
            # print(f"Configuring 'merlin2' ...")
            dpc = dets_by_name["merlin2"]
            yield from bps.abs_set(dpc.cam.num_images, num_total, wait=True)
        if "eiger2" in dets_by_name:
            # print(f"Configuring 'eiger2' ...")
            dpc = dets_by_name["eiger2"]
            yield from bps.abs_set(dpc.cam.num_triggers, 1, wait=True)
            yield from bps.abs_set(dpc.cam.num_images, num_total, wait=True)
            yield from bps.abs_set(dpc.cam.wait_for_plugins, 'No', wait=True)
        if "eiger_mobile" in dets_by_name:
            # print(f"Configuring 'eiger_mobile' ...")
            dpc = dets_by_name["eiger_mobile"]
            yield from bps.abs_set(dpc.cam.num_triggers, 1, group=wait_before_scan)
            yield from bps.abs_set(dpc.cam.num_images, num_total, group=wait_before_scan)
            yield from bps.abs_set(dpc.cam.wait_for_plugins, 'No', group=wait_before_scan)

        ion = flyer.sclr
        if ion:
            yield from bps.abs_set(ion.nuse_all, num_total, wait=True)
            yield from abs_set(ion.input_mode, 2, wait=True)
            #yield from bps.abs_set(ion.nuse_all, 2*xnum, wait=True)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - DETECTORS ARE CONFIGURED')

        def time_kickoff():
            # start_zebra, stop_zebra = xstart * 1000000, xstop * 1000000
            yield from kickoff(flyer,
                                num=num_total, dwell=dwell,wait=True
            )
        print('[TimeScan]Kickoff')
        yield from time_kickoff()

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - PANDA STARTED')

        # arm SIS3820, note that there is a 1 sec delay in setting X
        # into motion so the first point *in each row* won't
        # normalize...
        if ion:
            yield from bps.abs_set(ion.erase_start, 1)
            if verbose:
                toc(t_startfly, str='TIMER (STEP) - SCALAR STARTED')


        row_scan = short_uid('row')
        if verbose:
            print('Data collection:')

        #if roi_pv_force_update:
        #    yield from bps.mv(roi_pv_force_update, 1)


        # start the 'fly'

        for d in flyer.detectors:
            print(f'  triggering {d.name}')
            st = yield from bps.trigger(d)

        # st = yield from bps.abs_set(xmotor, row_stop)
        # st.watch(print_watch)


        # print("Waiting for motor to stop")
        # st.wait()
        # if verbose:
        #     toc(t_startfly, str='Total time: Motor stopped')

        # wait for the motor and detectors to all agree they are done
        exp_count = dpc.cam.num_images_counter.get()
        while exp_count<num_total:
            yield from bps.sleep(1)
            print('Exposure %6d/%d'%(exp_count,num_total))
            exp_count = dpc.cam.num_images_counter.get()
        yield from bps.abs_set(dpc._acquisition_signal,0,wait=True)

        # yield from bps.sleep(1)


        # we still know about ion from above
        if ion:
            yield from bps.abs_set(ion.stop_all, 1)  # stop acquiring scaler

        # print(f"Resetting scanner velocity")
        # set speed back
        # print(f"Completed resetting scanner velocity")

        # @timer_wrapper
        def time_complete():
            yield from complete(flyer)  # tell the Zebra we are done
        yield from time_complete()


        # @timer_wrapper
        def time_collect():
            yield from collect(flyer)  # extract data from Zebra
        yield from time_collect()

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


def pt_timescan(dets, num, exposure_time,auto_rescan = False, **kwargs):
    """
    Relative scan
    """
    do_scan = True
    while do_scan:
        do_scan = False
        try:
            zebra.output[2].ttl.addr.put(4)
            zebra.output[3].ttl.addr.put(4)
            kwargs.setdefault('flyer', time_flyer)

            #args = [center1, range1, num1, scan_start2, scan_end2, num2, exposure_time]

            # print(kwargs['xmotor'].name)
            # print(kwargs['ymotor'].name)
            # print(kwargs['flying_zebra'].name)

            #if motor1 == pt_tomo.ssx and motor2 == pt_tomo.ssy:
            # elif motor1 == pt_tomo.ssy and motor2 == pt_tomo.ssx:
            #     yield from bps.abs_set(nano_flying_zebra.fast_axis, 'NANO2D')
            #     yield from bps.abs_set(nano_flying_zebra.slow_axis, 'NANO2D')
            #else:
            #    raise RuntimeError(f"Unsupported set of motors: motor1={motor1} motor2={motor2}")

            #yield from bps.abs_set(motor1,center1,wait=True)
            #yield from bps.stage(motor1)
            #yield from bps.unstage(motor1)


            # _xs = kwargs.pop('xs', xs)
            # if extra_dets is None:
            #     extra_dets = []
            # dets = [] if  _xs is None else [_xs]
            # dets = dets + extra_dets
            # print(f"dets={dets}")
            # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
            # yield from bps.sleep(2)
            yield from time_scan(dets, num, exposure_time, **kwargs)
            if auto_rescan and dets[0].cam.num_images_counter.get()<num:
                do_scan = True
                print('Eiger has missing trigger, will rescan..')
            else:
                print('Scan finished.')
            # yield from bps.sleep(1)
            #yield from set_scanner_velocity(5)
        finally:
            pass
