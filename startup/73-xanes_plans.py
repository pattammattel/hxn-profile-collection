print(f"Loading {__file__!r} ...")


import numpy as np
import pandas as pd
import time,json,math
from datetime import datetime
import scipy.constants as consts
import traceback


#Paramer list from previous runs in the order of atomic number of the element

CrXANES = {'high_e':6.0, 'high_e_zpz1':10.48, 'zpz1_slope':-5.04,
          'energy':[(5.97,5.98,0.005),(5.981,6.03,0.001), (6.032,6.046,0.005)] }
          
MnXANES = {'high_e':6.6, 'high_e_zpz1':9.31, 'zpz1_slope':-5.04,
          'energy':[(6.510,6.530,0.005),(6.531,6.570,0.001),(6.575,6.600,0.0075)]}
               
FeXANES = {'high_e':7.2, 'high_e_zpz1':6.41, 'zpz1_slope':-5.04,
          'energy':[(7.09,7.105,0.005),(7.106,7.141,0.001),(7.14,7.18,0.005)],}
          
CoXANES = {'high_e':7.8, 'high_e_zpz1':3.197, 'zpz1_slope':-5.04,          
            'energy':[(7.690,7.705,0.005),(7.706,7.760,0.001),(7.765,7.800,0.005)],}

#CoXANES = {'high_e':7.8, 'high_e_zpz1':3.2725, 'zpz1_slope':-5.04,
#         'energy':[(7.736,7.760,0.001),(7.765,7.800,0.005)],}


NiXANES = {'high_e':8.300, 'high_e_zpz1':0.98, 'zpz1_slope':-5.04,
          'energy':[(8.30,8.325,0.005),(8.326,8.360,0.001),(8.360,8.430,0.006)],}

CuXANES = {'high_e':9.05,  'high_e_zpz1':-2.735, 'zpz1_slope':-5.04,
          'energy':[(8.950,8.975,0.005),(8.976,9.005,0.001),(9.009,9.033,0.004)],}

ZnXANES =  {'high_e':9.7, 'high_e_zpz1':-6.25, 'zpz1_slope':-5.04,
          'energy':[(9.620,9.650,0.005),(9.651,9.700,.001),(9.705,9.725,0.005)]}
          
HfXANES =  {'high_e':9.6, 'high_e_zpz1':-7.775, 'zpz1_slope':-5.04,
          'energy':[(9.500,9.540,0.005),(9.541,9.6,0.001)]}

LuL3XANES =  {'high_e':9.3, 'high_e_zpz1':-5.4246, 'zpz1_slope':-5.04,
          'energy':[(9.150,9.200,0.005),(9.201,9.350,0.001),(9.352,9.400,0.002)]}
          
TaXANES = {"high_e":9.95, 
            "high_e_zpz1":-15.05, 
            "zpz1_slope":-5.04,
            "energy":[(9.84,9.87,0.005),(9.871,9.900,0.001),(9.904,9.950,0.004)]}

          
          
As_MLL_XANES = {'high_e':11.94, 
                'low_e':11.84,
                'high_e_hmll_z':0,
                'high_e_sbz':0,
                'low_e_hmll_z':9,
                'low_e_sbz':-39,
                'energy':[(11.84,11.86,0.005),
                          (11.861,11.88,0.001),
                          (11.881,11.90,0.002),
                          (11.90,11.94,0.005)]
                          
                }


Hg_MLL_XANES_metacinnabar = {'high_e':12.350, 
                'low_e':12.250,
                'high_e_hmll_z':-129,
                'high_e_sbz':-1.5,
                'low_e_hmll_z':-129+9,
                'low_e_sbz':-1.5-39,
                'energy':[(12.235,12.270,0.005),
                          (12.271,12.314,0.001),
                          (12.315,12.380,0.005),
                          ]
                }

Hg_MLL_XANES_cinnabar = {'high_e':12.350, 
                'low_e':12.250,
                'high_e_hmll_z':-129,
                'high_e_sbz':-26,
                'low_e_hmll_z':-129+9,
                'low_e_sbz':-26-39,
                'energy':[(12.235,12.270,0.005),
                          (12.271,12.314,0.001),
                          (12.315,12.380,0.005),
                          ]
                }

Hg_MLL_XANES_NP = {'high_e':12.350, 
                'low_e':12.250,
                'high_e_hmll_z':-129,
                'high_e_sbz':-15,
                'low_e_hmll_z':-129+9,
                'low_e_sbz':-15-39,
                'energy':[(12.235,12.270,0.005),
                          (12.271,12.314,0.001),
                          (12.315,12.380,0.005),
                          ]
                }

As_MLL_XANES_minE = {'high_e':11.94, 
                'low_e':11.84,
                'high_e_hmll_z':0,
                'high_e_sbz':0,
                'low_e_hmll_z':9,
                'low_e_sbz':-39,
                'energy':[11.84,11.869,11.870,
                          11.872,11.878,11.880,
                          11.905,11.94]
                          
                }


                                ######################################
                                ######### FUNCTIONS BELOW ############
                                ######################################


def cbpm_on(action = True):
    cbpm_x = "XF:03IDC-CT{FbPid:04}PID:on"
    cbpm_y = "XF:03IDC-CT{FbPid:03}PID:on"

    if action:
        caput(cbpm_x,1)
        caput(cbpm_y,1)

        time.sleep(2)
    else:
        caput(cbpm_x,0)
        caput(cbpm_y,0)
        time.sleep(2)

def piezos_to_zero():
    yield from bps.mov(zpssx,0,zpssy,0,zpssz,0)



def move_energy(e,zpz_,harmonic = -1):

    yield from Energy.move(e, 
                           harmChoice=harmonic,
                           moveMonoPitch=False, 
                           moveMirror = "ignore")
    yield from mov_zpz1(zpz_)
    yield from bps.sleep(2)

    #cbpm_on(True)

def move_energy_mll(e, hmll_z = 0,vmll_z=0, harmonic = -1):

    yield from Energy.move(e, 
                           harmChoice=harmonic,
                           moveMonoPitch=False, 
                           moveMirror = "ignore")

    vmll_pos_ = hmll.hz.position
    if abs(vmll_z- vmll_pos_)>1:
        yield from bps.mov(vmll.vz,np.round(vmll_z,1))

    hmll_hz_pos = hmll.hz.position
    if abs(hmll_z-hmll_hz_pos)>1:
        yield from bps.mov(hmll.hz,np.round(hmll_z,1))

    else:
        pass



def alignment_scan(mtr, start,end,num,exp,elem_, align_with="line_center", 
                   threshold = 0.5, move_coarse = False, neg_flag = False, offset = 0):

    """
    scan to align samples to field of view using using fly1d scan 

    mtr--> scanning motor, dssx, dssy, dssz etc.
    start,end,num,exp --> flyscan paramters
    elem_ --> element to use for alignemnt
    align_with --> choose bettween "edge" or "line_center"
    threshold --> threshold for line centering
    
    """
    
    fly_to_coarse = {"zpssx":"smarx","zpssy":"smary","zpssz":"smarz"}



        # yield from fly1d(dets_fs,
        #                 mtr, 
        #                 start, 
        #                 end, 
        #                 num,
        #                 exp
        #                 )

    yield from fly1dpd([fs,xspress3],
            mtr,
            start,
            end,
            num,
            exp
            )
    if align_with == "line_center":
        xc = return_line_center(-1,elem_,threshold, neg_flag= neg_flag)

    elif align_with == "edge":
        xc,_ = erf_fit(-1,elem_,linear_flag=False)

    else:
        raise KeyError(f"{align_with}  is not defined")
    print(f"{mtr.name} centered to {xc :.2f}")

    xc += offset
    
    if move_coarse:
        yield from piezos_to_zero()
        yield from bps.movr(eval(fly_to_coarse[mtr.name]),xc)
        
    else:
        yield from bps.mov(mtr,xc)

    plt.close()



                        

def generateEPoints(ePointsGen = [(9.645,9.665,0.005),(9.666,9.7,0.0006),(9.705,9.725,0.005)],reversed = True):

    """

    Generates a list of energy values from the given list

    input: Tuples in the format (start energy, end energy, energy resolution),
    if reversed is true the list will be transposed

    return : list of energy points

    """

    e_points = []

    if isinstance(ePointsGen[0], tuple) or isinstance(ePointsGen[0], list):

        for values in ePointsGen:
            #use np.arange to generate values and extend it to the e_points list
            e_points.extend(np.arange(values[0],values[1],values[2]))

    elif isinstance(ePointsGen, list):
        e_points = ePointsGen

    else:
        raise TypeError("Invalid energy format")

    if reversed:
        #retrun list in the reversted order
        return e_points[::-1]
    else:
        return e_points                 
                        
                        
def generateEList(XANESParam = CrXANES, highEStart = True):

    """

    Generates a pandas dataframe of optics motor positions. Function uses high E and low E values in the dictionary
    to generate motor positions for all the energy points, assuming linear relationship.

    input: Dictionary conating optics values at 2 positions (high E and low E), option to start from high E or low E

    return : Dataframe looks like below;

       energy    ugap  crl_theta  ZP focus
    0   7.175  7652.5       1.75   65.6575
    1   7.170  7648.0       1.30   65.6870
    2   7.165  7643.5       0.85   65.7165
    3   7.160  7639.0       0.40   65.7460
    4   7.155  7634.5      -0.05   65.7755

    """
    # empty dataframe
    e_list = pd.DataFrame()

    #add list of energy as first column to DF
    e_list['energy'] = generateEPoints (ePointsGen = XANESParam ['energy'], reversed = highEStart)

    #read the paramer dictionary and calculate ugap list
    high_e = XANESParam['high_e']

    #zone plate increament is very close to the theorticla value , same step as above for zp focus
    zpz1_ref, zpz1_slope = XANESParam['high_e_zpz1'],XANESParam['zpz1_slope']
    zpz1_list = zpz1_ref + (e_list['energy'] - high_e)*zpz1_slope
    e_list['ZP focus'] = zpz1_list

    #return the dataframe
    return e_list

def generateEList_MLL(XANESParam = As_MLL_XANES, highEStart = False):
    print("generating e_list")

    """

    Generates a pandas dataframe of optics motor positions. Function uses high E and low E values in the dictionary
    to generate motor positions for all the energy points, assuming linear relationship.

    input: Dictionary conating optics values at 2 positions (high E and low E), option to start from high E or low E

    return : Dataframe looks like below;

       energy    ugap  crl_theta  ZP focus
    0   7.175  7652.5       1.75   65.6575
    1   7.170  7648.0       1.30   65.6870
    2   7.165  7643.5       0.85   65.7165
    3   7.160  7639.0       0.40   65.7460
    4   7.155  7634.5      -0.05   65.7755

    """

    #XANESParam = scan_params["elem_params"]
                    
    #e_list = generateEList(elemParam, highEStart =  scan_params["start_from_high_e"])
    #highEStart =  scan_params["start_from_high_e"]


    # empty dataframe
    e_list = pd.DataFrame()

    #add list of energy as first column to DF
    e_list['energy'] = generateEPoints (ePointsGen = XANESParam ['energy'], reversed = highEStart)

    #read the paramer dictionary and calculate ugap list
    high_e = XANESParam['high_e']
    low_e = XANESParam['low_e']

    #lens increament

    high_hmll = XANESParam['high_e_hmll_z']
    high_sbz = XANESParam['high_e_sbz']
    low_hmll = XANESParam['low_e_hmll_z']
    low_sbz = XANESParam['low_e_sbz']


    hmll_z_slope = (high_hmll-low_hmll)/(high_e-low_e)
    sbz_slope = (high_sbz-low_sbz)/(high_e-low_e)
    print(sbz_slope)


    hmll_list = high_hmll + (e_list['energy'] - high_e)*hmll_z_slope
    sbz_list = high_sbz + (e_list['energy'] - high_e)*sbz_slope
    
    e_list['hmll_hz'] = hmll_list
    e_list['sbz'] = sbz_list


    #return the dataframe
    return e_list                        


def generateEList_MLL_2(path_to_parameter_file, highEStart = False):
    print("generating e_list")

    """

    Generates a pandas dataframe of optics motor positions. Function uses high E and low E values in the dictionary
    to generate motor positions for all the energy points, assuming linear relationship.

    input: Dictionary conating optics values at 2 positions (high E and low E), option to start from high E or low E

    return : Dataframe looks like below;

       energy    ugap  crl_theta  ZP focus
    0   7.175  7652.5       1.75   65.6575
    1   7.170  7648.0       1.30   65.6870
    2   7.165  7643.5       0.85   65.7165
    3   7.160  7639.0       0.40   65.7460
    4   7.155  7634.5      -0.05   65.7755

    """

    with open(path_to_parameter_file,"r") as fp:
        scan_params = json.load(fp)
        fp.close()

    XANESParam = scan_params["elem_params"]
                    
    #e_list = generateEList(elemParam, highEStart =  scan_params["start_from_high_e"])

    # empty dataframe
    e_list = pd.DataFrame()

    #add list of energy as first column to DF
    e_list['energy'] = generateEPoints (ePointsGen = XANESParam ['energy'], reversed = highEStart)

    #read the paramer dictionary and calculate ugap list
    high_e = XANESParam['high_e']
    low_e = XANESParam['high_e']-0.1

    #lens increament

    high_hmll = XANESParam['high_e_hmll_z']
    high_vmll = XANESParam['high_e_vmll_z']
    low_hmll = XANESParam['high_e_hmll_z']+30
    #high_sbz = XANESParam['high_e_sbz']
    #low_sbz = XANESParam['high_e_sbz']-39
    low_vmll = XANESParam['high_e_vmll_z']+39


    hmll_z_slope = (high_hmll-low_hmll)/(high_e-low_e)
    vmll_z_slope = (high_vmll-low_vmll)/(high_e-low_e)
    #sbz_slope = (high_sbz-low_sbz)/(high_e-low_e)
    #print(sbz_slope)


    hmll_list = high_hmll + (e_list['energy'] - high_e)*hmll_z_slope
    vmll_list = high_vmll + (e_list['energy'] - high_e)*vmll_z_slope
    #sbz_list = high_sbz + (e_list['energy'] - high_e)*sbz_slope
    
    e_list['hmll_hz'] = hmll_list
    e_list['vmll_hz'] = vmll_list


    #return the dataframe
    return e_list                        


def run_zp_xanes(path_to_parameter_file, do_confirm  =True, add_low_res_scan = False):

    """ 
    Function to run XANES Scan. 
    
    Arguments:
           1. elemParam: Dictionary -  containg low and high energy optics positions and other useful info 
           2. dets: list - detector system in use
           3. mot1, mot2: EpicsMotors- Motors used for 2D scanning (eg: zpssx, zpssy, etc)
           4. xs,xe,ys,ye: float - scan start and end positions in X&Y directions
           5. x_num,y_num: float - number of steps in X&Y directions
           6. accq_t: float - aquistion (dwell) time for flyscan
           7. highEStart: boolean - if True start the stack with high energies first (Descenting order)
           8. doAlignScan: boolean - if True registration scans will be performed before the 2D scan
           9. xcen, ycen; positions where alignemnt scan would be done. This number updates after each alignment scan
           10. Options for reginstration scans
           11. Options to save XRFs to pdf after each scan
           12. Options to do foil calibration scans
           13. Save important information in CSV format to selected forlder 
           14. The user can turn on and off alignemnt scans
          "start_from_high_e":false,
      "stop_iter": false,
      "pause_scan": false,
      "pdf_log":true,
      "pdf_elems:["Cu"],
      "peak_flux":true,
      "save_log_to":"/data/users/current_user"
    
    """   
    
    print("Creating a look up table; please wait...")

    #load paramfile
    with open(path_to_parameter_file,"r") as fp:
        scan_params = json.load(fp)
        fp.close()
        
    elemParam = scan_params["elem_params"]
    # marker to track beam dump             
    beamDumpOccured = False


                    
    e_list = generateEList(elemParam, 
                           highEStart = True)

    #find energy scan direction
    current_energy = e.position
    if not math.isclose(current_energy,e_list['energy'].to_numpy()[0], abs_tol=0.07):

        print("current energy is below the edge; scanning from low to high")

        e_list = generateEList(elemParam, 
                           highEStart = False)

    else: 
        print("current energy is above the edge; scanning from high to low")
        
        

    #add real energy to the dataframe
    e_list['E Readback'] = np.nan 
    
    #add scan id to the dataframe
    e_list["scan_id"] = np.nan 
    
    #recoed time
    e_list['TimeStamp'] = pd.Timestamp.now()
    
    #record if peak beam happed before the scan   
    e_list['Peak Flux'] = False 
    
    
    yield from bps.sleep(1)#time to quit if anything wrong
    
    #get intal ic1 value
    ic_0 = sclr2_ch2.get()
    
    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
    yield from bps.sleep(5)

    logger.info("Reading IC3 value")
    
    #Ic values are useful for calibration
    e_list['IC3'] = sclr2_ch4.get() 
    e_list['IC0'] = sclr2_ch2.get()
    e_list['IC3_before_peak'] = sclr2_ch4.get()
    e_list["zpsth"] = zpsth.position
    
    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates 
    print(e_list)

    #set harmonic to same through out the series
    curr_harm = Energy.gap(e.position)[-1]

    print(f"{curr_harm = }")

    image_scan_i = scan_params["fly2d_scan"]
    x_motor = eval(image_scan_i["x_motor"])
    y_motor = eval(image_scan_i["y_motor"])

    tot_time_ = (image_scan_i["x_num"]*image_scan_i["y_num"]*image_scan_i["exposure"]*len(e_list))
    tot_time = tot_time_/3600
    overhead = 1.25
    end_datetime = time.ctime(time.time()+tot_time_*overhead)
    
    if do_confirm:
        check = 'n'
        check = input(f"This plan takes about {tot_time*overhead :.1f} hours,"
                    f"Projected to {end_datetime} continue (y/n)?")
    else:
        check = 'y'
        
    if check == "y":

        for i in tqdm.tqdm(range(len(e_list)),desc = 'Energy Scan'):
        #for i in range (len(e_list)):  
        
            print(i/len(e_list))

            #open the json file to catch any updates 
            with open(path_to_parameter_file,"r") as fp:
                scan_params = json.load(fp)
                fp.close()

            while scan_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_parameter_file,"r") as fp:
                    scan_params = json.load(fp)
                    fp.close() 

                if not scan_params["pause_scan"]:   
                    break

            #stop data collection if necessary.user input taken 
            if scan_params["stop_iter"]:
                save_page()
                break

            #if beam dump occur turn the marker on
            if sclr2_ch2.get()<1000:
                beamDumpOccured = True

            #wait if beam dump occured beamdump
            yield from check_for_beam_dump(threshold=5000)
            
            if beamDumpOccured:
                #wait for about 2 minutes for all the feedbacks to kick in
                yield from bps.sleep(120)
                yield from recover_from_beamdump()
                yield from bps.sleep(60)

                #redo the previous energy
                e_t,zpz_t, *others = e_list.iloc[i-1]

                #turn off the beamdump marker
                beamDumpOccured = False
                
            else:
                #unwrap df row for energy change
                e_t,zpz_t, *others = e_list.iloc[i]
            
            yield from move_energy(e_t,zpz_t, harmonic=curr_harm)

            #open fast shutter to check if ic3 reading is satistactory
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
            yield from bps.sleep(5)
            
            #get ic3 value before peaking, e change
            ic3_ = sclr2_ch4.get()
            
            # if ic3 value is below the threshold, peak the beam
            #if ic3_ < ic_3_init*0.9:
            if ic3_ < ic_3_init*scan_params["flux_threshold"]:
                
                if scan_params["peak_flux"]: 
                    yield from bps.movr(smary,-0.040) 
                    yield from peak_the_flux()
                    yield from bps.movr(smary,0.040)                     
                fluxPeaked = True # for df record
            else:
                fluxPeaked = False
            
            #for df
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            
            alignX = scan_params["xalign"]
            alignY = scan_params["yalign"]
            align_com = scan_params["align_with_com"]        

            if e_list['energy'][i]<0: # for special scans if no align elem available
                
                '''
                yield from fly1d(dets,x_motor,-1,1,100,0.1)
                xcen = return_line_center(-1,'Cl',0.7)
                yield from bps.mov(x_motor, xcen)
                yield from fly1d(dets,y_motor,-1,1 ,100,0.1)
                ycen = return_line_center(-1,'Cl',0.7)
                yield from bps.mov(y_motor, ycen)
                '''
                pass

            if (align_com["do_align"] and e_t>align_com["energy_threshold"] and not i==0): 
            # for special scans if no align elem available
                
                try:
                #find com
                    cx,cy = return_center_of_mass(-1,
                                                align_com["elem"],
                                                align_com["com_threshold"]
                                                )
                    

                    #move if true
                    if align_com["move_x"]:
                        yield from bps.mov(x_motor,cx)
                    if align_com["move_y"]:
                        yield from bps.mov(y_motor,cy)

                    print(f"COM correction Applied: {cx = :4f}, {cy = :4f}")

                except:
                    pass

            else:
            
                if alignY["do_align"]:
                    yield from align_scan(  y_motor, 
                                                alignY["start"],
                                                alignY["end"],
                                                alignY["num"],
                                                alignY["exposure"],
                                                alignY["elem"],
                                                align_with=alignY["center_with"], 
                                                threshold = alignY["threshold"],
                                                neg_flag =alignY["negative_flag"],
                                                offset=alignY["offset"]
                                                ) 
                
                if alignX["do_align"]:
                    yield from align_scan(  x_motor, 
                                                alignX["start"],
                                                alignX["end"],
                                                alignX["num"],
                                                alignX["exposure"],
                                                alignX["elem"],
                                                align_with=alignX["center_with"], 
                                                threshold = alignX["threshold"],
                                                neg_flag =alignX["negative_flag"],
                                                offset=alignX["offset"] )                


            # alignment_scan(mtr, start,end,num,exp,elem_, align_with="line_center", threshold = 0.5):
            
                                                                       

            print(f'Current scan: {i+1}/{len(e_list)}')
            image_scan = scan_params["fly2d_scan"]

            yield from fly2dpd( 
                            eval(image_scan['det']),
                            x_motor,
                            image_scan["x_start"],
                            image_scan["x_end"],
                            image_scan["x_num"],
                            y_motor,
                            image_scan["y_start"],
                            image_scan["y_end"],    
                            image_scan["y_num"],
                            image_scan["exposure"]
                            )
            yield from bps.sleep(1)
            #eval(image_scan["det"])
            if add_low_res_scan:
            
                yield from fly2dpd( 
                    eval(image_scan['det']),
                    x_motor,
                    image_scan["x_start"],
                    image_scan["x_end"],
                    image_scan["x_num"]//4,
                    y_motor,
                    image_scan["y_start"],
                    image_scan["y_end"],
                    image_scan["y_num"]//4,
                    image_scan["exposure"]
                    )
                yield from bps.sleep(1)

            #close fast shutter
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
            # get some scan details and add to the list of scan id and energy
            last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
            e_pos = e.position
            
            #Add more info to the dataframe
            e_list['E Readback'].at[i] = e_pos #add real energy to the dataframe
            e_list["zpsth"].at[i] = zpsth.position
            e_list["scan_id"].at[i] = int(last_sid) #add scan id to the dataframe
            e_list['TimeStamp'].at[i] = pd.Timestamp.now()
            e_list['IC3'].at[i] = ic_3 #Ic values are useful for calibration
            e_list['IC0'].at[i] = ic_0 #Ic values are useful for calibration
            e_list['Peak Flux'].at[i] = fluxPeaked # recoed if peakflux was excecuted
            e_list['IC3_before_peak'].at[i] = ic3_ #ic3 right after e change, no peaking
            fluxPeaked = False #reset
            scan_name = scan_params.get("scan_name",'')
            if scan_params["pdf_log"]:
                try:
                    insert_xrf_map_to_pdf(-1,
                                          scan_params["pdf_elems"],
                                          title_=['energy', 'zpsth'],
                                          note =scan_name,
                                          norm = None)# plot data and add to pdf
                    plt.close()
                except:
                    traceback.print_exc()
                    pass
            
            # save the DF in the loop so quitting a scan won't affect
            filename = f"HXN_nanoXANES_{scan_name}_startID{int(e_list['scan_id'][0])}_{len(e_list)}_e_points.csv"
            e_list.to_csv(os.path.join(scan_params["save_log_to"], filename), float_format= '%.5f')

        caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
        if scan_params["pdf_log"]: save_page() #save the pdf

    else:
        return
        
        
def run_mll_xanes(path_to_parameter_file,do_confirm =True):


    """ 
    Function to run XANES Scan. 
    
    Arguments:
           1. elemParam: Dictionary -  containg low and high energy optics positions and other useful info 
           2. dets: list - detector system in use
           3. mot1, mot2: EpicsMotors- Motors used for 2D scanning (eg: zpssx, zpssy, etc)
           4. xs,xe,ys,ye: float - scan start and end positions in X&Y directions
           5. x_num,y_num: float - number of steps in X&Y directions
           6. accq_t: float - aquistion (dwell) time for flyscan
           7. highEStart: boolean - if True start the stack with high energies first (Descenting order)
           8. doAlignScan: boolean - if True registration scans will be performed before the 2D scan
           9. xcen, ycen; positions where alignemnt scan would be done. This number updates after each alignment scan
           10. Options for reginstration scans
           11. Options to save XRFs to pdf after each scan
           12. Options to do foil calibration scans
           13. Save important information in CSV format to selected forlder 
           14. The user can turn on and off alignemnt scans
           
    usage: <run_mll_xanes(As_MLL_XANES,"/data/users/current_user/mll_xanes_2d_as-sid-pristine.json")

    
    
    """ 
    with open(path_to_parameter_file,"r") as fp:
        scan_params = json.load(fp)
        fp.close()

        #remeber the start positions
    image_scan_i = scan_params["fly2d_scan"]
    x_motor = eval(image_scan_i["x_motor"])
    y_motor = eval(image_scan_i["y_motor"])

    #recover the position using a scan numer and do a flyscan to center the particle
    if scan_params["pos_recover_scan_num"]:
        print(f'recovering positions from {scan_params["pos_recover_scan_num"]}')
        extra = scan_params["pos_recover_scan_extra_um"]
        yield from recover_scan_pos_and_find_com(int(scan_params["pos_recover_scan_num"]), 
                                             elem = scan_params["pos_recover_align_elem"], 
                                             fly_scan_plan = [x_motor,
                                                             image_scan_i["x_start"]-extra,
                                                             image_scan_i["x_end"]+extra,
                                                             image_scan_i["x_num"],
                                                             y_motor,
                                                             image_scan_i["y_start"]-extra,
                                                             image_scan_i["y_end"]+extra,
                                                             image_scan_i["y_num"],
                                                             image_scan_i["exposure"]],
                                             com_threshold = 0.1)
        
    
    
    elemParam = scan_params["elem_params"]
    # marker to track beam dump             
    beamDumpOccured = False    
                    
    #e_list = generateEList(elemParam, highEStart =  scan_params["start_from_high_e"])
    e_list = generateEList_MLL_2(path_to_parameter_file, highEStart=True)

    #find energy scan direction
    current_energy = e.position
    if not math.isclose(current_energy,e_list['energy'].to_numpy()[0], abs_tol=0.07):

        print("current energy is below the edge; scanning from low to high")

        e_list = generateEList_MLL_2(path_to_parameter_file, 
                           highEStart = False)

    else: 
        print("current energy is above the edge; scanning from high to low")
        

    # marker to track beam dump             
    beamDumpOccured = False

    #add real energy to the dataframe
    e_list['E Readback'] = np.nan 
    
    #add scan id to the dataframe
    e_list["scan_id"] = np.nan 
    
    #recoed time
    e_list['TimeStamp'] = pd.Timestamp.now()
    
    #Ic values are useful for calibration
    e_list['IC3'] = sclr2_ch4.get() 
    e_list['IC0'] = sclr2_ch2.get()
    e_list['IC3_before_peak'] = sclr2_ch4.get()
    
    
    #record if peak beam happed before the scan   
    e_list['Peak Flux'] = False 
    
    print(e_list)
    yield from bps.sleep(1)#time to quit if anything wrong
    
    #get intal ic1 value
    ic_0 = sclr2_ch2.get()
    
    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
    yield from bps.sleep(2)

    logger.info("Reading IC3 value")
    
    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    


    tot_time_ = (image_scan_i["x_num"]*image_scan_i["y_num"]*image_scan_i["exposure"]*len(e_list))
    tot_time = tot_time_/3600
    overhead = 1.25
    end_datetime = time.ctime(time.time()+tot_time_*overhead)

    if do_confirm:
        check = 'n'
        check = input(f"This plan takes about {tot_time*overhead :.1f} hours,"
                    f"Projected to {end_datetime} continue (y/n)?")
    else:
        check = 'y'
        
    if check == "y":

        for i in tqdm.tqdm(range(len(e_list)),desc = 'Energy Scan'):
            print(f'Current scan: {i+1}/{len(e_list)}')
            #for i in range (len(e_list)):

            with open(path_to_parameter_file,"r") as fp:
                scan_params = json.load(fp)
                fp.close()

            while scan_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_parameter_file,"r") as fp:
                    scan_params = json.load(fp)
                    fp.close() 

                if not scan_params["pause_scan"]:   
                    break

            #stop data collection if necessary.user input taken 
            if scan_params["stop_iter"]:
                save_page()
                break

            #if beam dump occur turn the marker on
            if sclr2_ch2.get()<1000:
                beamDumpOccured = True
                cbpm_on(False)


            #wait if beam dump occured beamdump
            yield from check_for_beam_dump(threshold=1000)
            
            if beamDumpOccured:
                #wait for about 3 minutes for all the feedbacks to kick in
                yield from bps.sleep(120)

                #redo the previous energy
                e_t, hmll_hz_t,vmll_vz_t, *others = e_list.iloc[i-1]

                #turn off the beamdump marker
                beamDumpOccured = False
                
            else:
                #unwrap df row for energy change
                e_t, hmll_hz_t,vmll_vz_t, *others = e_list.iloc[i]
            
            print("energy_change")
            yield from move_energy_mll(e_t,hmll_z = hmll_hz_t,vmll_z = vmll_vz_t)
            print("energy_change done")
            
            #open fast shutter to check if ic3 reading is satistactory
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
            yield from bps.sleep(3)
            #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
            
            #get ic3 value before peaking, e change
            ic3_ = sclr2_ch4.get()
            
            # if ic3 value is below the threshold, peak the beam
            if ic3_ < ic_3_init*0.85:
                
                if scan_params["peak_flux"]: yield from peak_the_flux()
                fluxPeaked = True # for df record
            else:
                fluxPeaked = False
            
            #for df
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            
            alignX = scan_params["xalign"]
            alignY = scan_params["yalign"] 
            align_com = scan_params["align_with_com"]   

            #print("align_scan step")

            if (align_com["do_align"] and e_t>align_com["energy_threshold"] and not i==0): 
            # for special scans if no align elem available
                
                try:
                #find com
                    cx,cy = return_center_of_mass(-1,
                                                align_com["elem"],
                                                align_com["com_threshold"]
                                                )
                    

                    #move if true
                    if align_com["move_x"]:
                        yield from bps.mov(x_motor,cx)
                    if align_com["move_y"]:
                        yield from bps.mov(y_motor,cy)

                    print(f"COM correction Applied: {cx = :4f}, {cy = :4f}")

                except:
                    pass

                

            if alignY["do_align"]:
                yield from align_scan(  y_motor, 
                                            alignY["start"],
                                            alignY["end"],
                                            alignY["num"],
                                            alignY["exposure"],
                                            alignY["elem"],
                                            align_with=alignY["center_with"], 
                                            threshold = alignY["threshold"],
                                            neg_flag =alignY["negative_flag"]
                                            ) 
                
            if alignX["do_align"]:
                yield from align_scan(  x_motor, 
                                            alignX["start"],
                                            alignX["end"],
                                            alignX["num"],
                                            alignX["exposure"],
                                            alignX["elem"],
                                            align_with=alignX["center_with"], 
                                            threshold = alignX["threshold"],
                                            neg_flag =alignX["negative_flag"] )      

            #print(f'Current scan: {i+1}/{len(e_list)}')

            # do the fly2d scan
            #cbpm_on(False)

            image_scan = scan_params["fly2d_scan"]

            if image_scan["det"] == "dets_fs": #for fast xanes scan, no transmission (merlin) in the list

                yield from fly2dpd([fs,xspress3,eiger2], x_motor,x_s,x_e,x_num,y_motor,y_s,y_e,y_num,accq_t) 
                #dead_time = 0.001 for 0.015 dwell

            else:

                image_scan = scan_params["fly2d_scan"]

                yield from fly2dpd( 
                                [fs,xspress3,eiger2],
                                x_motor,
                                image_scan["x_start"],
                                image_scan["x_end"],
                                image_scan["x_num"],
                                y_motor,
                                image_scan["y_start"],
                                image_scan["y_end"],
                                image_scan["y_num"],
                                image_scan["exposure"]
                                )
                yield from bps.sleep(1)


            #close fast shutter
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 

            
            # get some scan details and add to the list of scan id and energy

            last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
            e_pos = e.position
            
            #Add more info to the dataframe
            e_list['E Readback'].at[i] = e_pos #add real energy to the dataframe
            e_list["scan_id"].at[i] = int(last_sid) #add scan id to the dataframe
            e_list['TimeStamp'].at[i] = pd.Timestamp.now()
            e_list['IC3'].at[i] = ic_3 #Ic values are useful for calibration
            e_list['IC0'].at[i] = ic_0 #Ic values are useful for calibration
            e_list['Peak Flux'].at[i] = fluxPeaked # recoed if peakflux was excecuted
            e_list['IC3_before_peak'].at[i] = ic3_ #ic3 right after e change, no peaking
            fluxPeaked = False #reset
            
            if scan_params["pdf_log"]:
                try:
                    insert_xrf_map_to_pdf(-1,pdfElem,title_=['energy', 'sbz', 'hz'])# plot data and add to pdf
                except:
                    pass
            # save the DF in the loop so quitting a scan won't affect
            sample_name = scan_params["sample_name"]
            filename = f"HXN_nanoXANES_{sample_name}_StartID{int(e_list['scan_id'][0])}_{len(e_list)}_e_points.csv"
            e_list.to_csv(os.path.join(scan_params["save_log_to"], filename), float_format= '%.5f')
        '''
        #go back to max energy point if scans done reverese
        max_e_id = e_list['energy'].idxmax()
        e_max, hmll_max,v_mll_max *others = e_list.iloc[max_e_id]
        
        if not np.isclose(e_list['energy'].max(), e.position):
        
            yield from move_energy_mll(e_max,hmll_max,v_mll_max)
            
            yield from peak_the_flux()

        
        else: pass
        '''   
        caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
        if scan_params["pdf_log"]: save_page() #save the pdf

    else:
        return
    
'''

def batch_xanes2():
    yield from run_mll_xanes("/data/users/current_user/mll_xanes_sample5_roi2.json", do_confirm = False)
                             
    yield from recover_scan_pos_and_find_com(298422, 
                                             elem = "Hg_L", 
                                             fly_scan_plan = [dssx,-2,2,50,dssy,-2,2,50,0.1],
                                             com_threshold = 0.7)
    yield from run_mll_xanes("/data/users/current_user/mll_xanes_sample5_roi3.json", 
                             sample_name= "A",
                             do_confirm = False)

                                 
    yield from recover_scan_pos_and_find_com(298423, 
                                             elem = "Hg_L", 
                                             fly_scan_plan = [dssx,-1.5,1.5,50,dssy,-1.5,1.5,50,0.1],
                                             com_threshold = 0.7)
    yield from run_mll_xanes("/data/users/current_user/mll_xanes_sample6_roi1.json", 
                             sample_name= "B",
                             do_confirm = False)
        





def zp_batch_xanes():

    #yield from recover_zp_scan_pos(313235,0,1,0)
    yield from run_zp_xanes("/data/users/current_user/zp_xanes_Cu_MOF_p2.json", 
                             do_confirm = False,add_low_res_scan=True)
    
    yield from recover_zp_scan_pos(313224,0,1,0)
    yield from run_zp_xanes("/data/users/current_user/zp_xanes_Cu_MOF.json", 
                             do_confirm = False,add_low_res_scan=True)
    

'''
