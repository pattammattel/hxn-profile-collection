print(f"Loading {__file__!r} ...")

import json
import numpy as np
import tqdm
from datetime import datetime
from hxntools.motor_info import motor_table

det_dict = {"dets1":dets1,
            "dets2":dets2,
            "dets_fs":dets_fs}

mll_fly_motors= ["dssx", "dssy","dssz"]
mll_th_motor= "dsth"

zp_fly_motors= ["zpssx", "zpssy","zpssz"]
zp_th_motor= "zpsth"




#tomo_use_panda = False

def make_tomo_plan(save_as = "/nsls2/data/hxn/legacy/user_macros/HXN_GUI/Scan/temp_files/tomo_params.json" ):

    tomo_scan =     {"flying_panda":True,
                     "fly_motors":["dssx", "dssy","dssz"],
                     "th_motor":"dsth",
                    "angle_info":{"start":-90,
                                "end":90,
                                "angle_step":2},

                    "fly2d_scan":{'det':'dets1',
                                "x_start":-1,
                                "x_end":1,
                                "x_num":100,
                                "y_start":-1,
                                "y_end":1,
                                "y_num":100,
                                "exposure":0.03},

                    "xalign": {
                        "do_align": True,
                        "start": -10,
                        "end": 10,
                        "num": 300,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False
                    },
                    "yalign": {
                        "do_align": True,
                        "start": -4,
                        "end": 4,
                        "num": 200,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5
                    },
                    "align_2d_com": {
                        "do_align": False,
                        "x_start": -5,
                        "x_end": 5,
                        "x_num": 50,
                        "y_start": -2,
                        "y_end": 2,
                        "y_num": 20,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "threshold": 0.5,
                        "move_x": True,
                        "move_y": True,
                        "x_offset": -0.95,
                        "y_offset": -0.2,
                        "zero_before_scan": False
                    },

                    "stop_iter":False,
                    "add_angles":[ ],
                    "remove_angles":[-90,-91],
                    "stop_pdf":False,
                    "pdf_elems":["Au_L"],
                    "pause_scan":False,
                    "test":False,
                    "ic_threshold":0.9,
                    "do_y_offset": True,
                    "th_init": 58.99987099999999,
                    "y_init": -0.18154,
                    "scan_label":"HXN_Tomo_Scan",
                    "Notes": 'My sample # 10'
                }

    with open(save_as,"w") as fp:
            json.dump(tomo_scan,fp, indent=6)

    fp.close()

def align_scan(mtr,start,end,num,exp,elem_, align_with="line_center",
               threshold = 0.5,move_coarse = False, neg_flag = False, offset = 0,
               tomo_use_panda= True, reset_piezos_to_zero = False, initial_position=0, 
               align_movement_limit=0):

    """
    scan to align samples to field of view using using fly1d scan

    mtr--> scanning motor, dssx, dssy, dssz etc.
    start,end,num,exp --> flyscan paramters
    elem_ --> element to use for alignemnt
    align_with --> choose bettween "edge" or "line_center"
    threshold --> threshold for line centering

    """
    fly_to_coarse = {"zpssx":smarx,"zpssy":smary,"zpssz":smarz,
                     "dssx":dsx,"dssy":dsy,"dssz":dsz}


    if reset_piezos_to_zero:
            yield from bps.mov(mtr,0,wait=True)
            # yield from piezos_to_zero(zp_flag = zp_flag)

    if not tomo_use_panda:
        yield from fly1d(dets_fs,
                        mtr,
                        start,
                        end,
                        num,
                        exp
                        )
    else:
        print("uses panda scan")
        #TODO swap xmotor programically 
        yield from fly1dpd([fs,xspress3],
                        mtr,
                        start,
                        end,
                        num,
                        exp
                        )
    if align_with == "line_center":
        yield from bps.sleep(1)
        xc = return_line_center(-1,elem_,threshold, neg_flag = neg_flag)
        xc = xc+offset
        
    elif align_with == "edge":
        yield from bps.sleep(1)
        xc,_ = erf_fit(-1,elem_,linear_flag=False)
        if abs(xc) - abs(initial_position) > align_movement_limit:
            xc = mtr.position + offset
        else:
            xc = xc + offset
         
    else:
        xc = mtr.position

    if move_coarse:
        coarse_stage = fly_to_coarse[mtr.name]
        print(f"move {coarse_stage.name} relative {xc}")
        yield from bps.movr(coarse_stage,xc)
        
        # yield from bps.movr(eval(fly_to_coarse[mtr.name]),xc/uni_conv)
        #yield from piezos_to_zero(zp_flag = zp_flag)

    else:
        yield from bps.sleep(1)
        print(f"move {mtr.name} to {xc}")
        yield from bps.mov(mtr,xc)
    
    return xc


def tomo_2d_scan(angle,dets_,fly_motors,x_start,x_end,x_num,y_start,y_end,y_num,exp, 
                     tomo_use_panda = False):
    
    '''
    fly_motors = [dssx,dssy,dssz]
    fly_motors = [zpssx,zpssy,zpssz]
    '''

    if np.abs(angle) < 44.99:

        x_start_real = x_start / np.cos(angle * np.pi / 180.)
        x_end_real = x_end / np.cos(angle * np.pi / 180.)
        
        

        if fly_motors[0].name == 'zpssx':
            x_scale_factor = 1
            x_start_real /= x_scale_factor
            x_end_real /= x_scale_factor
        
        print(x_start_real,x_end_real)


        if not tomo_use_panda:
            yield from fly2d(dets_,
                            fly_motors[0],
                            x_start_real,
                            x_end_real,
                            x_num,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp
                            )
        else:
            yield from fly2dpd([fs,eiger2,xspress3],
                            fly_motors[0],
                            x_start_real,
                            x_end_real,
                            x_num,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp,
                            position_supersample = 10
                            )

    else:
        x_start_real = x_start / np.abs(np.sin(angle * np.pi / 180.))
        x_end_real = x_end / np.abs(np.sin(angle * np.pi / 180.))
        if fly_motors[2].name == 'dssz':
            pass
            # print('WARNING!!: Applying temporary scaling correction ratio to dssz motor.')
            # x_start_real *= 0.955
            # x_end_real *= 0.955

        elif fly_motors[2].name == 'zpssz':
            

            # x_scale_factor = 0.9542
            # z_scale_factor = 1.0309

            
            z_scale_factor = 1
            x_start_real /= z_scale_factor
            x_end_real /= z_scale_factor

            print(x_start_real,x_end_real)

        if not tomo_use_panda:
            yield from fly2d(dets_,
                            fly_motors[2],
                            x_start_real,
                            x_end_real,
                            x_num,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp
                            )
        else:
            yield from fly2dpd([fs,eiger2,xspress3],
                            fly_motors[2],
                            x_start_real,
                            x_end_real,
                            x_num,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp,
                            position_supersample = 10
                            )

def align_2d_com_scan(mtr1,x_s,x_e,x_n,mtr2,y_s,y_e,y_n,exp,elem_,
                      threshold,move_x=False,move_y=False, 
                      x_offset = 0, y_offset = 0,tomo_use_panda = True,
                      zero_before_scan = False
                      ):


    """
    @aaron removed 'angle' from first argument
    scan to align samples to field of view using using fly1d scan

    mtr1, mtr2--> scanning motor, dssx, dssy, dssz etc.
    xs,xe,xn,y_s,y_e,y_n,exp --> flyscan paramters
    elem_ --> element to use for alignemnt

    threshold --> threshold for center of mass
    move_x,move_y --> moves piezos to the com if true

    """
    #peform fly2d

    if zero_before_scan:
            yield from bps.mov(mtr1,0,wait=True)
            yield from bps.mov(mtr2,0,wait=True)



    if not tomo_use_panda:
        yield from fly2dpd(dets_fast,
                        mtr1,
                        x_s,
                        x_e,
                        x_n,
                        mtr2,
                        y_s,
                        y_e,
                        y_n,
                        exp)
    else:
        yield from fly2dpd(dets_fast,
                        mtr1,
                        x_s,
                        x_e,
                        x_n,
                        mtr2,
                         y_s,
                        y_e,
                        y_n,
                        exp)
            

    #find com
    cx,cy = return_center_of_mass(-1,
                                elem_,
                                threshold
                                )
    
    cx = cx + x_offset
    cy = cy + y_offset

    #move if true
    if move_x:
        yield from bps.mov(mtr1,cx)
    if move_y:
        yield from bps.mov(mtr2,cy)

def tomo_scan_to_loop(angle, tomo_params, ic_init, do_y_offset = True,tracking_file = None):

        #caput("XF:03IDC-ES{Merlin:2}HDF1:NDArrayPort","ROI1") #patch for merlin2 issuee

        #get parameters from json
        xalign = tomo_params["xalign"]
        yalign = tomo_params["yalign"]
        align_2d = tomo_params["align_2d_com"]
        image_scan = tomo_params["fly2d_scan"]
        dets = eval(image_scan["det"])
        elems_to_pdf = tomo_params["pdf_elems"]
        fly_motors= [eval(item) for item in tomo_params["fly_motors"]]


        yield from bps.mov(eval(tomo_params["th_motor"]), angle)

        if do_y_offset:

            # precalculated y offset, mll only
            y_init = tomo_params["y_init"]
            th_init = tomo_params["th_init"]
            y_offset1 = sin_func(angle, 0.110, -0.586, 7.85,1.96)
            y_offset2 = sin_func(th_init, 0.110, -0.586, 7.85,1.96)
            yield from bps.mov(dssy,y_init+y_offset1-y_offset2)



        #yield from bps.mov(dssx,0,dssz,0)
        print(f'{tomo_params["flying_panda"] = }')
        #1d alignment sequence, based on angle x or z will be scanned
        if np.abs(angle) < 44.99:
            print('dssx scanning')
            if xalign["do_align"]:
                yield from align_scan(fly_motors[0],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                tomo_params["flying_panda"],
                                xalign["zero_before_scan"]
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:

                x_start_real = align_2d["x_start"] / np.cos(angle * np.pi / 180.)
                x_end_real = align_2d["x_end"] / np.cos(angle * np.pi / 180.)


                yield from align_2d_com_scan(   fly_motors[0],
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                tomo_params["flying_panda"],
                                                align_2d["zero_before_scan"])

            else:
                pass

        else:
            print('dssz scanning')
            if xalign["do_align"]:
                yield from align_scan(  fly_motors[2],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                tomo_params["flying_panda"],
                                xalign["zero_before_scan"]
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:

                x_start_real = align_2d["x_start"] / np.abs(np.sin(angle * np.pi / 180.))
                x_end_real = align_2d["x_end"] / np.abs(np.sin(angle * np.pi / 180.))

                yield from align_2d_com_scan(   fly_motors[2],
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                tomo_params["flying_panda"],
                                                align_2d["zero_before_scan"]
                                                )
            else:
                pass

        #1d y alignemnt scan
        if yalign["do_align"]:
            yield from align_scan(  fly_motors[1],
                                    yalign["start"],
                                    yalign["end"],
                                    yalign["num"],
                                    yalign["exposure"],
                                    yalign["elem"],
                                    yalign["center_with"],
                                    yalign["threshold"],
                                    yalign["move_coarse"],
                                    xalign["neg_flag"],
                                    yalign["offset"],
                                    tomo_params["flying_panda"],
                                    yalign["zero_before_scan"],
                                    tomo_params["y_init"],
                                    yalign["align_movement_limit"]
                )

        else:
            pass

        #2d scan sequence, based on angle x or z are scanned
        yield from tomo_2d_scan(    angle,
                                    dets,
                                    fly_motors,
                                    image_scan["x_start"],
                                    image_scan["x_end"],
                                    image_scan["x_num"],
                                    image_scan["y_start"],
                                    image_scan["y_end"],
                                    image_scan["y_num"],
                                    image_scan["exposure"],
                                    tomo_params["flying_panda"]
                                    )

        xspress3.unstage()

        #save images to pdf if
        if not tomo_params["stop_pdf"]:

            try:
                insert_xrf_map_to_pdf(-1,
                                      elements = elems_to_pdf,
                                      title_=['energy', tomo_params["th_motor"]],
                                      note = tomo_params["scan_label"])
                plt.close()

            except:
                pass
        if tracking_file is not None:
            flog = open(tracking_file,'a')
            flog.write("%d %.3f\n"%(db[-1].start['scan_id'],angle))
            flog.close()

def run_tomo_json(path_to_json,tracking_file = None):


    """mll_tomo_scan by taking parameters from a json file,
    TODO add angles smartly

    """
    beamDumpOccured = False

    #open json file for angle info first
    with open(path_to_json,"r") as fp:
        tomo_params = json.load(fp)
    fp.close()
    print("json file loaded")

    #create angle list for iteration
    angle_info = tomo_params["angle_info"]
    print(angle_info)
    # angles = np.arange(angle_info["start"],
    #                     angle_info["end"]+angle_info["angle_step"],
    #                     angle_info["angle_step"]
    #                     )

    angles = np.linspace(angle_info["start"],
                        angle_info["end"],
                        int(1+abs(angle_info["end"] - angle_info["start"])/angle_info["angle_step"])
                        )
    if "split_tomo" in angle_info:
        split = int(angle_info["split_tomo"])
        angles0 = angles.copy()
        angles = angles0[0::split]
        for i in range(1,split):
            angles = np.concatenate((angles,angles0[i::split]))
    if "start_angle" in angle_info:
        angst = angle_info["start_angle"]
        for i,ang in enumerate(angles):
            if np.abs(ang-angst)<1e-3:
                angles = angles[i:]
                break

    angle_list = pd.DataFrame(columns= ['scan_id', 'angle'])

    angle_list["angle"] = angles

    print(angle_list)


    yield from bps.sleep(2)
    fly_motors= [eval(item) for item in tomo_params["fly_motors"]]
    th_motor = eval(tomo_params["th_motor"])
    
    
    #get some initial parameters
    ic_0 = sclr2_ch2.get()
    th_init = th_motor.position
    y_init = fly_motors[1].position
    do_y_offset = tomo_params["do_y_offset"]
    tomo_params["th_init"] = th_init
    tomo_params["y_init"] = y_init
    

    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    yield from bps.sleep(2)

    logger.info("Reading IC3 value")

    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates

     #Ic values are useful for calibration

         #add real energy to the dataframe
    angle_list['energy_rbv'] = np.nan
    #add scan_id to the dataframe
    angle_list['scan_id'] = np.nan
    #record time
    angle_list['TimeStamp'] = pd.Timestamp.now()
    #record if peak beam happed before the scan
    angle_list['Peak Flux'] = False
    angle_list['IC3'] = ic_3_init
    angle_list['IC0'] = ic_0
    angle_list[fly_motors[1].name] = np.nan
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)


    #set the pause and stop inter keys to False before the loop
    #to reverse the abort scan and pause when using the gui
    tomo_params["stop_iter"] = False
    tomo_params["pause_scan"] = False

    with open(path_to_json,"w") as fp:
            json.dump(tomo_params,fp, indent=6)

    fp.close()
    
    fluxPeaked = False

    

    #loop with list of angles
    for n,angle in enumerate(tqdm.tqdm(angles,desc = 'Tomo Scan')):
        yield from bps.sleep(1)

        #open the json file to catch any updates
        with open(path_to_json,"r") as fp:
            tomo_params = json.load(fp)
            fp.close()

        #stop data collection if necessary.user input taken
        if tomo_params["stop_iter"]:
            save_page()
            break

        while tomo_params["pause_scan"]:
            yield from bps.sleep(10) #check if this freezes the gui or not
            with open(path_to_json,"r") as fp:
                tomo_params = json.load(fp)
                fp.close()

            if not tomo_params["pause_scan"]:
                break

        if tomo_params["remove_angles"]==None:
            tomo_params["remove_angles"] = []

        if not tomo_params["test"]:
            if sclr2_ch2.get()<1000:
                beamDumpOccured = True
                yield from check_for_beam_dump()


            if beamDumpOccured:
                angle = angles[n-1]
                yield from bps.sleep(60)
                yield from recover_from_beamdump()
                beamDumpOccured = False

        #look for beam dump and ic3 threshold, ignores for code tests using json
        if not tomo_params["test"]:
            #opening fast shutter for initial ic3 reading
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
            yield from bps.sleep(2)
            if (sclr2_ch4.get() < (tomo_params["ic_threshold"]*ic_3_init)):
                 yield from peak_the_flux()
                 ic_0 = sclr2_ch2.get()
                 fluxPeaked = True

        if not angle in np.array(tomo_params["remove_angles"]):
            #tomo scan at a single angle
            yield from tomo_scan_to_loop(angle,tomo_params,ic_0,do_y_offset = do_y_offset,tracking_file = tracking_file)

            last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

            #Add more info to the dataframe
            angle_list['energy_rbv'].at[n] = e.position #add real energy to the dataframe
            angle_list["angle"].at[n] = th_motor.position
            angle_list['scan_id'].at[n] = int(last_sid) #add scan_id to the dataframe
            angle_list['TimeStamp'].at[n] = pd.Timestamp.now()
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            angle_list['IC3'].at[n] = ic_3 #Ic values are useful for calibration
            angle_list['IC0'].at[n] = ic_0 #Ic values are useful for calibration
            angle_list['Peak Flux'].at[n] = fluxPeaked # recoed if peakflux was excecuted
            #angle_list['IC3_before_peak'].at[n] = ic3 #ic3 right after e change, no peaking
            fluxPeaked = False #reset
            angle_list[fly_motors[1].name].at[n] = fly_motors[1].position
            
            #close c shutter
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

            # save the DF in the loop so quitting a scan won't affect
            filename = f"{tomo_params.get('scan_label','')}_startID{int(angle_list['scan_id'][0])}.csv"
            angle_list.to_csv(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename),
                              float_format= '%.5f')
        else:
            print(f"{angle} skipped")
            pass


    #TODO add angles to scan; need to be better
    #sort based on what current angle is
    if not tomo_params["add_angles"]==None:

        added_angles = tomo_params["add_angles"]

        for nn,angle in enumerate(tqdm.tqdm(added_angles,desc = 'Tomo Scan; Additional Angles')):

            #open the json file to catch any updates
            with open(path_to_json,"r") as fp:
                tomo_params = json.load(fp)
                fp.close()

            #stop data collection if necessary.user input taken
            if tomo_params["stop_iter"]:
                save_page()
                break

            while tomo_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_json,"r") as fp:
                    tomo_params = json.load(fp)
                    fp.close()

                if not tomo_params["pause_scan"]:
                    break

            if not angle in np.array(tomo_params["remove_angles"]):
                yield from tomo_scan_to_loop(angle, tomo_params,ic_0,do_y_offset = do_y_offset)

                last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

                #Add more info to the dataframe
                angle_list['energy_rbv'].at[n] = e.position #add real energy to the dataframe
                angle_list["angle"].at[n] = th_motor.position
                angle_list['scan_id'].at[n] = int(last_sid) #add scan_id to the dataframe
                angle_list['TimeStamp'].at[n] = pd.Timestamp.now()
                ic_3 = sclr2_ch4.get()
                ic_0 = sclr2_ch2.get()
                angle_list['IC3'].at[n] = ic_3 #Ic values are useful for calibration
                angle_list['IC0'].at[n] = ic_0 #Ic values are useful for calibration
                angle_list['Peak Flux'].at[n] = fluxPeaked # recoed if peakflux was excecuted
                #angle_list['IC3_before_peak'].at[n] = ic3 #ic3 right after e change, no peaking
                fluxPeaked = False #reset
                angle_list[fly_motors[1].name].at[n] = fly_motors[1].position

                # save the DF in the loop so quitting a scan won't affect
                filename = f"hxn_zp_diff_{tomo_params.get('scan_label','')}_startID{int(angle_list['scan_id'][0])}.csv"
                angle_list.to_csv(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename),
                                float_format= '%.5f')

            else:
                print(f"{angle} skipped")
                pass

    else:
        pass

    #save pdf
    save_page()

###################Diffraction######################

def make_diff_plan(save_as = "/nsls2/data/hxn/legacy/user_macros/HXN_GUI/Scan/temp_files/diff_params.json" ):

    diff_scan =     {"flying_panda":False,
                     "fly_motors":["dssx", "dssy"],
                     "th_motor":"dsth",
                    "angle_info":{"start":70,
                                "end":71,
                                "angle_step":0.025},

                    "fly2d_scan":{'det':'dets4',
                                "x_start":-1,
                                "x_end":1,
                                "x_num":100,
                                "y_start":-1,
                                "y_end":1,
                                "y_num":100,
                                "exposure":0.03},

                    "xalign": {
                        "do_align": True,
                        "start": -10,
                        "end": 10,
                        "num": 300,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5
                    },
                    "yalign": {
                        "do_align": True,
                        "start": -4,
                        "end": 4,
                        "num": 200,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5
                    },
                    "align_2d_com": {
                        "do_align": False,
                        "x_start": -5,
                        "x_end": 5,
                        "x_num": 50,
                        "y_start": -2,
                        "y_end": 2,
                        "y_num": 20,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "threshold": 0.5,
                        "move_x": True,
                        "move_y": True,
                        "x_offset": -0.95,
                        "y_offset": -0.2,
                        "zero_before_scan": False
                    },

                    "stop_iter":False,
                    "add_angles":[ ],
                    "remove_angles":[-90,-91],
                    "stop_pdf":False,
                    "pdf_elems":["Au_L", "Pt_L"],
                    "pause_scan":False,
                    "test":False,
                    "ic_threshold":0.9,
                    "scan_label":"HXN_Tomo_Scan",
                    "Notes": 'My sample # 10'
                }

    with open(save_as,"w") as fp:
            json.dump(diff_scan,fp, indent=6)

    fp.close()


def diff_2d_scan(angle,dets_,fly_motors,x_start,x_end,x_num,y_start,y_end,y_num,exp, 
                     diff_use_panda = False):
    
    '''
    fly_motors = [dssx,dssy,dssz]
    fly_motors = [zpssx,zpssy,zpssz]
    '''



    if not diff_use_panda:
        yield from fly2d(dets_,
                        fly_motors[0],
                        x_start,
                        x_end,
                        x_num,
                        fly_motors[1],
                        y_start,
                        y_end,
                        y_num,
                        exp
                        )
    else:
        yield from fly2dpd(dets_,
                        fly_motors[0],
                        x_start,
                        x_end,
                        x_num,
                        fly_motors[1],
                        y_start,
                        y_end,
                        y_num,
                        exp,
                        position_supersample = 10
                        )

def diff_scan_to_loop(angle, diff_params, ic_init,tracking_file = None):

        #caput("XF:03IDC-ES{Merlin:2}HDF1:NDArrayPort","ROI1") #patch for merlin2 issuee

        #get parameters from json
        xalign = diff_params["xalign"]
        yalign = diff_params["yalign"]
        align_2d = diff_params["align_2d_com"]
        image_scan = diff_params["fly2d_scan"]
        dets = eval(image_scan["det"])
        elems_to_pdf = diff_params["pdf_elems"]
        fly_motors= [eval(item) for item in diff_params["fly_motors"]]


        # yield from bps.mov(eval(diff_params["th_motor"]), angle)

        # #yield from bps.mov(dssx,0,dssz,0)
        # print(f'{diff_params["flying_panda"] = }')
        # #1d alignment sequence, based on angle x or z will be scanned
        

        # if xalign["do_align"]:
        #     yield from align_scan(fly_motors[0],
        #                     xalign["start"],
        #                     xalign["end"],
        #                     xalign["num"],
        #                     xalign["exposure"],
        #                     xalign["elem"],
        #                     xalign["center_with"],
        #                     xalign["threshold"],
        #                     xalign["move_coarse"],
        #                     xalign["neg_flag"],
        #                     xalign["offset"],
        #                     diff_params["flying_panda"],
        #                     xalign["zero_before_scan"],
        #                     xalign["initial_position"],
        #                     xalign["align_movement_limit"]
        #                     )

        #     #2d alignemnt using center of mass if condition is true
        # if align_2d["do_align"]:

        #     yield from align_2d_com_scan(   fly_motors[0],
        #                                     align_2d["x_start"],
        #                                     align_2d["x_end"],
        #                                     align_2d["x_num"],
        #                                     fly_motors[1],
        #                                     align_2d["y_start"],
        #                                     align_2d["y_end"],
        #                                     align_2d["y_num"],
        #                                     align_2d["exposure"],
        #                                     align_2d["elem"],
        #                                     align_2d["threshold"],
        #                                     align_2d["move_x"],
        #                                     align_2d["move_y"],
        #                                     align_2d["x_offset"],
        #                                     align_2d["y_offset"],
        #                                     diff_params["flying_panda"])

        # #1d y alignemnt scan
        # if yalign["do_align"]:
        #     yield from align_scan(  fly_motors[1],
        #                             yalign["start"],
        #                             yalign["end"],
        #                             yalign["num"],
        #                             yalign["exposure"],
        #                             yalign["elem"],
        #                             yalign["center_with"],
        #                             yalign["threshold"],
        #                             yalign["move_coarse"],
        #                             xalign["neg_flag"],
        #                             yalign["offset"],
        #                             diff_params["flying_panda"],
        #                             yalign["zero_before_scan"],
        #                             yalign["initial_position"],
        #                             yalign["align_movement_limit"]
        #         )

            
        #     insert_xrf_map_to_pdf(-1,
        #                             elements = elems_to_pdf,
        #                             title_=['energy', diff_params["th_motor"]],
        #                             note = diff_params["scan_label"])
        #     plt.close()


        
        # else:
        #     pass

        #2d scan sequence, based on angle x or z are scanned
        yield from diff_2d_scan(    angle,
                                    dets,
                                    fly_motors,
                                    image_scan["x_start"],
                                    image_scan["x_end"],
                                    image_scan["x_num"],
                                    image_scan["y_start"],
                                    image_scan["y_end"],
                                    image_scan["y_num"],
                                    image_scan["exposure"],
                                    diff_params["flying_panda"]
                                    )

        #save images to pdf if
        if not diff_params["stop_pdf"]:

            try:
                insert_xrf_map_to_pdf(-1,
                                      elements = elems_to_pdf,
                                      title_=['energy', diff_params["th_motor"]],
                                      note = diff_params["scan_label"])
                plt.close()

            except:
                pass
        if tracking_file is not None:
            flog = open(tracking_file,'a')
            flog.write("%d %.3f\n"%(db[-1].start['scan_id'],angle))
            flog.close()


def run_diff_json(path_to_json,tracking_file = None,do_confirm =True):


    """diff_scan by taking parameters from a json file,
    TODO add angles smartly

    """
    beamDumpOccured = False

    #open json file for angle info first
    with open(path_to_json,"r") as fp:
        diff_params = json.load(fp)
    fp.close()
    print("json file loaded")

    #create angle list for iteration
    angle_info = diff_params["angle_info"]
    print(angle_info)
    angles = np.arange(angle_info["start"],
                         angle_info["end"]+(angle_info["angle_step"]/2),
                         angle_info["angle_step"]
                         )
    
    print(f"{angles = }")

    #angles = np.linspace(angle_info["start"],
    #                   angle_info["end"],
    #                    int(1+abs(angle_info["end"] - angle_info["start"])/angle_info["angle_step"])
    #                   )
    if "split_diff" in angle_info:
        split = int(angle_info["split_diff"])
        angles0 = angles.copy()
        angles = angles0[0::split]
        for i in range(1,split):
            angles = np.concatenate((angles,angles0[i::split]))
    if "start_angle" in angle_info:
        angst = angle_info["start_angle"]
        for i,ang in enumerate(angles):
            if np.abs(ang-angst)<1e-3:
                angles = angles[i:]
                break

    angle_list = pd.DataFrame(columns= ['scan_id', 'angle'])

    angle_list["angle"] = angles

    print(angle_list)


    yield from bps.sleep(2)
    fly_motors= [eval(item) for item in diff_params["fly_motors"]]
    th_motor = eval(diff_params["th_motor"])
    
    
    #get some initial parameters
    ic_0 = sclr2_ch2.get()

    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    yield from bps.sleep(2)

    logger.info("Reading IC3 value")

    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates

     #Ic values are useful for calibration

         #add real energy to the dataframe
    angle_list['energy_rbv'] = np.nan
    #add scan_id to the dataframe
    angle_list['scan_id'] = np.nan
    #record time
    angle_list['TimeStamp'] = pd.Timestamp.now()
    #record if peak beam happed before the scan
    angle_list['Peak Flux'] = False
    angle_list['IC3'] = ic_3_init
    angle_list['IC0'] = ic_0
    angle_list[fly_motors[1].name] = np.nan
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)


    #set the pause and stop inter keys to False before the loop
    #to reverse the abort scan and pause when using the gui
    diff_params["stop_iter"] = False
    diff_params["pause_scan"] = False

    with open(path_to_json,"w") as fp:
            json.dump(diff_params,fp, indent=6)

    fp.close()
    
    fluxPeaked = False
    image_scan_i = diff_params["fly2d_scan"]

    tot_time_ = (image_scan_i["x_num"]*image_scan_i["y_num"]*image_scan_i["exposure"]*len(angle_list))
    tot_time = tot_time_/3600
    overhead = 1.2
    end_datetime = time.ctime(time.time()+tot_time_*overhead)
    
    if do_confirm:
        check = 'n'
        check = input(f"This plan takes about {tot_time*overhead :.1f} hours,"
                    f"Projected to {end_datetime} continue (y/n)?")
    else:
        check = 'y'
    
    if check == "y":

        #loop with list of angles
        for n,angle in enumerate(tqdm.tqdm(angles,desc = 'diff Scan')):
            print(f"{angle = }")
            yield from bps.sleep(1)

            #open the json file to catch any updates
            with open(path_to_json,"r") as fp:
                diff_params = json.load(fp)
                fp.close()

            #stop data collection if necessary.user input taken
            if diff_params["stop_iter"]:
                save_page()
                break

            #get parameters from json
            xalign = diff_params["xalign"]
            yalign = diff_params["yalign"]
            align_2d = diff_params["align_2d_com"]
            image_scan = diff_params["fly2d_scan"]
            dets = eval(image_scan["det"])
            elems_to_pdf = diff_params["pdf_elems"]
            fly_motors= [eval(item) for item in diff_params["fly_motors"]]


            yield from bps.mov(eval(diff_params["th_motor"]), angle)

            #yield from bps.mov(dssx,0,dssz,0)
            print(f'{diff_params["flying_panda"] = }')
            #1d alignment sequence, based on angle x or z will be scanned
            

            if xalign["do_align"]:
                yield from align_scan(fly_motors[0],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                diff_params["flying_panda"],
                                xalign["zero_before_scan"],
                                xalign["initial_position"],
                                xalign["align_movement_limit"]
                                )

                #2d alignemnt using center of mass if condition is true
            if align_2d["do_align"]:

                yield from align_2d_com_scan(   fly_motors[0],
                                                align_2d["x_start"],
                                                align_2d["x_end"],
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                diff_params["flying_panda"])

            #1d y alignemnt scan
            if yalign["do_align"]:
                yield from align_scan(  fly_motors[1],
                                        yalign["start"],
                                        yalign["end"],
                                        yalign["num"],
                                        yalign["exposure"],
                                        yalign["elem"],
                                        yalign["center_with"],
                                        yalign["threshold"],
                                        yalign["move_coarse"],
                                        xalign["neg_flag"],
                                        yalign["offset"],
                                        diff_params["flying_panda"],
                                        yalign["zero_before_scan"],
                                        yalign["initial_position"],
                                        yalign["align_movement_limit"]
                    )

                
                # insert_xrf_map_to_pdf(-1,
                #                         elements = elems_to_pdf,
                #                         title_=['energy', diff_params["th_motor"]],
                #                         note = diff_params["scan_label"])
                plt.close()


            
            else:
                pass


            yield from bps.sleep(5)
            while diff_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_json,"r") as fp:
                    diff_params = json.load(fp)
                    fp.close()

                if not diff_params["pause_scan"]:
                    break

            if diff_params["remove_angles"]==None:
                diff_params["remove_angles"] = []

            if not diff_params["test"]:
                if sclr2_ch2.get()<1000:
                    beamDumpOccured = True
                    yield from check_for_beam_dump()


                if beamDumpOccured:
                    angle = angles[n-1]
                    yield from bps.sleep(60)
                    yield from recover_from_beamdump()
                    beamDumpOccured = False

            #look for beam dump and ic3 threshold, ignores for code tests using json
            if not diff_params["test"]:
                #opening fast shutter for initial ic3 reading
                caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
                yield from bps.sleep(2)
                if (sclr2_ch4.get() < (diff_params["ic_threshold"]*ic_3_init)):
                    yield from peak_the_flux()
                    ic_0 = sclr2_ch2.get()
                    fluxPeaked = True

            if not angle in np.array(diff_params["remove_angles"]):
                #diff scan at a single angle
                yield from diff_scan_to_loop(angle,diff_params,ic_0,tracking_file = tracking_file)

                last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

                #Add more info to the dataframe
                angle_list['energy_rbv'].at[n] = e.position #add real energy to the dataframe
                angle_list["angle"].at[n] = th_motor.position
                angle_list['scan_id'].at[n] = int(last_sid) #add scan_id to the dataframe
                angle_list['TimeStamp'].at[n] = pd.Timestamp.now()
                ic_3 = sclr2_ch4.get()
                ic_0 = sclr2_ch2.get()
                angle_list['IC3'].at[n] = ic_3 #Ic values are useful for calibration
                angle_list['IC0'].at[n] = ic_0 #Ic values are useful for calibration
                angle_list['Peak Flux'].at[n] = fluxPeaked # recoed if peakflux was excecuted
                #angle_list['IC3_before_peak'].at[n] = ic3 #ic3 right after e change, no peaking
                fluxPeaked = False #reset
                angle_list[fly_motors[1].name].at[n] = fly_motors[1].position
                
                #close c shutter
                caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

                # save the DF in the loop so quitting a scan won't affect
                filename = f"{diff_params.get('scan_label','')}_startID{int(angle_list['scan_id'][0])}.csv"
                angle_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                                float_format= '%.5f')
            else:
                print(f"{angle} skipped")
                pass


        #TODO add angles to scan; need to be better
        #sort based on what current angle is
        if not diff_params["add_angles"]==None:

            added_angles = diff_params["add_angles"]

            for nn,angle in enumerate(tqdm.tqdm(added_angles,desc = 'diff Scan; Additional Angles')):

                #open the json file to catch any updates
                with open(path_to_json,"r") as fp:
                    diff_params = json.load(fp)
                    fp.close()

                #stop data collection if necessary.user input taken
                if diff_params["stop_iter"]:
                    save_page()
                    break

                while diff_params["pause_scan"]:
                    yield from bps.sleep(10) #check if this freezes the gui or not
                    with open(path_to_json,"r") as fp:
                        diff_params = json.load(fp)
                        fp.close()

                    if not diff_params["pause_scan"]:
                        break

                if not angle in np.array(diff_params["remove_angles"]):
                    yield from diff_scan_to_loop(angle, diff_params,ic_0)

                    last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

                    #Add more info to the dataframe
                    angle_list['energy_rbv'].at[n] = e.position #add real energy to the dataframe
                    angle_list["angle"].at[n] = th_motor.position
                    angle_list['scan_id'].at[n] = int(last_sid) #add scan_id to the dataframe
                    angle_list['TimeStamp'].at[n] = pd.Timestamp.now()
                    ic_3 = sclr2_ch4.get()
                    ic_0 = sclr2_ch2.get()
                    angle_list['IC3'].at[n] = ic_3 #Ic values are useful for calibration
                    angle_list['IC0'].at[n] = ic_0 #Ic values are useful for calibration
                    angle_list['Peak Flux'].at[n] = fluxPeaked # recoed if peakflux was excecuted
                    #angle_list['IC3_before_peak'].at[n] = ic3 #ic3 right after e change, no peaking
                    fluxPeaked = False #reset
                    angle_list[fly_motors[1].name].at[n] = fly_motors[1].position

                    # save the DF in the loop so quitting a scan won't affect
                    filename = f"hxn_zp_diff_{diff_params.get('scan_label','')}_startID{int(angle_list['scan_id'][0])}.csv"
                    angle_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                                    float_format= '%.5f')

                else:
                    print(f"{angle} skipped")
                    pass

        else:
            pass

        #go back to the initial angle    
        yield from bps.mov(eval(diff_params["th_motor"]), angles[0])

        #save pdf
        save_page()




def run_repeat_2d_json(path_to_json, n_repeat=10, tracking_file=None, do_confirm=True):
    """
    Perform repeated diffraction scans (n_repeat times) at a single angle using
    parameters from a JSON file, including x/y/2D alignment scans before each run.

    Example:
        RE(run_diff_json_repeat('/path/to/diff_params.json', n_repeat=10))
    """
    beamDumpOccured = False
    fluxPeaked = False

    # Load JSON
    with open(path_to_json, "r") as fp:
        diff_params = json.load(fp)
    print("json file loaded")

    # Motors and detectors
    fly_motors = [eval(item) for item in diff_params["fly_motors"]]
    th_motor = eval(diff_params["th_motor"])

    # Determine scan angle
    if "angle_info" in diff_params and "start" in diff_params["angle_info"]:
        scan_angle = diff_params["angle_info"]["start"]
    else:
        scan_angle = th_motor.position

    # Initial IC readings
    ic_0 = sclr2_ch2.get()
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 1)
    yield from bps.sleep(2)
    ic_3_init = sclr2_ch4.get()
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 0)

    # Create DataFrame
    repeat_list = pd.DataFrame(columns=['scan_id', 'iteration', 'energy_rbv', 'IC3', 'IC0',
                                        'Peak Flux', 'TimeStamp', fly_motors[1].name])
    repeat_list['iteration'] = np.arange(1, n_repeat + 1)

    # Estimate time
    image_scan_i = diff_params["fly2d_scan"]
    tot_time_ = (image_scan_i["x_num"] * image_scan_i["y_num"] *
                 image_scan_i["exposure"] * n_repeat)
    tot_time = tot_time_ / 3600
    overhead = 1.2
    end_datetime = time.ctime(time.time() + tot_time_ * overhead)

    if do_confirm:
        check = input(f"This plan will take about {tot_time*overhead:.1f} hours, "
                      f"projected to finish {end_datetime}. Continue (y/n)? ")
    else:
        check = 'y'

    if check.lower() != 'y':
        print("Scan aborted by user.")
        return

    print(f"Running {n_repeat} repeated scans at angle = {scan_angle:.3f}")

    # Set pause/stop flags
    diff_params["stop_iter"] = False
    diff_params["pause_scan"] = False
    with open(path_to_json, "w") as fp:
        json.dump(diff_params, fp, indent=6)

    for n in range(n_repeat):
        print(f"=== Scan {n+1}/{n_repeat} ===")

        # Re-read JSON in case user edited mid-scan
        with open(path_to_json, "r") as fp:
            diff_params = json.load(fp)

        # stop/pause logic
        if diff_params.get("stop_iter", False):
            save_page()
            print("Scan stopped by user.")
            break

        while diff_params.get("pause_scan", False):
            yield from bps.sleep(5)
            with open(path_to_json, "r") as fp:
                diff_params = json.load(fp)

        # Move to scan angle
        yield from bps.mov(th_motor, scan_angle)

        # --- Alignment Scans ---
        xalign = diff_params["xalign"]
        yalign = diff_params["yalign"]
        align_2d = diff_params["align_2d_com"]

        # X alignment
        if xalign["do_align"]:
            yield from align_scan(
                fly_motors[0],
                xalign["start"], xalign["end"], xalign["num"],
                xalign["exposure"], xalign["elem"], xalign["center_with"],
                xalign["threshold"], xalign["move_coarse"], xalign["neg_flag"],
                xalign["offset"], diff_params["flying_panda"],
                xalign["zero_before_scan"], xalign["initial_position"],
                xalign["align_movement_limit"]
            )

        # 2D alignment
        if align_2d["do_align"]:
            yield from align_2d_com_scan(
                fly_motors[0],
                align_2d["x_start"], align_2d["x_end"], align_2d["x_num"],
                fly_motors[1],
                align_2d["y_start"], align_2d["y_end"], align_2d["y_num"],
                align_2d["exposure"], align_2d["elem"], align_2d["threshold"],
                align_2d["move_x"], align_2d["move_y"],
                align_2d["x_offset"], align_2d["y_offset"],
                diff_params["flying_panda"]
            )

        # Y alignment
        if yalign["do_align"]:
            yield from align_scan(
                fly_motors[1],
                yalign["start"], yalign["end"], yalign["num"],
                yalign["exposure"], yalign["elem"], yalign["center_with"],
                yalign["threshold"], yalign["move_coarse"], yalign["neg_flag"],
                yalign["offset"], diff_params["flying_panda"],
                yalign["zero_before_scan"], yalign["initial_position"],
                yalign["align_movement_limit"]
            )

        yield from bps.sleep(2)

        # --- Beam Check and Flux Peaking ---
        if not diff_params["test"]:
            if sclr2_ch2.get() < 1000:
                beamDumpOccured = True
                yield from check_for_beam_dump()

            if beamDumpOccured:
                yield from bps.sleep(60)
                yield from recover_from_beamdump()
                beamDumpOccured = False

            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 1)
            yield from bps.sleep(2)
            if (sclr2_ch4.get() < (diff_params["ic_threshold"] * ic_3_init)):
                yield from peak_the_flux()
                ic_0 = sclr2_ch2.get()
                fluxPeaked = True
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 0)

        # --- Run Diffraction Scan ---
        yield from diff_scan_to_loop(scan_angle, diff_params, ic_0, tracking_file=tracking_file)

        # --- Record Results ---
        last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
        repeat_list.at[n, 'scan_id'] = last_sid
        repeat_list.at[n, 'energy_rbv'] = e.position
        repeat_list.at[n, 'IC3'] = sclr2_ch4.get()
        repeat_list.at[n, 'IC0'] = sclr2_ch2.get()
        repeat_list.at[n, 'Peak Flux'] = fluxPeaked
        repeat_list.at[n, 'TimeStamp'] = pd.Timestamp.now()
        repeat_list.at[n, fly_motors[1].name] = fly_motors[1].position
        fluxPeaked = False

        # Save after each repeat
        filename = f"{diff_params.get('scan_label','repeat_diff')}_n{n_repeat}_startID{int(repeat_list['scan_id'][0])}.csv"
        repeat_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                           float_format='%.5f')

        print(f"Repeat scan {n+1}/{n_repeat} done and logged.")

    # Final save
    save_page()
    print("All repeated scans completed successfully.")
