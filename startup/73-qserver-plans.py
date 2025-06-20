
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
    
    yield from fly2dpd(dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t)


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

def mosaic_overlap_scan_for_queue(dets, ylen = 100, xlen = 100, overlap_per = 15, dwell = 0.05,
                        step_size = 500, plot_elem = ["Cl"],using_mll = False):

    max_travel = 30

    dsx_i = dsx.position
    dsy_i = dsy.position

    smarx_i = smarx.position
    smary_i = smary.position

    scan_dim = max_travel - round(max_travel*overlap_per*0.01)

    x_tile = round(xlen/scan_dim)
    y_tile = round(ylen/scan_dim)

    xlen_updated = scan_dim*x_tile
    ylen_updated = scan_dim*y_tile


    X_position = np.linspace(0,xlen_updated-scan_dim,x_tile)
    Y_position = np.linspace(0,ylen_updated-scan_dim,y_tile)
    
    X_position_abs = smarx.position*1000+(X_position)
    Y_position_abs = smary.position*1000+(Y_position)

    num_steps = round(max_travel*1000/step_size)

    if using_mll:

        yield from bps.movr(dsy, ylen_updated/-2)
        yield from bps.movr(dsx, xlen_updated/-2)
        X_position_abs = dsx.position+(X_position)
        Y_position_abs = dsy.position+(Y_position)
        

    else:
        yield from bps.movr(smary, ylen_updated*-0.001/2)
        yield from bps.movr(smarx, xlen_updated*-0.001/2)
        X_position_abs = smarx.position+(X_position*0.001)
        Y_position_abs = smary.position+(Y_position*0.001)
        
        print(X_position_abs)
        print(Y_position_abs)
        
        
    for i in tqdm.tqdm(Y_position_abs):
            for j in tqdm.tqdm(X_position_abs):
                print((i,j))
                yield from check_for_beam_dump(threshold=5000)
                yield from bps.sleep(1) #cbm catchup time

                if using_mll:

                    yield from bps.mov(dsy, i)
                    yield from bps.mov(dsx, j)
                    yield from fly2d(dets,dssx,-15,15,num_steps,dssy,-15,15,num_steps,dwell)
                    yield from bps.sleep(1)
                    yield from bps.mov(dssx,0,dssy,0)

                else:

                    yield from bps.mov(smary, i)
                    yield from bps.mov(smarx, j)
                    yield from fly2d(dets, zpssx,-15,15,num_steps,zpssy, -15,15,num_steps,dwell)
                    yield from bps.sleep(1)
                    yield from bps.mov(zpssx,0,zpssy,0)


def send_mosaic_overlap_scan_to_queue(dets, ylen = 100, xlen = 100, overlap_per = 15, dwell = 0.05,
                        step_size = 500, plot_elem = ["Cl"],using_mll = False):

    max_travel = 30
    scan_dim = max_travel - round(max_travel*overlap_per*0.01)

    x_tile = round(xlen/scan_dim)
    y_tile = round(ylen/scan_dim)

    xlen_updated = scan_dim*x_tile
    ylen_updated = scan_dim*y_tile


    X_position = np.linspace(0,xlen_updated-scan_dim,x_tile)
    Y_position = np.linspace(0,ylen_updated-scan_dim,y_tile)


    num_steps = round(max_travel*1000/step_size)

    unit = "minutes"
    fly_time = (num_steps**2)*dwell*2
    num_flys= len(X_position)*len(Y_position)
    total_time = (fly_time*num_flys)/60


    if total_time>60:
        total_time/=60
        unit = "hours"

    #print(f'total time = {total_time} {unit}; 10 seconds to quit')

    ask = input(f"Optimized scan x and y range = {xlen_updated} by {ylen_updated};"
     f"\n total time = {total_time} {unit}"
     f"\n Do you wish to send it to queue? (y/n) ")

    if ask == 'y':

            det_names = [d.name for d in dets]
            RM.item_add((BPlan("mosaic_overlap_scan_for_queue",
            det_names,
            ylen = ylen, 
            xlen = xlen, 
            overlap_per = overlap_per, 
            dwell = dwell,
            step_size = step_size, 
            plot_elem = plot_elem,
            using_mll = using_mll)))



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


