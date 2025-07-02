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
def get_tomo_ref(angle):
    if angle < RASMI_laser_ref[0,0] or angle>RASMI_laser_ref[-1,0]:
        return 0
    for i in range(len(RASMI_laser_ref)-1):
        if RASMI_laser_ref[i,0]<=angle and RASMI_laser_ref[i+1,0]>=angle:
            return (RASMI_laser_ref[i+1,1]*(angle-RASMI_laser_ref[i,0])+RASMI_laser_ref[i,1]*(RASMI_laser_ref[i+1,0]-angle))/(RASMI_laser_ref[i+1,0]-RASMI_laser_ref[i,0])

def get_tomo_drift(angle):
    if angle < RASMI_align_drift[0,0] or angle>RASMI_align_drift[-1,0]:
        return 0
    for i in range(len(RASMI_align_drift)-1):
        if RASMI_align_drift[i,0]<=angle and RASMI_align_drift[i+1,0]>=angle:
            return (RASMI_align_drift[i+1,1]*(angle-RASMI_align_drift[i,0])+RASMI_align_drift[i,1]*(RASMI_align_drift[i+1,0]-angle))/(RASMI_align_drift[i+1,0]-RASMI_align_drift[i,0])

def get_tomo_drift_y(angle):
    if angle < RASMI_align_drift_y[0,0] or angle>RASMI_align_drift_y[-1,0]:
        return 0
    for i in range(len(RASMI_align_drift_y)-1):
        if RASMI_align_drift_y[i,0]<=angle and RASMI_align_drift_y[i+1,0]>=angle:
            return (RASMI_align_drift_y[i+1,1]*(angle-RASMI_align_drift_y[i,0])+RASMI_align_drift_y[i,1]*(RASMI_align_drift_y[i+1,0]-angle))/(RASMI_align_drift_y[i+1,0]-RASMI_align_drift_y[i,0])
        
def hmll_roty(step):
    yield from bps.mvr(pt_tomo.hm_ry,1.*step)
    yield from bps.mvr(pt_tomo.hm_x,-657.*step)
def vmll_rotx(step):
    yield from bps.mvr(pt_tomo.vm_rx,1.*step)
    yield from bps.mvr(pt_tomo.vm_y,-30.*step)
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

def rasmi_x_ref():
    #return (caget("XF:03IDC-ES{Pico:1}POS_1")-caget("XF:03IDC-ES{Pico:1}POS_2"))/0.85/1e6 - ptssx.user_readback.get()

    #Scanning MLL
    return (caget("XF:03IDC-ES{Pico:1}POS_1")-caget("XF:03IDC-ES{Pico:1}POS_2"))/0.85/1e6 - ptssx.user_readback.get()*(1.666)

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
