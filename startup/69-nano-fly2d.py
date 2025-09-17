if not USE_RASMI:
    print(f"RASMI not used, skipping {__file__!r} ...")
    import sys
    sys.exit()

print(f"Loading {__file__!r} ...")

import bluesky.suspenders as sps
# changed the flyer device to be aware of fast vs slow axis in a 2D scan
# should abstract this method to use fast and slow axes, rather than x and y
def scan_and_fly_2d(detectors, xcenter, xrange, xnum, ystart, ystop, ynum, dwell, *,
                      flying_zebra_2d, xmotor, ymotor,
                      delta=None, pulse_dur = 0.8, shutter=False, align=False, plot=False,
                      md=None, snake=False, verbose=False):
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

    # Assign detectors to flying_zebra, this may fail
    flying_zebra_2d.detectors = detectors
    # Setup detectors, combine the zebra, sclr, and the just set detector list
    detectors = (flying_zebra_2d.encoder, flying_zebra_2d.sclr) + flying_zebra_2d.detectors
    detectors = [_ for _ in detectors if _ is not None]

    names_stage_once = ("merlin2", "eiger2", "eiger_mobile")
    detectors_stage_once = [_ for _ in flying_zebra_2d.detectors if _.name in names_stage_once]
    detectors_stage_every_row = [_ for _ in flying_zebra_2d.detectors if _.name not in names_stage_once]

    # print(f"detectors_stage_once={detectors_stage_once}")
    # print(f"detectors_stage_every_row={detectors_stage_every_row}")

    dets_by_name = {d.name : d for d in detectors}

    flying_zebra_2d.frame_per_point = num_total

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
                acquire_time = 0.9 * dwell
                acquire_period = acquire_time
            elif det_name == "eiger_mobile":
                acquire_time = pulse_dur * dwell
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

            dpc.cam.stage_sigs['acquire_time'] = acquire_time
            dpc.cam.stage_sigs['acquire_period'] = acquire_period
            dpc.cam.stage_sigs['num_images'] = 1
            dpc.cam.stage_sigs['wait_for_plugins'] = 'No'
            dpc.stage_sigs['total_points'] = num_total
            dpc.hdf5.stage_sigs['num_capture'] = num_total
            dpc.hdf5.frame_per_point = num_total
            del dpc

    if verbose:
        toc(t_detset,'Detectors initialized')

    # If delta is None, set delta based on time for acceleration
    if delta is None:
        # MIN_DELTA = 0.5  # old default value
        # v = (ystop - ystart) / num_total / dwell  # compute "stage speed"
        # t_acc = 0.5
        # # t_acc = xmotor.acceleration.get()  # acceleration time
        # delta = t_acc * v  # distance the stage will travel in t_acc
        # # delta = np.amax((delta, MIN_DELTA))
        # delta = min(0.5, delta + 0.1)
        delta = 0.1
    delta = delta * np.sign(ystop - ystart)


    scan_start, scan_stop = ystart, ystop

    # row_start, row_stop = xstart - 0.3, xstop + 0.3

    # Run a peakup before the map?
    if (align):
        yield from peakup_fine(shutter=shutter)

    # This is added for consistency with existing HXN plans. Requires custom
    #   setup of RE:   hxntools.scans.setup(RE=RE)
    if not FIP_TESTING:
        yield Msg('hxn_next_scan_id')

    yield from bps.pause()
    if "scan" not in md:
        md["scan"] = {}
    # Scan metadata
    md['scan']['type'] = 'FIP_2D_FLY'
    md['scan']['scan_input'] = [float(xcenter),float(xrange),xnum,ystart,ystop,ynum,dwell]
    md['scan']['sample_name'] = ''
    try:
        md['scan']['theta'] = pt_tomo.th.position
        md['scan']['picoy'] = pt_tomo.p1_pos1.get()/1e6
    except:
        pass
    md['scan']['detectors'] = [d.name for d in detectors]
    md['scan']['detector_distance'] = 1.055
    md['scan']['dwell'] = dwell
    md['scan']['fast_axis'] = {'motor_name' : xmotor.name,
                               'units' : xmotor.motor_egu.get()}
    md['scan']['slow_axis'] = {'motor_name' : ymotor.name,
                               'units' : ymotor.motor_egu.get()}
    # md['scan']['theta'] = {'val' : pt_tomo.th.user_readback.get(),
    #                        'units' : pt_tomo.th.motor_egu.get()}
    md['scan']['delta'] = {'val' : delta,
                           'units' : xmotor.motor_egu.get()}
    md['scan']['pulse_dur'] = pulse_dur
    md['scan']['snake'] = snake
    md['scan']['shape'] = (xnum, ynum)

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

    yield from set_scanner_velocity(5)

    # Select PV for monitoring
    d_names = [_.name for _ in detectors_stage_once]
    ts_monitor_dec = ts_monitor_during_decorator
    if "merlin2" in d_names:
        roi_pv = merlin2.stats1.ts_total
        roi_pv_force_update = merlin2.stats1.ts.ts_read_proc
    elif "eiger2" in d_names:
        roi_pv = eiger2.stats1.ts_total
        roi_pv_force_update = eiger2.stats1.ts.ts_read_proc
    elif "eiger_mobile" in d_names:
        roi_pv = eiger_mobile.stats1.ts_total
        roi_pv_force_update = eiger_mobile.stats1.ts.ts_read_proc
    else:
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

    for d in detectors_stage_once:
        if d:
            yield from bps.mov(d.fly_next, True)




    #@subs_decorator(livepopup)
    @subs_decorator({'start': at_scan})
    @subs_decorator({'stop': finalize_scan})
    @ts_monitor_dec([roi_pv])
    # @monitor_during_decorator([xs.channel1.rois.roi01.value])  ## Uncomment this
    # @monitor_during_decorator([xs.channel1.rois.roi01.value, xs.array_counter])
    @stage_decorator([flying_zebra_2d])  # Below, 'scan' stage ymotor.
    @stage_decorator(flying_zebra_2d.detectors)
    @run_decorator(md=md)
    def plan():
        if verbose:
            print("Starting the plan ...")
            print(f"flying_zebra.detectors={flying_zebra_2d.detectors}")

        # print(f"Plan start (enc1): {flying_zebra._encoder.pc.data.cap_enc1_bool.get()}")
        # print(f"Plan start (enc2): {flying_zebra._encoder.pc.data.cap_enc2_bool.get()}")

        # TODO move this to stage sigs
        for d in flying_zebra_2d.detectors:
            if d.name != "merlin2":
                yield from bps.mov(d.total_points, num_total)

        ystep = 0
        print(f"Scanning 2D fly")
        # yield from bps.sleep(10)

        if verbose:
            print(f"Starting the next row")
        for d in detectors_stage_every_row:
            # if d and (d.name != "merlin2"):
            if d:
                yield from bps.mov(d.fly_next, True)

        direction = np.sign(scan_stop - scan_start)
        start = scan_start
        stop = scan_stop

        if verbose:
            print(f'Direction = {direction}')
            print(f'Start = {start}')
            print(f'Stop  = {stop}')

        def move_to_start_fly():
            "See http://nsls-ii.github.io/bluesky/plans.html#the-per-step-hook"

            # print(f"Start moving to beginning of the row")
            row_mv_to_start = short_uid('row')
            yield from bps.checkpoint()
            yield from set_scanner_velocity(5)
            yield from bps.abs_set(ymotor, scan_start-delta, group=row_mv_to_start)
            yield from bps.wait(group=row_mv_to_start)
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
        v = (np.abs(scan_stop - scan_start) / num_total) / dwell  # compute "stage speed"
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
            yield from abs_set(dpc.cam.num_triggers, num_total, wait=True)
            yield from abs_set(dpc.cam.num_images, 1, wait=True)
        if "eiger_mobile" in dets_by_name:
            # print(f"Configuring 'eiger_mobile' ...")
            dpc = dets_by_name["eiger_mobile"]
            yield from abs_set(dpc.cam.num_triggers, num_total, wait=True)
            yield from abs_set(dpc.cam.num_images, 1, wait=True)

        ion = flying_zebra_2d.sclr
        if ion:
            yield from abs_set(ion.nuse_all, num_total, wait=True)
            yield from abs_set(ion.input_mode, 2, wait=True)
            #yield from abs_set(ion.nuse_all, 2*xnum, wait=True)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - DETECTORS ARE CONFIGURED')

        def zebra_kickoff():
            # start_zebra, stop_zebra = xstart * 1000000, xstop * 1000000
            start_zebra, stop_zebra = scan_start, scan_stop
            yield from kickoff(flying_zebra_2d,
                                ystart=start_zebra, ystop=stop_zebra, num=num_total, dwell=dwell, delta=np.abs(delta), pulse_dur = pulse_dur,
                                wait=True)
        yield from zebra_kickoff()

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - ZEBRA STARTED')

        # arm SIS3820, note that there is a 1 sec delay in setting X
        # into motion so the first point *in each row* won't
        # normalize...
        if ion:
            yield from abs_set(ion.erase_start, 1)
            if verbose:
                toc(t_startfly, str='TIMER (STEP) - SCALAR STARTED')


        # trigger all of the detectors
        row_scan = short_uid('row')
        if verbose:
            print('Data collection:')
        for d in flying_zebra_2d.detectors:
            if verbose:
                print(f'  triggering {d.name}')
            st = yield from bps.trigger(d)
            st.add_callback(lambda x: toc(t_startfly, str=f"  DETECTOR  {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')}"))

            # if (d.name == 'merlin2'):
            # if (d.name == 'eiger2'):
            #     t_wait_detector = tic()
            #     # while d.cam.num_images_counter.get() != 0:
            #     # while (d.cam.detector_state.get(as_string=True) != "Acquire"):
            #     # while not d.cam.acquire.get():
            #         # print("Waiting for detector state")
            #         # yield from bps.sleep(0.001)
            #     yield from bps.sleep(0.2)
            #     if verbose:
            #         toc(t_wait_detector, str=f'  waiting for detector {d.name!r}')
            # if (d.name == 'eiger_mobile'):
            #     t_wait_detector = tic()
            #     # while d.cam.num_images_counter.get() != 0:
            #     # while (d.cam.detector_state.get(as_string=True) != "Acquire"):
            #     # while not d.cam.acquire.get():
            #         # print("Waiting for detector state")
            #         # yield from bps.sleep(0.001)
            #     yield from bps.sleep(0.2)
            #     if verbose:
            #         toc(t_wait_detector, str=f'  waiting for detector {d.name!r}')

        if roi_pv_force_update:
            yield from bps.mv(roi_pv_force_update, 1)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - DETECTORS TRIGGERED')

        # start the 'fly'
        def print_watch(*args, **kwargs):
            with open('~/bluesky_output.txt', 'a') as f:
                f.write(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f\n'))
                # print(args)
                f.write(json.dumps(kwargs))
                f.write('\n')
        st = yield from abs_set(ymotor, scan_stop+delta,group=row_scan)
        if verbose:
            st.add_callback(lambda x: toc(t_startfly, str=f"  MOTOR  {datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S.%f')}"))

        # st = yield from abs_set(xmotor, row_stop)
        # st.watch(print_watch)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - MOTOR STARTED')

        if verbose and False:
            ttime.sleep(1)
            while (xmotor.motor_is_moving.get()):
                ttime.sleep(0.001)
            toc(t_datacollect, str='  move end')
            while (xs.settings.detector_state.get()):
                ttime.sleep(0.001)
            toc(t_datacollect, str='  xs done')
            while (sclr1.acquiring.get()):
                ttime.sleep(0.001)
            toc(t_datacollect, str='  sclr1 done')

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
        if dpc._acquisition_signal.get() == 1:
            print("Eiger trigger not finished, sending stop signal")
            yield from bps.sleep(0.2)
            yield from abs_set(dpc._acquisition_signal,0,wait=True)
        if flying_zebra_2d._encoder.pc.armed.get() == 1:
            print("Zebra still armed, sending disarm signal")
            yield from bps.sleep(0.2)
            yield from abs_set(flying_zebra_2d._encoder.pc.disarm,1,wait=True)

        # yield from bps.sleep(1)

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - MOTOR STOPPED. ACQUISITION_COMPLETED.')

        # we still know about ion from above
        if ion:
            yield from abs_set(ion.stop_all, 1)  # stop acquiring scaler

        # print(f"Resetting scanner velocity")
        # set speed back
        yield from set_scanner_velocity(5)
        # print(f"Completed resetting scanner velocity")

        # @timer_wrapper
        def zebra_complete():
            yield from complete(flying_zebra_2d)  # tell the Zebra we are done
        if verbose:
            t_zebcomplete = tic()
        yield from zebra_complete()
        if verbose:
            toc(t_zebcomplete, str='Zebra complete')

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - ZEBRA ACQUISITION COMPLETED.')

        # @timer_wrapper
        def zebra_collect():
            yield from collect(flying_zebra_2d)  # extract data from Zebra
        if verbose:
            t_zebcollect = tic()
        yield from zebra_collect()
        if verbose:
            toc(t_zebcollect, str='Zebra collect')

        if verbose:
            toc(t_startfly, str='TIMER (STEP) - ZEBRA COLLECTION COMPLETED.')

        # Force update of the respective PV so that all collected monitoring data for the row
        #   is loaded before the plugin is reset. Otherwise data in monitoring stream will not
        #   contain last points of rows.
        if roi_pv_force_update:
            yield from bps.mv(roi_pv_force_update, 1)

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



class SRXFlyer2D(Device):
    """
    This is the Zebra.
    """
    LARGE_FILE_DIRECTORY_WRITE_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_READ_PATH = LARGE_FILE_DIRECTORY_PATH
    LARGE_FILE_DIRECTORY_ROOT = LARGE_FILE_DIRECTORY_ROOT
    KNOWN_DETS = {"xs", "xs2", "merlin2", "eiger2", "dexela", "eiger_mobile"}
    fast_axis = Cpt(Signal, value="HOR", kind="config")
    slow_axis = Cpt(Signal, value="VER", kind="config")

    @property
    def encoder(self):
        return self._encoder

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

    def __init__(self, dets, sclr, zebra, *, reg=db.reg, **kwargs):
        super().__init__("", parent=None, **kwargs)
        self._mode = "idle"
        self._dets = dets
        self._sis = sclr
        self._filestore_resource = None
        self._encoder = zebra

        self.fast_axis.put('NANO2D')
        self.slow_axis.put('NANO2D')

        # self._encoder.pc.block_state_reset.put(1)
        self.reg = reg
        self._document_cache = []
        self._last_bulk = None

        self._point_counter = None
        self.frame_per_point = None

        self._data_exporter = ExportNanoZebraData()
        if self._sis is not None:
            self._data_sis_exporter = ExportSISData()

    def _select_captured_data(self):
        """
        Select the data to be captured by Zebra. Capturing unnecessary data slows down
        the scans, so only necessary sources should be selected. Setting the respective
        PVs can not be done in a fast sequence (technically setting PV is fast, but Zebra
        parameters remain unchanged unless there is a pause after writing to each PV),
        so the configuration can not be performed using 'stage_sigs'.
        """
        dir = self.fast_axis.get()

        sigs = {_: 0 for _ in [
            self._encoder.pc.data.cap_enc1_bool,
            self._encoder.pc.data.cap_enc2_bool,
            self._encoder.pc.data.cap_enc3_bool,
            self._encoder.pc.data.cap_enc4_bool,
            self._encoder.pc.data.cap_filt1_bool,
            self._encoder.pc.data.cap_filt2_bool,
            self._encoder.pc.data.cap_div1_bool,
            self._encoder.pc.data.cap_div2_bool,
            self._encoder.pc.data.cap_div3_bool,
            self._encoder.pc.data.cap_div4_bool
        ]}

        if dir == "NANO2D":
            sigs[self._encoder.pc.data.cap_enc1_bool] = True
            sigs[self._encoder.pc.data.cap_enc2_bool] = True
        elif dir == "NANOHOR":
            sigs[self._encoder.pc.data.cap_enc1_bool] = bool(load_positions_from_zebra)
        elif dir == "NANOVER":
            sigs[self._encoder.pc.data.cap_enc2_bool] = bool(load_positions_from_zebra)
        elif dir == "NANOZ":
            sigs[self._encoder.pc.data.cap_enc3_bool] = bool(load_positions_from_zebra)
        else:
            raise ValueError(f"Unknown value: dir={dir!r}")

        # Change the PV values only if the new values is different from the current values.
        for sig, value in sigs.items():
            current_value = sig.get()
            if current_value != value:
                sig.set(value).wait()
                ttime.sleep(0.2)  # Determined experimentally

    def stage(self):
        self._point_counter = 0
        dir = self.fast_axis.get()

        self._select_captured_data()

        # # Gating info for encoder capture
        self.stage_sigs[self._encoder.pc.gate_num] = 1
        self.stage_sigs[self._encoder.pc.pulse_start] = 0

        # This is for the merlin
        self.stage_sigs[self._encoder.output1.ttl.addr] = 31

        # Scaler
        self.stage_sigs[self._encoder.output2.ttl.addr] = 31
        self.stage_sigs[self._encoder.output3.ttl.addr] = 31

        self.stage_sigs[self._encoder.pc.gate_source] = "Position"
        self.stage_sigs[self._encoder.pc.pulse_source] = "Time"

        if self._sis is not None:
            # Put SIS3820 into single count (not autocount) mode
            self.stage_sigs[self._sis.count_mode] = 0
            self.stage_sigs[self._sis.count_on_start] = 1
            # Stop the SIS3820
            self._sis.stop_all.put(1)

        if dir == "NANOHOR":
            self.stage_sigs[self._encoder.pc.enc] = "Enc1"
            # self.stage_sigs[self._encoder.pc.dir] = "Positive"
            # self.stage_sigs[self._encoder.pc.enc_res2] = 9.5368e-05
        elif dir == "NANOVER":
            self.stage_sigs[self._encoder.pc.enc] = "Enc2"
            # self.stage_sigs[self._encoder.pc.dir] = "Positive"
            # self.stage_sigs[self._encoder.pc.enc_res2] = 9.5368e-05
        elif dir == "NANOZ":
            self.stage_sigs[self._encoder.pc.enc] = "Enc3"
            # self.stage_sigs[self._encoder.pc.dir] = "Positive"
            # self.stage_sigs[self._encoder.pc.enc_res2] = 9.5368e-05
        elif dir == "NANO2D":
            self.stage_sigs[self._encoder.pc.enc] = "Enc2"
            # self.stage_sigs[self._encoder.pc.dir] = "Positive"
            # self.stage_sigs[self._encoder.pc.enc_res2] = 9.5368e-05
        else:
            raise ValueError(f"Unknown value: dir={dir!r}")

        # print(f"stage_sigs={self.stage_sigs}") ##

        self.__filename = "{}.h5".format(uuid.uuid4())
        self.__filename_sis = "{}.h5".format(uuid.uuid4())
        self.__read_filepath = os.path.join(
            self.LARGE_FILE_DIRECTORY_READ_PATH, self.__filename
        )
        self.__read_filepath_sis = os.path.join(
            self.LARGE_FILE_DIRECTORY_READ_PATH, self.__filename_sis
        )
        self.__write_filepath = os.path.join(
            self.LARGE_FILE_DIRECTORY_WRITE_PATH, self.__filename
        )
        self.__write_filepath_sis = os.path.join(
            self.LARGE_FILE_DIRECTORY_WRITE_PATH, self.__filename_sis
        )

        self.__filestore_resource, self._datum_factory_z = resource_factory(
            ZebraHDF5Handler.HANDLER_NAME,
            root=self.LARGE_FILE_DIRECTORY_ROOT,
            resource_path=self.__read_filepath,
            resource_kwargs={"frame_per_point": self.frame_per_point},
            path_semantics="posix",
        )
        self.__filestore_resource_sis, self._datum_factory_sis = resource_factory(
            SISHDF5Handler.HANDLER_NAME,
            root=self.LARGE_FILE_DIRECTORY_ROOT,
            resource_path=self.__read_filepath_sis,
            resource_kwargs={"frame_per_point": self.frame_per_point},
            path_semantics="posix",
        )

        resources = [self.__filestore_resource]
        if self._sis:
            resources.append(self.__filestore_resource_sis)
        self._document_cache.extend(("resource", _) for _ in resources)

        self._data_exporter.open(self.__write_filepath)
        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            self._data_sis_exporter.open(
                self.__write_filepath_sis, mca_names=sis_mca_names, ion=self._sis, zebra=self._encoder
            )

        super().stage()

    def unstage(self):
        self._point_counter = None
        self._data_exporter.close()
        if self._sis is not None:
            self._data_sis_exporter.close()
        super().unstage()

    def describe_collect(self):

        ext_spec = "FileStore:"

        spec = {
            "external": ext_spec,
            "dtype": "array",
            "shape": [self._npts],
            "source": "",  # make this the PV of the array the det is writing
        }

        desc = OrderedDict()
        for chan in ("time", "enc1", "enc2", "enc3"):
            desc[chan] = spec
            desc[chan]["source"] = getattr(self._encoder.pc.data, chan).pvname

        # Handle the detectors we are going to get
        for d in self._dets:
            desc.update(d.describe())

        # Handle the ion chamber that the zebra is collecting
        if self._sis is not None:
            sis_mca_names = self._sis_mca_names()
            for n, name in enumerate(sis_mca_names):
                desc[name] = spec
                desc[name]["source"] = self._sis.mca_by_index[n + 1].spectrum.pvname

        return {"primary": desc}

    def kickoff(self, *, ystart, ystop, num, dwell, delta = 0.1, pulse_dur):
        # print(f"Kickoff: xstart={xstart} xtop={xstop} dwell={dwell}")

        self._data_exporter.set_fixed_positions()
        self._data_exporter.set_fast_axis_parameters(fast_start=ystart, fast_stop=ystop, fast_n=num)

        dets_by_name = {d.name: d for d in self.detectors}

        self._encoder.pc.arm.put(0)
        self._mode = "kicked off"
        self._npts = int(num)
        if ystart < ystop:
            direction = 1
        else:
            direction = -1
        # pxsize = np.abs(ystop - ystart) / (num - 1)
        extent = np.abs(ystop - ystart)
        # 2 ms delay between pulses
        # decrement = (pxsize / dwell) * 0.0005
        # decrement = max(decrement, 1e-5)

        self._encoder.pc.dir.put((-direction/2)+0.5)

        # print(f"gate_start={xstart - direction * (pxsize/2)}")
        # print(f"extent={extent}")
        self._encoder.pc.gate_start.put(ystart)
        self._encoder.pc.gate_step.put(extent + delta*0.5)
        self._encoder.pc.gate_width.put(extent + delta*0.3)

        self._encoder.pc.pulse_start.put(0.0)
        self._encoder.pc.pulse_max.put(num)
        self._encoder.pc.pulse_width.put(dwell*pulse_dur)
        self._encoder.pc.pulse_step.put(dwell)
        self._encoder.pc.pulse_delay.put(dwell*pulse_dur*0.5)
        # self._encoder.pc.pulse_width.put(pxsize * 0.2)

        # # self._encoder.pc.pulse_width.put(pxsize - decrement)
        # # If decrement is too small, then zebra will not send individual pulses
        # # but integrate over the entire line
        # # Hopefully taken care of with decrement check above

        # The case when Merlin is configured to work in 'Trigger Enable' trigger mode.
        # The numbers are picked using trial and error method and work for dwell time
        #   up to 0.004 s (250 Hz acquistion rate).
        # velocity = pxsize / dwell

        # if any([("merlin" in _) for _ in dets_by_name]):
        #     x_debounce = 0.0025 * velocity  # The true debounce time is 0.0016392 s
        # else:
        #     x_debounce = 0

        # pulse_width = pxsize * 0.9 - x_debounce

        # if pulse_width < 0:
        #     raise Exception(f"Dwell time is too small ...")
        # self._encoder.pc.pulse_width.put(pulse_width)

        # Arm the zebra
        self._encoder.pc.arm.put(1)

        # TODO Return a status object *first* and do the above asynchronously.
        return NullStatus()

    def _sis_mca_names(self):
        n_mcas = n_scaler_mca
        return [getattr(self._sis.channels, f"chan{_}").name for _ in range(1, n_mcas + 1)]

    def complete(self):
        """
        Call this when all needed data has been collected. This has no idea
        whether that is true, so it will obligingly stop immediately. It is
        up to the caller to ensure that the motion is actually complete.
        """

        amk_debug_flag = False

        # print(f"Complete 1")
        # Our acquisition complete PV is: XF:05IDD-ES:1{Dev:Zebra1}:ARRAY_ACQ
        while self._encoder.pc.data_in_progress.get() == 1:
            time.sleep(0.01)
        # print(f"Complete 2")
        # ttime.sleep(.1)
        self._mode = "complete"
        self._encoder.pc.block_state_reset.put(1)
        # see triggering errors of the xspress3 on suspension.  This is
        # to test the reset of the xspress3 after a line.

        # print(f"Complete 3")

        for d in self._dets:
            d.stop(success=True)

        # print(f"Complete 4")

        time_datum = self._datum_factory_z({"column": "time", "point_number": self._point_counter})
        enc1_datum = self._datum_factory_z({"column": "enc1", "point_number": self._point_counter})
        enc2_datum = self._datum_factory_z({"column": "enc2", "point_number": self._point_counter})
        enc3_datum = self._datum_factory_z({"column": "enc3", "point_number": self._point_counter})
        if self._sis:
            sis_mca_names = self._sis_mca_names()
            sis_datum = []
            for name in sis_mca_names:
                sis_datum.append(self._datum_factory_sis({"column": name, "point_number": self._point_counter}))

        self._document_cache.extend(
            ("datum", d)
            for d in (
                time_datum,
                enc1_datum,
                enc2_datum,
                enc3_datum,
            )
        )

        if self._sis:
            self._document_cache.extend(("datum", d) for d in sis_datum)

        # grab the asset documents from all of the child detectors
        for d in self._dets:
            self._document_cache.extend(d.collect_asset_docs())

        # Write the file.
        # @timer_wrapper
        def get_zebra_data():
            self._data_exporter.export(self._encoder, self.fast_axis.get())

        if amk_debug_flag:
            t_getzebradata = tic()
        get_zebra_data()
        if amk_debug_flag:
            toc(t_getzebradata, str='Get Zebra data')

        # @timer_wrapper
        def get_sis_data():
            if self._sis is None:
                return
            self._data_sis_exporter.export()

            # export_sis_data(
            #     self._sis, sis_mca_names, self.__write_filepath_sis, self._encoder
            # )

        if amk_debug_flag:
            t_sisdata = tic()
        get_sis_data()
        if amk_debug_flag:
            toc(t_sisdata, str='Get SIS data')

        # Yield a (partial) Event document. The RunEngine will put this
        # into metadatastore, as it does all readings.
        self._last_bulk = {
            "time": ttime.time(),
            "seq_num": 1,
            "data": {
                "time": time_datum["datum_id"],
                "enc1": enc1_datum["datum_id"],
                "enc2": enc2_datum["datum_id"],
                "enc3": enc3_datum["datum_id"],
            },
            "timestamps": {
                "time": time_datum["datum_id"],  # not a typo#
                "enc1": time_datum["datum_id"],
                "enc2": time_datum["datum_id"],
                "enc3": time_datum["datum_id"],
            },
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

    def collect(self):
        # Create records in the FileStore database.
        # move this to stage because I thinkt hat describe_collect needs the
        # resource id
        # TODO use ophyd.areadectector.filestoer_mixins.resllource_factory here
        if self._last_bulk is None:
            raise Exception(
                "the order of complete and collect is brittle and out "
                "of sync. This device relies on in-order and 1:1 calls "
                "between complete and collect to correctly create and stash "
                "the asset registry documents"
            )
        yield self._last_bulk
        self._point_counter += 1
        self._last_bulk = None
        self._mode = "idle"

    def collect_asset_docs(self):
        yield from iter(list(self._document_cache))
        self._document_cache.clear()

    def stop(self):
        self._encoder.pc.block_state_reset.put(1)
        pass

    def pause(self):
        "Pausing in the middle of a kickoff nukes the partial dataset."
        self._encoder.pc.block_state_reset.put(1)
        if self._sis is not None:
            self._sis.stop_all.put(1)
        for d in self._dets:
            if hasattr(d, "settings"):
                d.settings.acquire.put(0)
            if hasattr(d, "cam"):
                d.cam.acquire.put(0)
        self._mode = "idle"
        self.unstage()

    def resume(self):
        self.unstage()
        self.stage()

nano_flying_zebra_2d = SRXFlyer2D(
    list(xs for xs in [xs] if xs is not None), sclr1 if use_sclr else None, nanoZebra, name="nano_flying_zebra_2D"
)

def pt_fly2dcont(dets, motor1, scan_start1, scan_end1, num1, motor2, scan_start2, scan_end2, num2, exposure_time, pos_return = True, **kwargs):
    """
    Relative scan
    """
    m1_pos = motor1.position
    m2_pos = motor2.position
    print(f"Initial positions: m1_pos={m1_pos}  m2_pos={m2_pos}")
    try:
        center1, range1 =(scan_start1+scan_end1)/2, np.abs(scan_end1-scan_start1)
        start2, end2 = m2_pos + scan_start2, m2_pos + scan_end2
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
        kwargs.setdefault('flying_zebra_2d', nano_flying_zebra_2d)

        nano_flying_zebra_2d._encoder.pc.enc_pos2_sync.put(1)
        #args = [center1, range1, num1, scan_start2, scan_end2, num2, exposure_time]

        # print(kwargs['xmotor'].name)
        # print(kwargs['ymotor'].name)
        # print(kwargs['flying_zebra'].name)

        #if motor1 == pt_tomo.ssx and motor2 == pt_tomo.ssy:
        yield from abs_set(nano_flying_zebra.fast_axis, 'NANO2D')
        yield from abs_set(nano_flying_zebra.slow_axis, 'NANO2D')
        # elif motor1 == pt_tomo.ssy and motor2 == pt_tomo.ssx:
        #     yield from abs_set(nano_flying_zebra.fast_axis, 'NANO2D')
        #     yield from abs_set(nano_flying_zebra.slow_axis, 'NANO2D')
        #else:
        #    raise RuntimeError(f"Unsupported set of motors: motor1={motor1} motor2={motor2}")

        #yield from abs_set(motor1,center1,wait=True)
        #yield from bps.stage(motor1)
        #yield from bps.unstage(motor1)

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
        # print(f"dets={dets} args={args} kwargs={kwargs}")

        # _xs = kwargs.pop('xs', xs)
        # if extra_dets is None:
        #     extra_dets = []
        # dets = [] if  _xs is None else [_xs]
        # dets = dets + extra_dets
        # print(f"dets={dets}")
        # yield from mv(pt_tomo.ssx, 0, pt_tomo.ssy, 0, pt_tomo.ssz, 0)
        # yield from bps.sleep(2)
        yield from scan_and_fly_2d(dets, center1, range1, num1, start2, end2, num2, exposure_time, **kwargs)
        print('Scan finished.')
        # yield from bps.sleep(1)
        #yield from set_scanner_velocity(5)
    finally:
        yield from pt_fg.off()
        if pos_return:
            mv_back = short_uid('back')
            yield from abs_set(motor1,m1_pos,group=mv_back)
            yield from abs_set(motor2,m2_pos,group=mv_back)
            yield from bps.wait(group=mv_back)
