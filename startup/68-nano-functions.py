if not USE_RASMI:
    print(f"RASMI not used, skipping {__file__!r} ...")
    import sys
    sys.exit()

print(f"Loading {__file__!r} ...")

class HXN_FuncGen1(Device):
    freq = Cpt(EpicsSignal, '{FG:1}OUTPUT1:FREQ:SP') #freq.set('#.##'){.wait()}
    freq_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT1:FREQ') #freq.set('#.##'){.wait()}
    volt = Cpt(EpicsSignal, '{FG:1}OUTPUT1:VOLT:SP')
    volt_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT1:VOLT')
    offset = Cpt(EpicsSignal, '{FG:1}OUTPUT1:VOLT:OFFSET:SP')
    sym = Cpt(EpicsSignal, '{FG:1}OUTPUT1:RAMP:SYMM:SP')
    func = Cpt(EpicsSignal, '{FG:1}OUTPUT1:FUNC:SP')
    burst_count = Cpt(EpicsSignal, '{FG:1}OUTPUT1:BURST_NCYCLES:SP')
    burst = Cpt(EpicsSignal, '{FG:1}OUTPUT1:BURST_STATUS:SP')
    output = Cpt(EpicsSignal, '{FG:1}OUTPUT1:STATUS:SP') #output.set('ON'){.wait()}
    output_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT1:STATUS') #output.set('ON'){.wait()}
    trig = Cpt(EpicsSignal, '{FG:1}TRIGGER') #output.set('ON'){.wait()}
    
    #slt_hcen = Cpt(EpicsMotor, '{Slt:4-Ax:Top}Mtr')

    def on(self):
        yield from abs_set(self.output,"ON",wait=True)
        yield from bps.sleep(0.5)

    def off(self):
        yield from abs_set(self.output,"OFF",wait=True)
        yield from bps.sleep(0.5)

class HXN_FuncGen2(Device):
    freq = Cpt(EpicsSignal, '{FG:1}OUTPUT2:FREQ:SP') #freq.set('#.##'){.wait()}
    freq_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT2:FREQ') #freq.set('#.##'){.wait()}
    volt = Cpt(EpicsSignal, '{FG:1}OUTPUT2:VOLT:SP')
    volt_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT2:VOLT')
    offset = Cpt(EpicsSignal, '{FG:1}OUTPUT2:VOLT:OFFSET:SP')
    sym = Cpt(EpicsSignal, '{FG:1}OUTPUT2:RAMP:SYMM:SP')
    func = Cpt(EpicsSignal, '{FG:1}OUTPUT2:FUNC:SP')
    burst_count = Cpt(EpicsSignal, '{FG:1}OUTPUT2:BURST_NCYCLES:SP')
    burst = Cpt(EpicsSignal, '{FG:1}OUTPUT2:BURST_STATUS:SP')
    output = Cpt(EpicsSignal, '{FG:1}OUTPUT2:STATUS:SP') #output.set('ON'){.wait()}
    output_readout = Cpt(EpicsSignal, '{FG:1}OUTPUT2:STATUS') #output.set('ON'){.wait()}
    #slt_hcen = Cpt(EpicsMotor, '{Slt:4-Ax:Top}Mtr')

    def on(self):
        yield from abs_set(self.output,"ON",wait=True)
        yield from bps.sleep(0.5)

    def off(self):
        yield from abs_set(self.output,"OFF",wait=True)
        yield from bps.sleep(0.5)

pt_fg = HXN_FuncGen1('XF:03IDC-ES', name='pt_fg')
pt_fg_ch1 = HXN_FuncGen1('XF:03IDC-ES', name='pt_fg_ch1')
pt_fg_ch2 = HXN_FuncGen2('XF:03IDC-ES', name='pt_fg_ch2')
# pt_fg.output._put_complete = True
# pt_fg.burst._put_complete = True

RASMI_align_drift = np.load('/nsls2/data2/hxn/legacy/users/startup_parameters/68-RASMI-align-drift.npy')
RASMI_align_drift_y = np.load('/nsls2/data2/hxn/legacy/users/startup_parameters/68-RASMI-align-drift_y.npy')
RASMI_laser_ref = np.load('/nsls2/data2/hxn/legacy/users/startup_parameters/68-RASMI-laser-ref.npy')

def get_laser_ref():
    return ((caget('XF:03IDC-ES{Pico:1}POS_1')- caget('XF:03IDC-ES{Pico:1}POS_2'))/1e6*0.689 + \
        caget('XF:03IDC-ES{Pico:1}POS_0')/1e6 \
        - 2.0056506670000003 + 2.05 + 15.019345561000002 -3) # Additional correction

def calib_rasmi_laser_ref(angle_range = np.arange(-90,91,1)):
    input('Will recalibrate and overwrite RASMI tomography alignment lookup table, Ctrl+C now to quit, Enter to continue.')

    yield from bps.mov(pt_tomo.th,angle_range[0]-1)
    laser_ref_temp = None
    for angle in angle_range:
        yield from bps.mov(pt_tomo.th,angle)
        print(f"At {angle} degree")
        input('Move the sample to reference position with *ONLY* ptssx / Sample Scanner X axis and press ENTER')
        if laser_ref_temp is None:
            laser_ref_temp = np.array([angle,get_laser_ref()])
        else:
            laser_ref_temp = np.vstack([laser_ref_temp,np.array([angle,get_laser_ref()])])
        
        # Save temporary data
        np.save('/nsls2/data2/hxn/legacy/users/startup_parameters/68-RASMI-laser-ref-tmp.npy',laser_ref_temp)
        print('\n')
        print(laser_ref_temp)
    np.save('/nsls2/data2/hxn/legacy/users/startup_parameters/68-RASMI-laser-ref.npy',laser_ref_temp)


def get_tomo_ref(angle = None):
    if angle is None:
        angle = pt_tomo.th.user_readback.get()
    if angle < RASMI_laser_ref[0,0]:
        return 0
    if angle>RASMI_laser_ref[-1,0]:
        return RASMI_laser_ref[-1,1] - RASMI_laser_ref[0,1]
    for i in range(len(RASMI_laser_ref)-1):
        if RASMI_laser_ref[i,0]<=angle and RASMI_laser_ref[i+1,0]>=angle:
            return (RASMI_laser_ref[i+1,1]*(angle-RASMI_laser_ref[i,0])+RASMI_laser_ref[i,1]*(RASMI_laser_ref[i+1,0]-angle))/(RASMI_laser_ref[i+1,0]-RASMI_laser_ref[i,0])\
                - RASMI_laser_ref[0,1]


def get_laser_ref_y():
    return (caget('XF:03IDC-ES{Pico:1}POS_1') +  caget('XF:03IDC-ES{Pico:1}POS_2')) /1e6/2


def get_tomo_ref_y(angle = None):
    if angle is None:
        angle = pt_tomo.th.user_readback.get()
    # Calculate mathematically
    return -np.sin(angle/180*np.pi*2)*0.3
        

def get_tomo_drift(angle):
    if angle < RASMI_align_drift[0,0] or angle>RASMI_align_drift[-1,0]:
        return 0
    for i in range(len(RASMI_align_drift)-1):
        if RASMI_align_drift[i,0]<=angle and RASMI_align_drift[i+1,0]>=angle:
            return (RASMI_align_drift[i+1,1]*(angle-RASMI_align_drift[i,0])+RASMI_align_drift[i,1]*(RASMI_align_drift[i+1,0]-angle))/(RASMI_align_drift[i+1,0]-RASMI_align_drift[i,0])

def align_sample_tomo():
    while np.abs(get_laser_ref() - get_tomo_ref(pt_tomo.th.position))>0.05: # or np.abs(get_laser_ref_y() - get_tomo_ref_y(pt_tomo.th.position))>0.05:
        yield from bps.movr(ptssx,get_laser_ref() - get_tomo_ref(pt_tomo.th.position))
        # yield from bps.movr(ptssy,get_laser_ref_y() - get_tomo_ref_y(pt_tomo.th.position))
        yield from bps.sleep(1)

def get_tomo_drift_y(angle):
    if angle < RASMI_align_drift_y[0,0] or angle>RASMI_align_drift_y[-1,0]:
        return 0
    for i in range(len(RASMI_align_drift_y)-1):
        if RASMI_align_drift_y[i,0]<=angle and RASMI_align_drift_y[i+1,0]>=angle:
            return (RASMI_align_drift_y[i+1,1]*(angle-RASMI_align_drift_y[i,0])+RASMI_align_drift_y[i,1]*(RASMI_align_drift_y[i+1,0]-angle))/(RASMI_align_drift_y[i+1,0]-RASMI_align_drift_y[i,0])

def match_rasmi_mcs_readback_positions():
    """
    Match the readback values to the setpoint values for mcs7 and 8 controllers for RASMI.
    Run this whenever the controllers are power-cycled.
    """
    motor_list = [
        pt_tomo.th,
        pt_tomo.cx,
        pt_tomo.cz,
        pt_tomo.bs_x,
        pt_tomo.bs_y,
        pt_tomo.bs_z,
        pt_tomo.bs_rz,
        pt_tomo.hm_x,
        pt_tomo.hm_y,
        pt_tomo.hm_z,
        pt_tomo.hm_ry,
        pt_tomo.zp_x,
        pt_tomo.zp_y,
        pt_tomo.zp_z,
        #pt_tomo.zp_rx, 
        #pt_tomo.zp_ry,
        pt_tomo.osa_x,
        pt_tomo.osa_y,
        pt_tomo.osa_z,
        pt_tomo.sb_x,
        # pt_tomo.sb_y,
        pt_tomo.sb_z,
        pt_tomo.vm_x,
        pt_tomo.vm_y,
        pt_tomo.vm_z,
        pt_tomo.vm_rx,
        pt_tomo.vm_rz,
    ]
    for motor in motor_list:
        motor.set_current_position(motor.user_setpoint.get())
        time.sleep(0.01)
        motor.set_current_position(motor.user_setpoint.get())


def hmll_roty(step):
    yield from bps.mvr(pt_tomo.hm_ry,1.*step)
    yield from bps.mvr(pt_tomo.hm_x,-657.*step)
def vmll_rotx(step):
    yield from bps.mvr(pt_tomo.vm_rx,1.*step)
    #yield from bps.mvr(pt_tomo.vm_y,-30.*step)
    yield from bps.mvr(pt_tomo.vm_y,-11*step)
def vmll_rotz(step):
    yield from bps.mvr(pt_tomo.vm_rz,1.*step)
    yield from bps.mvr(pt_tomo.vm_y,18*step)
    yield from bps.mvr(pt_tomo.vm_x,-18.*step)

def opt_rotx(step):
    yield from bps.mvr(pt_tomo.zp_rx,1.*step)
    yield from bps.mvr(pt_tomo.zp_y,.15*step)
def opt_roty(step):
    yield from bps.mvr(pt_tomo.zp_ry,1.*step)
    yield from bps.mvr(pt_tomo.zp_x,.135*step)


def sample_movz(step,use_cx = False,use_sby=False):
    yield from bps.mvr(pt_tomo.cz,1.*step)
    if use_cx:
        yield from bps.mvr(pt_tomo.cx,14./1000*step)
    else:
        yield from bps.mvr(pt_tomo.ssx,14./1000*step)
    if use_sby:
        yield from bps.mvr(pt_tomo.sb_y,-18./1000*step)
    else:
        yield from bps.mvr(pt_tomo.ssy,-18./1000*step)

def measure_proj_series(zlist,exp_time=3):
    eiger_mobile.tif_filename.put_complete=True
    z0 = zlist[0]
    for i in range(len(zlist)):
        if i>0:
            yield from sample_movz(zlist[i]-zlist[i-1],True)
        yield from bps.abs_set(eiger_mobile.tif_filename,list(b'SiemenStar_%dum_3s'%(zlist[i])))
        yield from bps.abs_set(eiger_mobile.tif_capture,1)
        yield from bps.abs_set(eiger_mobile.cam.acquire,1)
        yield from bps.sleep(16)

def rotate_rasmi_sample_tomo_roty(abs_angle):
    angle_backlash = 1
    yield from bps.mov(pt_tomo.th,abs_angle-angle_backlash)
    yield from bps.sleep(0.5)
    yield from bps.mvr(pt_tomo.th,angle_backlash)
    yield from bps.sleep(0.5)
    yield from align_sample_tomo()
    yield from bps.sleep(0.5)

def rasmi_tomo(anglist,startx,endx,stepx,starty,endy,stepy,exposure_time,logfile="/data/users/current_user/rasmi_tomo.txt",close_shutter_after_scan = False):

    # Use the tweak input box for both stages for manual correction offset
    caput('XF:03IDC-ES{PT:Smpl-Ax:ssx}Mtr.TWV',0)
    caput('XF:03IDC-ES{PT:Smpl-Ax:ssy}Mtr.TWV',0)

    yield from bps.mov(pt_tomo.th,anglist[0]-5)
    # Always scan from minus angle towards positive direction

    for angle in anglist:
        yield from bps.mov(pt_tomo.th,angle)
        yield from align_sample_tomo()
        xoffset = caget('XF:03IDC-ES{PT:Smpl-Ax:ssx}Mtr.TWV')
        yoffset = caget('XF:03IDC-ES{PT:Smpl-Ax:ssy}Mtr.TWV')
        yield from pt_fly2dcontpd([eiger3],ptssx,startx+xoffset,endx+xoffset,int(stepx),\
                                  ptssy,starty+yoffset,endy+yoffset,stepy,exposure_time)
        flog = open(logfile,'a')
        flog.write('%d %.2f\n'%(db[-1].start['scan_id'],pt_tomo.th.user_readback.value))
        flog.close()
    if close_shutter_after_scan:
        caput("XF:03IDB-PPS{PSh}Cmd:Cls-Cmd", 1)

def parse_newscan_rois(filename):
    import configparser
    config = configparser.ConfigParser(inline_comment_prefixes=('#',))
    config.read(filename)
    i = 0
    roi = []
    try:
        while i < 100:
            roi_name = 'ROI'+str(i)
            x_mvr           = config.getfloat(roi_name,'x_mvr')
            y_mvr           = config.getfloat(roi_name,'y_mvr')
            x_range           = config.getfloat(roi_name,'x_range')
            y_range           = config.getfloat(roi_name,'y_range')
            roi.append([x_mvr,y_mvr,x_range,y_range])
            i += 1
    except:
        pass
    return roi

def rasmi_auto_2d_scan_demo(startx,endx,stepx,starty,endy,stepy,exposure_time):

    roi_filename = '/data/users/current_user/test/roi_ranges_bsui.txt'
    max_roi_num = 8

    try:
        os.remove(roi_filename)
    except:
        pass

    yield from pt_fly2dcontpd([eiger3],ptssx,startx,endx,int(stepx),\
                                ptssy,starty,endy,stepy,exposure_time)
    
    print('Waiting for ROIs detection from previous scan...')

    while not os.path.isfile(roi_filename):
        yield from bps.sleep(0.5)

    rois = parse_newscan_rois(roi_filename)
    # rois = [[0.,0.,2.,2.]]

    for roi in rois[:max_roi_num]:
        startx = roi[0]
        endx = roi[0] - roi[2]
        starty = roi[1]
        endy = roi[1] + roi[3]
        print(f'Next scan: ptssx,{startx},{endx},{stepx}; ptssy,{starty},{endy},{stepy}')
        input('press Enter to start')
        yield from pt_fly2dcontpd([eiger3],ptssx,startx,endx,int(stepx),\
                                ptssy,starty,endy,stepy,exposure_time)

    

def golden_tomo(samplename,interv,offset = 0):
     gdratio = (np.sqrt(5)-1)/2
     while True:
         if pt_tomo.th.position<0:
             yield from do_tomo(samplename,-90+offset,90+offset,interv)
         else:
             yield from do_tomo(samplename,90+offset,-90+offset,interv)
         offset = offset+interv*gdratio
         if offset>interv:
             offset -= interv
def get_masscenter(x, y, I):
    return np.array([-np.sum(x*I), np.sum(y*I)])/np.sum(I)

class software_shutter:
    def stage(self):
        caput('XF:03IDB-PPS{PSh}Cmd:Opn-Cmd',1)
        yield from bps.sleep(3)
    def unstage(self):
        caput('XF:03IDB-PPS{PSh}Cmd:Cls-Cmd',1)
        yield from bps.sleep(3)

def rasmi_interf_calib_scan(npoints):
    yield from bps.mov(pt_tomo.th,-114)
    step = 360/npoints
    for i in range(npoints):
        yield from bps.sleep(1)
        yield from bps.mov(pt_tomo.ssy,5)
        yield from bps.sleep(1)
        yield from bps.mov(pt_tomo.ssy,0)
        yield from bps.sleep(1)
        yield from bps.movr(pt_tomo.th,step)
    yield from bps.sleep(1)
    yield from bps.mov(pt_tomo.ssy,5)
    yield from bps.sleep(1)
    yield from bps.mov(pt_tomo.ssy,0)
    yield from bps.sleep(1)
    yield from bps.mov(pt_tomo.th,0)
