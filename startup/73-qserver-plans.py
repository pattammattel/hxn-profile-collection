
def get_current_position(zp_flag = True):
        roi = {}
        if zp_flag:

            fx, fy, fz = zpssx.position, zpssy.position, zpssz.position
            cx, cy, cz = smarx.position, smary.position, smarz.position
            zpz1_pos = zp.zpz1.position
            zp_sx, zp_sz = zps.zpsx.position, zps.zpsz.position
            th = zpsth.position

            roi = {
                "zpssx": fx, "zpssy": fy, "zpssz": fz,
                "smarx": cx, "smary": cy, "smarz": cz,
                "zp.zpz1": zpz1_pos, "zpsth": th,
                "zps.zpsx": zp_sx, "zps.zpsz": zp_sz
            }

        else:
            fx, fy, fz = dssx.position, dssy.position, dssz.position
            cx, cy, cz = dsx.position, dsy.position, dsz.position
            sbz_pos = sbz.position
            th = dsth.position
            roi = {
                "dssx": fx, "dssy": fy, "dssz": fz,
                "dsx": cx, "dsy": cy, "dsz": cz,
                "sbz": sbz_pos, "dsth": th,
            }

        return roi


def recover_pos_and_scan(label,roi_positions, dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t, ic1_count = 55000, scan_time_min = 5.0):

    print(f"{label} running")
    for key, value in roi_positions.items():
        if not key == "zp.zpz1":
            yield from bps.mov(eval(key), value)
        elif key == "zp.zpz1":
            yield from mov_zpz1(value)

        print(f"{key} moved to {value :.3f}")

        

    yield from check_for_beam_dump(threshold = 5000)

    if sclr2_ch2.get() < ic1_count*0.9:
        yield from peak_the_flux()
    else:
        pass
    RE.md["scan_name"] = str(label)

    dets = dets_fast

    try:
    
        yield from fly2dpd(dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t)

        yield from piezos_to_zero()

    except: pass


def fly2d_qserver_plan(label, dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t):
     RE.md["scan_name"] = str(label)
     yield from fly2dpd(dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t)

def send_fly2d_to_queue(label, dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t):
    det_names = [d.name for d in eval(dets)]
    RM.item_add((BPlan("fly2d_qserver_plan",
            label,
            det_names, 
            mot1, 
            mot1_s, 
            mot1_e, 
            mot1_n, 
            mot2, 
            mot2_s, 
            mot2_e, 
            mot2_n, 
            exp_t)))
    


def align_and_scan(
        dets,
        x_motor, x_start, x_end, x_num,
        y_motor,y_start, y_end, y_num,
        exposure=0.01,
        elem='Pt_L',
        pad_frac=0.5,
        do_2d_align=False,
        tomo_use_panda=True
    ):
    """
    Aligns a particle using 1D (X, Y) and optional 2D COM alignment scans,
    then performs a 2D fly scan.

    Alignment ranges are automatically derived from the 2D scan window by
    adding a fractional padding (pad_frac), and step sizes are scaled
    relative to the 2D fly scan resolution.

    Parameters
    ----------
    x_motor, y_motor : EpicsMotor
        Motors to use for the 2D scan.
    x_start, x_end, x_num : float
        Range and number of points for X fly scan.
    y_start, y_end, y_num : float
        Range and number of points for Y fly scan.
    exposure : float
        Exposure time per point (seconds).
    elem : str
        Element edge for XRF alignment signal.
    pad_frac : float
        Fractional padding for alignment range (default = 0.2).
    do_2d_align : bool
        Whether to perform a 2D COM alignment between 1D alignments.
    tomo_use_panda : bool
        Use Panda trigger mode for scans.

    Example
    -------
    RE(particle_align_and_scan(zps.sx, zps.sy, -5, 5, 100, -5, 5, 100, 0.05, 'Pt_L'))
    """

    # --- Compute padded ranges ---
    x_range = x_end - x_start
    y_range = y_end - y_start

    x_pad = pad_frac * x_range / 2
    y_pad = pad_frac * y_range / 2

    x_align_start = x_start - x_pad
    x_align_end   = x_end + x_pad
    y_align_start = y_start - y_pad
    y_align_end   = y_end + y_pad

    # --- Proportional step sizes ---
    x_step_size = (x_end - x_start) / max(x_num, 1)
    y_step_size = (y_end - y_start) / max(y_num, 1)

    # coarser alignment resolution (~1/3 of fly scan)
    x_align_num = max(5, int((x_align_end - x_align_start) / (3 * x_step_size)))
    y_align_num = max(5, int((y_align_end - y_align_start) / (3 * y_step_size)))

    print(f"→ X alignment range: {x_align_start:.2f} to {x_align_end:.2f}, {x_align_num} pts")
    print(f"→ Y alignment range: {y_align_start:.2f} to {y_align_end:.2f}, {y_align_num} pts")

    # --- 1D X alignment ---
    print("→ Performing X alignment...")
    yield from align_scan(
        x_motor,
        x_align_start, x_align_end, x_align_num,
        exposure, elem,
        align_with="line_center",
        threshold=0.5,
        move_coarse=False,
        neg_flag=False,
        offset=0,
        tomo_use_panda=tomo_use_panda,
        reset_piezos_to_zero=True,
        initial_position=0,
        align_movement_limit=3
    )

    # --- Optional 2D COM alignment ---
    if do_2d_align:
        print("→ Performing 2D COM alignment...")
        yield from align_2d_com_scan(
            x_motor,
            x_align_start, x_align_end, x_align_num,
            y_motor,
            y_align_start, y_align_end, y_align_num,
            exposure, elem,
            threshold=0.5,
            move_x=True, move_y=True,
            x_offset=0, y_offset=0,
            tomo_use_panda=tomo_use_panda
        )

    # --- 1D Y alignment ---
    print("→ Performing Y alignment...")
    yield from align_scan(
        y_motor,
        y_align_start, y_align_end, y_align_num,
        exposure, elem,
        align_with="line_center",
        threshold=0.5,
        move_coarse=False,
        neg_flag=False,
        offset=0,
        tomo_use_panda=tomo_use_panda,
        reset_piezos_to_zero=True,
        initial_position=0,
        align_movement_limit=3
    )

    # --- Final 2D Fly Scan ---
    print("→ Running 2D fly scan with fly2dpd...")
    yield from fly2dpd(
        dets,
        x_motor, x_start, x_end, x_num,
        y_motor, y_start, y_end, y_num,
        exposure
    )

    print("✅ Particle alignment and 2D scan complete.")

def align_and_scan_qserver_plan(
        label,
        dets,
        x_motor, x_start, x_end, x_num,
        y_motor, y_start, y_end, y_num,
        exposure=0.01,
        elem='Pt_L',
        pad_frac=0.5,
        do_2d_align=False,
        tomo_use_panda=True
    ):
    """
    QServer-compatible version of align_and_scan().
    Assigns RE.md['scan_name'] = label and runs the full alignment + 2D scan plan.
    """
    RE.md["scan_name"] = str(label)
    yield from align_and_scan(
        eval(dets),
        eval(x_motor), x_start, x_end, x_num,
        eval(y_motor), y_start, y_end, y_num,
        exposure,
        elem,
        pad_frac,
        do_2d_align,
        tomo_use_panda
    )


def send_align_and_scan_to_queue(
        label,
        dets,
        x_motor, x_start, x_end, x_num,
        y_motor, y_start, y_end, y_num,
        exposure=0.01,
        elem='Pt_L',
        pad_frac=0.5,
        do_2d_align=False,
        tomo_use_panda=True
    ):
    """
    Adds an align_and_scan plan to the Bluesky Queue Server.

    Parameters
    ----------
    label : str
        Descriptive scan label (stored in RE.md["scan_name"])
    dets : str
        String for detector list (e.g. "[xs, sclr]")
    x_motor, y_motor : str
        Strings of motor objects (e.g. "zps.sx", "zps.sy")
    x_start, x_end, x_num : float
        Range and number of points for X motor
    y_start, y_end, y_num : float
        Range and number of points for Y motor
    exposure : float
        Exposure time per point (s)
    elem : str
        Element name for XRF alignment
    pad_frac : float
        Fractional padding for alignment (default 0.5)
    do_2d_align : bool
        Whether to run 2D COM alignment between 1D alignments
    tomo_use_panda : bool
        Use Panda trigger mode during scans
    """

    det_names = [d.name for d in eval(dets)]

    RM.item_add(
        BPlan(
            "align_and_scan_qserver_plan",
            label,
            det_names,
            x_motor, x_start, x_end, x_num,
            y_motor, y_start, y_end, y_num,
            exposure,
            elem,
            pad_frac,
            do_2d_align,
            tomo_use_panda
        )
    )

    print(f"✅ Added '{label}' align_and_scan plan to QServer queue.")


def get_scan_num_label(plan_dict):

    if plan_dict['args']:
        scan_label = plan_dict['args'][0]
        scan_plan = plan_dict['args'][3:12]

    else:
        scan_label = plan_dict['kwargs']["label"]
        scan_plan = [plan_dict['kwargs']["mot1"],
                      plan_dict['kwargs']["mot1_s"],
                      plan_dict['kwargs']["mot1_e"],
                      plan_dict['kwargs']["mot1_n"],
                      plan_dict['kwargs']["mot2"],
                      plan_dict['kwargs']["mot2_s"],
                      plan_dict['kwargs']["mot2_e"],
                      plan_dict['kwargs']["mot2_n"],
                      plan_dict['kwargs']["exp_t"]
                      ]

    scan_num = plan_dict['result']['scan_ids']
    status = plan_dict['result']['exit_status']
    
    return scan_num, scan_label, scan_plan, status
    
def get_complete_log(history_file):
    
    with open(history_file, "r") as fp:
        plans_dict = json.load(fp)

    log_sheet = pd.DataFrame(columns=["scan_num", "scan_label", "scan_plan","exit_status"], 
                             index=np.arange(len(plans_dict)))

    for n, plan in enumerate(plans_dict):
        #print(plan)
        scan_num, scan_label,scan_plan, status = get_scan_num_label(plan)
        print("additng to log")
        if scan_num:
            log_sheet["scan_num"].at[n] = scan_num[0]
        else:
            log_sheet["scan_num"].at[n] = None
        log_sheet["scan_label"].at[n] = scan_label
        log_sheet["scan_plan"].at[n] = scan_plan
        log_sheet["exit_status"].at[n] = status
        

    print(log_sheet)
    savedir = os.path.dirname(history_file)
    log_sheet.to_csv(f"{savedir}/scan_log.csv")


