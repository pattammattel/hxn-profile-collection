def disable_KB_piezo_close_loop():
    # PPMAC control signal
    sl = ppmac.gpascii.send_line
    sl('#3,4,5k')

def zero_KB_piezos():
    # PPMAC control signal
    sl = ppmac.gpascii.send_line
    sl('#3,4,5hmz')

def hm_roty(angle_mdeg):
    disable_KB_piezo_close_loop()
    yield from bps.movr(kb_stage.hm_ry,0.001*angle_mdeg)
    # yield from bps.movr(kb_stage.vm_z,-219.404*angle_mdeg)

    # Correct sample position
    # yield from bps.movr(p_sbx,angle_mdeg*1.745)
    # Move with EPICS channel to avoid bluesky sending stop signal to the stage

    # p_sbx
    caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWV',np.abs(angle_mdeg*4.5))
    if angle_mdeg < 0:
        caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWR',1)
    else:
        caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWF',1)
    yield from bps.sleep(1)

    # #p_sby
    # caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWV',np.abs(angle_mdeg*0))
    # if angle_mdeg > 0: # Move negative
    #     caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWR',1)
    # else:
    #     caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWF',1)
    # yield from bps.sleep(1)

    # #p_sbz
    # caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWV',np.abs(angle_mdeg*219.404))
    # if angle_mdeg > 0: # Move negative
    #     caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWR',1)
    # else:
    #     caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWF',1)
    # yield from bps.sleep(1)

    zero_KB_piezos()


def vm_rotx(angle_mdeg):
    disable_KB_piezo_close_loop()
    yield from bps.movr(kb_stage.vm_rx,0.001*angle_mdeg)
    # yield from bps.movr(kb_stage.vm_z,463.743*angle_mdeg)

    # Correct sample position
    # yield from bps.movr(p_sby,-angle_mdeg*3.665)
    # Move with EPICS channel to avoid bluesky sending stop signal to the stage

    # p_sby
    caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWV',np.abs(angle_mdeg*(3.665)))
    if angle_mdeg > 0: # Move negative
        caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWR',1)
    else:
        caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWF',1)

    yield from bps.sleep(1)
    zero_KB_piezos()

def movr_kb_sbz(distance_um):
    disable_KB_piezo_close_loop()

    caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWV',np.abs(distance_um))
    if distance_um < 0:
        caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWR',1)
    else:
        caput('XF:03IDC-ES{ANC350:9-Ax:1}Mtr.TWF',1)

    yield from bps.sleep(1)
    caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWV',np.abs(distance_um*0.00876))
    if distance_um < 0:
        caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWR',1)
    else:
        caput('XF:03IDC-ES{ANC350:9-Ax:2}Mtr.TWF',1)

    yield from bps.sleep(1)
    caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWV',np.abs(distance_um*0.0175))
    if distance_um > 0: # Move negative
        caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWR',1)
    else:
        caput('XF:03IDC-ES{ANC350:9-Ax:3}Mtr.TWF',1)
    
    yield from bps.sleep(1)
    zero_KB_piezos()


def plot_kb_scan(sid = -1, elem = 'Au_L', norm = 'sclr1_ch3'):

    if elem in elem_K_list:
        energy = energy_K_list[elem_K_list == elem]
    elif elem in elem_L_list:
        energy = energy_L_list[elem_L_list == elem]
    elif elem in elem_M_list:
        energy = energy_M_list[elem_M_list == elem]
    else:
        raise Exception(f'Cannot found element {elem}')
    
    e_low = int(energy//10-15)
    e_high = int(energy//10+15)
    
    ic  = np.squeeze(np.array(list(db[sid].data(norm))))

    fp = np.sum(np.squeeze(np.array(list(db[sid].data('xspress3_ch4'))))[:,e_low:e_high],1)/ic
    plt.figure() 
    st = db[sid].start
    arg = st['scan']['scan_input']
    plt.imshow(fp.reshape(st['shape']),aspect='auto',extent=[arg[0],arg[1],arg[4],arg[3]])
    plt.title(f"{st['scan_id']} {elem}")
    plt.xlabel(st['motors'][0])
    plt.ylabel(st['motors'][1]) 



