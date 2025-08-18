#Last Update 09/11/2021 by AP

"""

ReadMe:



EXAMPLE OF USAGE:

<zp_spectro_tomo_scan(MnXANES,path_to_json,pdfElem = ['Mn'],pdfLog = True, peakBeam = True,saveLogFolder = '/data/users/current_user/cycled_nmc_mn_spectro-tomo/)


"""


import numpy as np
import pandas as pd
import time,json
import scipy
from datetime import datetime
import scipy.constants as consts
from scipy.sparse.linalg import gmres, lgmres, LinearOperator

#from phantominator import shepp_logan
import tifffile as tf


#Paramer list from previous runs in the order of atomic number of the element
            
FeXANES = {'high_e':7.2, 'high_e_zpz1':6.41, 'zpz1_slope':-5.04}
CoXANES = {'high_e':7.8, 'high_e_zpz1':3.2725, 'zpz1_slope':-5.04}
MnXANES = {'high_e':6.6, 'high_e_zpz1':1.975, 'zpz1_slope':-5.04}
NiXANES_ST = {'high_e':8.45, 'high_e_zpz1':-5.2, 'zpz1_slope':-6.093}

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
def rand_list(input_list):
    n = len(input_list)
    output_list = []
    for i in range(n):
        ind = int(np.floor(np.random.rand()*(n-i)))
        output_list.append(input_list[ind])
        input_list = np.delete(input_list,ind)
    return output_list


multiplicity = 3

def generate_plan(ref,angle_rng,num_angle,option):
    num_energy, num_state = np.shape(ref)
    #num_angle = num_energy*multiplicity
    spectra_list = []    
    ind = []
    if option == 'uniform-uniform': 
        angle_list = np.linspace(angle_rng[0],angle_rng[1],num_angle)
        for i in range(multiplicity):
            if len(spectra_list) == 0:
                spectra_list = ref
            else:
                spectra_list = np.concatenate((spectra_list,ref),axis = 0)    
    elif option == 'golden-ratio-uniform':
        rng = angle_rng[1]-angle_rng[0]
        angle_list = angle_rng[0] + np.mod(rng*np.linspace(0,num_angle,num_angle)/1.618,rng)
        angle_list = np.sort(angle_list)
        for i in range(multiplicity):
            if len(spectra_list) == 0:
                spectra_list = ref
            else:
                spectra_list = np.concatenate((spectra_list,ref),axis = 0)    
    elif option == 'random-random':
        angle_list = np.random.rand(num_angle)*(angle_rng[1]-angle_rng[0])+angle_rng[0]
        angle_list = np.sort(angle_list)
        ind = np.array(np.floor(np.random.rand(num_angle)*num_energy),dtype='int')
        spectra_list = ref[ind,:]
    elif option == 'uniform-random':
        angle_list = np.linspace(angle_rng[0],angle_rng[1],num_angle)
        ind = np.array(np.floor(np.random.rand(num_angle)*num_energy),dtype='int')
        spectra_list = ref[ind,:]
    elif option == 'random-uniform':
        angle_list = np.random.rand(num_angle)*(angle_rng[1]-angle_rng[0])+angle_rng[0]
        angle_list = np.sort(angle_list)
        for i in range(multiplicity):
            if len(spectra_list) == 0:
                spectra_list = ref
            else:
                spectra_list = np.concatenate((spectra_list,ref),axis = 0) 
    elif option == 'golden-ratio-random':
        rng = angle_rng[1]-angle_rng[0]
        angle_list = angle_rng[0] + np.mod(rng*np.linspace(0,num_angle,num_angle)/1.618,rng)
        angle_list = np.sort(angle_list)
        ind = np.array(np.floor(np.random.rand(num_angle)*num_energy),dtype='int')
        spectra_list = ref[ind,:]
    elif option == 'uniform-random2':
        angle_list = np.linspace(angle_rng[0],angle_rng[1],num_angle)
        
        for i in range(multiplicity):
            ind = rand_list(np.linspace(0,num_energy-1,num_energy,dtype='int'))
            if len(spectra_list) == 0:
                spectra_list = ref[ind,:]
            else:
                spectra_list = np.concatenate((spectra_list,ref[ind,:]),axis = 0)
    elif option == 'random-random2':
        angle_list = np.random.rand(num_angle)*(angle_rng[1]-angle_rng[0])+angle_rng[0]
        angle_list = np.sort(angle_list)
        for i in range(multiplicity):
            ind = rand_list(np.linspace(0,num_energy-1,num_energy,dtype='int'))
            if len(spectra_list) == 0:
                spectra_list = ref[ind,:]
            else:
                spectra_list = np.concatenate((spectra_list,ref[ind,:]),axis = 0)
    elif option == 'special':
        n = 10
        angle_list = np.random.rand(n)*(angle_rng[1]-angle_rng[0])+angle_rng[0]
        spectra_list = np.reshape(ref[num_energy//2,:],(1,-1))
        print(np.shape(spectra_list))
        for i in range(n-1):
            spectra_list = np.concatenate((spectra_list,np.reshape(ref[num_energy//2,:],(1,-1))),axis = 0)
        angle_list = np.concatenate((angle_list,np.random.rand(num_angle-n)*(angle_rng[1]-angle_rng[0])+angle_rng[0]),axis=0)
        angle_list = np.sort(angle_list)
        ind = np.array(np.floor(np.random.rand(num_angle-n)*num_energy),dtype='int')
        tmp = ref[ind,:]
        print(np.shape(tmp))
        spectra_list = np.concatenate((spectra_list,ref[ind,:]),axis=0)
    else:
        angle_list = np.linspace(angle_rng[0],angle_rng[1],num_angle)
        for i in range(multiplicity):
            if len(spectra_list) == 0:
                spectra_list = ref
            else:
                spectra_list = np.concatenate((spectra_list,ref),axis = 0)
    
    plan = np.column_stack((angle_list, spectra_list, ind))
    return plan
    #return angle_list, spectra_list, ind



# used_spect = np.reshape(np.loadtxt('Co_energy_list_reduced.txt'),(-1,1))
# angle, ref, ind = generate_plan(used_spect,[-90,90],181,'uniform-random')
# plan = np.concatenate([np.reshape(angle,(-1,1)),np.reshape(ref,(-1,1)),np.reshape(ind,(-1,1))],axis=1)
# np.savetxt('plan_cobalt_better.txt',plan,fmt=['%3.2f','%4.3f','%d'])




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



def move_energy_and_angle(e,angle,zpz_):

    yield from Energy.move(e, moveMonoPitch=False, moveMirror = "ignore")
    yield from mov_zpz1(zpz_)
    yield from bps.mov(zpsth, angle)
    yield from bps.sleep(2)
    #cbpm_on(True)


def create_energy_angle_df(filename, XANESParam):

    """

    Generates a pandas dataframe of optics motor positions. Function uses high E and low E values in the dictionary
    to generate motor positions for all the energy points, assuming linear relationship.

    input: Dictionary conating optics values at 2 positions (high E and low E), option to start from high E or low E

    return : Dataframe looks like below;

       energy     ZP focus
    0   7.175     65.6575
    1   7.170     65.6870
    2   7.165     65.7165
    3   7.160     65.7460
    4   7.155     65.7755

    """
    # empty dataframe
    e_list = pd.DataFrame()
    
    enegy_and_angle = np.loadtxt(filename)
    e_points = enegy_and_angle[:,1]

    if e_points[0] >100:
        e_points *= 0.001

    angles = enegy_and_angle[:,0]

    #add list of energy as first column to DF
    e_list['energy'] = e_points
    e_list['angle'] = angles
    

    #read the paramer dictionary and calculate ugap list
    high_e = XANESParam['high_e']

    #zone plate increament is very close to the theorticla value , same step as above for zp focus
    zpz1_ref, zpz1_slope = XANESParam['high_e_zpz1'],XANESParam['zpz1_slope']
    zpz1_list = zpz1_ref + (e_list['energy'] - high_e)*zpz1_slope
    e_list['ZP focus'] = zpz1_list

    #return the dataframe
    return e_list

def zp_tomo_2d_scan(angle,dets_,x_start,x_end,x_num,y_start,y_end,y_num,exp):
    print("zp tomo 2d scan")
    
    x_scale_factor = 0.9542
    z_scale_factor = 1.0309

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

def run_zp_spectro_tomo_scan(path_to_json):

    """ 
    Usage:
    path_to_json  = "/data/users/current_user/spectro_tomo_ni_golden.json"
<run_zp_spectro_tomo_scan(path_to_json)





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
    
    
    """   
    #load paramfile
    with open(path_to_json,"r") as fp:
        scan_params = json.load(fp)
        fp.close()
    # marker to track beam dump             
    beamDumpOccured = False
                    
    e_list = create_energy_angle_df(scan_params["energy_angle_list_file"],scan_params)

    #add real energy to the dataframe
    e_list['E Readback'] = np.nan 
    
    #add scan id to the dataframe
    e_list['Scan ID'] = np.nan 
    
    #recoed time
    e_list['TimeStamp'] = pd.Timestamp.now()
    
    #Ic values are useful for calibration
    e_list['IC3'] = sclr2_ch4.get() 
    e_list['IC0'] = sclr2_ch2.get()
    e_list['IC3_before_peak'] = sclr2_ch4.get()
    e_list["zpsth"] = zpsth.position
    
    
    #record if peak beam happed before the scan   
    e_list['Peak Flux'] = False 
    
    # print(e_list.head())
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
    #open the json file to catch any updates 


    image_scan_i = scan_params["fly2d_scan"]

    tot_time_ = (image_scan_i["x_num"]*image_scan_i["y_num"]*image_scan_i["exposure"]*len(e_list))
    tot_time = tot_time_/3600
    overhead = 1.2
    end_datetime = time.ctime(time.time()+tot_time_*overhead)
    check = input(f"This plan takes about {tot_time*overhead :.1f} hours,"
                    f"Projected to {end_datetime} continue (y/n)?")
    if check == "y":

        for i in tqdm.tqdm(range(len(e_list)),desc = 'Energy-Angle Scan'):
        #for i in range (len(e_list)):

            print(i/len(e_list))

            #open the json file to catch any updates 
            with open(path_to_json,"r") as fp:
                scan_params = json.load(fp)
                fp.close()

            while scan_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_json,"r") as fp:
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
                yield from recover_from_beamdump() #patch for low energy e change issues

            #wait if beam dump occured beamdump
            yield from check_for_beam_dump(threshold=5000)
            
            if beamDumpOccured:
                #wait for about 3 minutes for all the feedbacks to kick in
                yield from bps.sleep(120)

                #redo the previous energy
                e_t,angle_t,zpz_t, *others = e_list.iloc[i-1]

                #turn off the beamdump marker
                beamDumpOccured = False
                
            else:
                #unwrap df row for energy change
                e_t,angle_t,zpz_t, *others = e_list.iloc[i]
            
            yield from move_energy_and_angle(e_t,angle_t,zpz_t)

            #open fast shutter to check if ic3 reading is satistactory
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
            yield from bps.sleep(5)
            
            #get ic3 value before peaking, e change
            ic3_ = sclr2_ch4.get()
            
            # if ic3 value is below the threshold, peak the beam
            if ic3_ < ic_3_init*scan_params["flux_threshold"]:
                
                if scan_params["peak_flux"]: 
                    yield from peak_the_flux()
                    
                fluxPeaked = True # for df record
            else:
                fluxPeaked = False
            
            #for df
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            
            alignX = scan_params["xalign"]
            alignY = scan_params["yalign"]       

            if e_list['energy'][i]<0: # for special scans if no align elem available
                
                '''
                yield from fly1d(dets,zpssx,-1,1,100,0.1)
                xcen = return_line_center(-1,'Cl',0.7)
                yield from bps.mov(zpssx, xcen)
                yield from fly1d(dets,zpssy,-1,1 ,100,0.1)
                ycen = return_line_center(-1,'Cl',0.7)
                yield from bps.mov(zpssy, ycen)
                '''
                pass

            else:
                if np.abs(angle_t) < 44.99:
                    mtr = zpssx
                else:
                    mtr = zpssz
                
                if alignX["do_align"]:
                    yield from align_scan(  mtr, 
                                                alignX["start"],
                                                alignX["end"],
                                                alignX["num"],
                                                alignX["exposure"],
                                                alignX["elem"],
                                                align_with=alignX["center_with"], 
                                                threshold = alignX["threshold"],
                                                offset=alignX["offset"],
                                                move_coarse = alignX["move_coarse"])  
                #plt.close()              

                if alignY["do_align"]:
                    yield from align_scan(  zpssy, 
                                                alignY["start"],
                                                alignY["end"],
                                                alignY["num"],
                                                alignY["exposure"],
                                                alignY["elem"],
                                                align_with=alignY["center_with"], 
                                                threshold = alignY["threshold"],
                                                offset=alignY["offset"],
                                                move_coarse = alignX["move_coarse"]
                                                ) 
            # alignment_scan_(mtr, start,end,num,exp,elem_, align_with="line_center", threshold = 0.5):
                                                                       
            #plt.close()
            print(f'Current scan: {i+1}/{len(e_list)}')
            image_scan = scan_params["fly2d_scan"]

            yield from zp_tomo_2d_scan( angle_t,
                                        eval(image_scan["det"]),
                                        image_scan["x_start"],
                                        image_scan["x_end"],
                                        image_scan["x_num"],
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
            e_list["zpsth"].at[i] = zpsth.position
            e_list['Scan ID'].at[i] = int(last_sid) #add scan id to the dataframe
            e_list['TimeStamp'].at[i] = pd.Timestamp.now()
            e_list['IC3'].at[i] = ic_3 #Ic values are useful for calibration
            e_list['IC0'].at[i] = ic_0 #Ic values are useful for calibration
            e_list['Peak Flux'].at[i] = fluxPeaked # recoed if peakflux was excecuted
            e_list['IC3_before_peak'].at[i] = ic3_ #ic3 right after e change, no peaking
            fluxPeaked = False #reset
            
            if scan_params["pdf_log"]:
                try:
                    insert_xrf_map_to_pdf(-1,scan_params["pdf_elems"],
                                          title_=['energy', 'zpsth'])# plot data and add to pdf
                    plt.close()
                except:
                    pass
            # save the DF in the loop so quitting a scan won't affect
            saveLogFolder = scan_params["save_log_to"]
            scan_name = scan_params.get("scan_name",'')
            filename = f"HXN_spectro-tomo_{scan_name}_startID{int(e_list['Scan ID'][0])}_{len(e_list)}_e_angle_points.csv"
            e_list.to_csv(os.path.join(saveLogFolder, filename), float_format= '%.5f')

        caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
        if scan_params["pdf_log"]: save_page() #save the pdf

    else:
        return
