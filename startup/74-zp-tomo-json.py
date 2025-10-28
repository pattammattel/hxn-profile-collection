print(f"Loading {__file__!r} ...")


def make_zp_tomo_plan(save_as = "/nsls2/data/hxn/legacy/user_macros/HXN_GUI/Scan/temp_files/zp_tomo_params.json" ):

    zp_tomo_scan = {   
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

                    "xalign":{"do_align":True,
                            "start":-2,
                            "end": 2,
                            "num": 100,
                            "exposure": 0.03,
                            "elem": "Fe",
                            "center_with":"line_center",
                            "threshold": 0.5,
                            "move_coarse":False,
                            "negative_flag":False},
                    
                    "yalign":{"do_align":True,
                            "start":-2,
                            "end": 2,
                            "num": 100,
                            "exposure": 0.03,
                            "elem": "Fe",
                            "center_with":"line_center",
                            "threshold": 0.5,
                            "move_coarse":False,
                            "negative_flag":True},

                    "align_2d_com":{"do_align":False,
                            "x_start":-2,
                            "x_end": 2,
                            "x_num": 100,
                            "y_start":-2,
                            "y_end": 2,
                            "y_num": 100,
                            "exposure": 0.03,
                            "elem": "Fe",
                            "threshold": 0.5,
                            "move_x":True,
                            "move_y":True},
                    
                    "stop_iter":False,
                    "add_angles":[91,92],
                    "remove_angles":[-90,-91],
                    "pdf_elems":["Fe","Ni","Cr"],
                    "stop_pdf":False,
                    "pause_scan":False,
                    "test":False,
                    "ic_threshold":0.9,
                    "scan_label":"HXN_Tomo_Scan",
                    "save_log_to":"/data/users/current_user/"

                }


    with open(save_as,"w") as fp:
            json.dump(zp_tomo_scan,fp, indent=6)

    fp.close()

def zp_tomo_2d_scan_loop(angle,dets_,x_start,x_end,x_num,y_start,y_end,y_num,exp,add_low_res_scan=False):
    print("zp tomo 2d scan")
    print(f"exposure time = {exp}")
    
    from hxntools.motor_info import motor_table

    # x_scale_factor = 0.9542
    # z_scale_factor = 1.0309

    x_scale_factor = 1
    z_scale_factor = 1

    if np.abs(angle) < 44.99:
                
        x_start_real = x_start / np.cos(angle * np.pi / 180.)/ x_scale_factor
        x_end_real = x_end / np.cos(angle * np.pi / 180.)/ x_scale_factor

        yield from fly2dpd(dets_, 
                        zpssx,
                        x_start_real,
                        x_end_real,
                        x_num,
                        zpssy,
                        y_start, 
                        y_end, 
                        y_num, 
                        exp
                        )
        
        if add_low_res_scan:

            yield from fly2dpd(dets_, 
                        zpssx,
                        x_start_real,
                        x_end_real,
                        x_num//4,
                        zpssy,
                        y_start, 
                        y_end, 
                        y_num//4, 
                        exp
                        )

    else:

        x_start_real = x_start / np.abs(np.sin(angle * np.pi / 180.))/ z_scale_factor
        x_end_real = x_end / np.abs(np.sin(angle * np.pi / 180.))/ z_scale_factor
        print(x_start_real,x_end_real)

        yield from fly2dpd(dets_, 
                        zpssz,
                        x_start_real,
                        x_end_real,
                        x_num,
                        zpssy,
                        y_start, 
                        y_end, 
                        y_num, 
                        exp
                        )
        
        if add_low_res_scan:
            yield from fly2dpd(dets_, 
                        zpssz,
                        x_start_real,
                        x_end_real,
                        x_num//4,
                        zpssy,
                        y_start, 
                        y_end, 
                        y_num//4, 
                        exp
                        )
            


def zp_tomo_scan_to_loop(angle, tomo_params, ic_init,tracking_file = None,add_low_res_scan=False):

        #caput("XF:03IDC-ES{Merlin:2}HDF1:NDArrayPort","ROI1") #patch for merlin2 issuee
        
        #get parameters from json
        xalign = tomo_params["xalign"]
        yalign = tomo_params["yalign"]
        align_2d = tomo_params["align_2d_com"]
        image_scan = tomo_params["fly2d_scan"]
        dets = eval(image_scan["det"])
        elems_to_pdf = tomo_params["pdf_elems"]

        yield from bps.mov(zpsth, angle)
        
        #look for beam dump and ic3 threshold, ignores for code tests using json
        if not tomo_params["test"]:
       
            yield from check_for_beam_dump()

            while (sclr2_ch2.get() < (tomo_params["ic_threshold"]*ic_init)):
                 yield from peak_the_flux()
                 ic_0 = sclr2_ch2.get()
        
        #yield from bps.mov(zpssx,0,zpssz,0)

        #1d alignment sequence, based on angle x or z will be scanned
        if np.abs(angle) < 44.99:

            if xalign["do_align"]:
                try:
                    move_coarse = xalign["move_coarse"]
                except:
                    move_coarse = False
                yield from align_scan(zpssx, 
                                xalign["start"], 
                                xalign["end"], 
                                xalign["num"], 
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                move_coarse = move_coarse,
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:

                x_start_real = align_2d["x_start"] / np.cos(angle * np.pi / 180.)
                x_end_real = align_2d["x_end"] / np.cos(angle * np.pi / 180.)


                yield from align_2d_com_scan(zpssx,
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                zpssy,
                                                align_2d["y_start"], 
                                                align_2d["y_end"], 
                                                align_2d["y_num"], 
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],)

            else:
                pass
            
        else:

            if xalign["do_align"]:
                try:
                    move_coarse = xalign["move_coarse"]
                except:
                    move_coarse = False
                yield from align_scan(zpssz, 
                                xalign["start"], 
                                xalign["end"], 
                                xalign["num"], 
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                move_coarse = move_coarse,
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:
                
                x_start_real = align_2d["x_start"] / np.abs(np.sin(angle * np.pi / 180.))
                x_end_real = align_2d["x_end"] / np.abs(np.sin(angle * np.pi / 180.))

                yield from align_2d_com_scan(zpssz,
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                zpssy,
                                                align_2d["y_start"], 
                                                align_2d["y_end"], 
                                                align_2d["y_num"], 
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"]
                                                )
            else:
                pass
        
        #1d y alignemnt scan
        try:
            move_coarse = yalign["move_coarse"]
        except:
            move_coarse = False
        if yalign["do_align"]:
            yield from align_scan(zpssy, 
                                yalign["start"], 
                                yalign["end"], 
                                yalign["num"], 
                                yalign["exposure"],
                                yalign["elem"],
                                yalign["center_with"],
                                yalign["threshold"],
                                move_coarse = move_coarse,
                )
            
        else:
            pass

        #2d scan sequence, based on angle x or z are scanned
        yield from zp_tomo_2d_scan_loop(angle,
                                    dets,
                                    image_scan["x_start"],
                                    image_scan["x_end"],
                                    image_scan["x_num"],
                                    image_scan["y_start"],
                                    image_scan["y_end"],
                                    image_scan["y_num"],
                                    image_scan["exposure"],
                                    add_low_res_scan
                                    )

        xspress3.unstage()

        #save images to pdf if
        if not tomo_params["stop_pdf"]:

            try:
                insert_xrf_map_to_pdf(-1,
                                     elems_to_pdf,
                                     title_ =  ["zpsth", "energy"], 
                                     note = tomo_params["scan_label"])
                plt.close()
                
            except:
                traceback.print_exc()
                pass

        if tracking_file is not None:
            flog = open(tracking_file,'a')
            if not add_low_res_scan:
                flog.write("%d %.3f\n"%(db[-1].start['scan_id'],angle))
            else:
                flog.write("%d %.3f\n"%(db[-2].start['scan_id'],angle))
            flog.close()
                
def run_zp_tomo_json(path_to_json,tracking_file = None,add_low_res_scan = False):


    """zp_tomo_scan by taking parameters from a json file,
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
            if i%2 == 0:
                angles = np.concatenate((angles,angles0[i::split]))
            else:
                angles = np.concatenate((angles,np.flip(angles0[i::split])))
    if "start_angle" in angle_info:
        angst = angle_info["start_angle"]
        for i,ang in enumerate(angles):
            if np.abs(ang-angst)<1e-3:
                angles = angles[i:]
                break

    print(angles)

    angle_list = pd.DataFrame()

    angle_list["angles"] = angles

    #add real energy to the dataframe
    angle_list['E Readback'] = np.nan 
    
    #add scan id to the dataframe
    angle_list['Scan ID'] = np.nan 
    
    #recoed time
    angle_list['TimeStamp'] = pd.Timestamp.now()
    
    
    #record if peak beam happed before the scan   
    angle_list['Peak Flux'] = False 
    
    yield from bps.sleep(6)
    


    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
    yield from bps.sleep(5)

    logger.info("Reading IC3 value")
    
    #get some initial parameters 
    ic_0 = sclr2_ch2.get()
    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates 

         #Ic values are useful for calibration
    angle_list['IC3'] = ic_3_init
    angle_list['IC0'] = sclr2_ch2.get()
    angle_list['IC3_before_peak'] = ic_3_init
    angle_list["zpsth"] = np.nan

    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

    #set the pause and stop inter keys to False before the loop
    #to reverse the abort scan and pause when using the gui
    tomo_params["stop_iter"] = False
    tomo_params["pause_scan"] = False

    with open(path_to_json,"w") as fp:
            json.dump(tomo_params,fp, indent=6)

    fp.close()


    #loop with list of angles
    for n,angle in enumerate(tqdm.tqdm(angles,desc = 'ZP Tomo Scan')):
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
            
        if sclr2_ch2.get()<1000:
            beamDumpOccured = True
            yield from check_for_beam_dump()
            
            
        if beamDumpOccured:
            angle = angles[n-1]
            yield from bps.sleep(60)
            yield from recover_from_beamdump()
            beamDumpOccured = False

        if not angle in np.array(tomo_params["remove_angles"]):
            print(f"{angle = } ")
            #tomo scan at a single angle
            yield from zp_tomo_scan_to_loop(angle, tomo_params,ic_0,tracking_file=tracking_file, add_low_res_scan=add_low_res_scan)

        else:
            print(f"{angle = } skipped")
            pass

        
    #TODO add angles to scan; need to be better
    #sort based on what current angle is
    if not tomo_params["add_angles"]==None:
    
        added_angles = tomo_params["add_angles"]
        
        for angle in tqdm.tqdm(added_angles,desc = 'ZP Tomo Scan; Additional Angles'):
            
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
                yield from zp_tomo_scan_to_loop(angle, tomo_params,ic_0,add_low_res_scan=add_low_res_scan)

            else:
                print(f"{angle} skipped")
                pass

    else:
        pass

    #save pdf
    save_page()

