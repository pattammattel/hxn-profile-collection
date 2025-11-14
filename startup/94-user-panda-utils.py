import re 

def export_scan_header(scan_id,motorx,rangex,numx,motory,rangey,numy,detectors):
    with open('/data/users/startup_parameters/scan_header.txt','w') as f:
        f.write('[scan]\n')
        f.write('scan_num = %d\n'%scan_id)
        f.write('xmotor = %s\n'%motorx.name)
        f.write('ymotor = %s\n'%motory.name)
        f.write('x_range = %.2f\n'%rangex)
        f.write('y_range = %.2f\n'%rangey)
        f.write('x_num = %d\n'%numx)
        f.write('y_num = %d\n'%numy)
        f.write('nz = %d\n'%(numx*numy))
        if detectors:
            roi_start = detectors[0].roi1.min_xyz.get()
            f.write('det_roix_start = %d\n'%roi_start[0])
            f.write('det_roiy_start = %d\n'%roi_start[1])
        
        # Eiger2 image is mirrored
        if detectors:
            if detectors[0].name == 'eiger2':
                f.write('mirror_image = True\n')
            else:
                f.write('mirror_image = False\n')


def plotlastfluo(id=-1,elem = 'Ni'):
    st = db[id].start['scan']
    scan_size = [st['scan_input'][2],st['scan_input'][5]]
    fluo = np.zeros(scan_size[1]*scan_size[0])
    for roi in xspress3.enabled_rois:
        if elem in roi.name:
            f = roi.settings.array_data.get()
            fluo[:len(f)] += f
    f2d = fluo.reshape(scan_size[1],scan_size[0])

    plt.close(110)
    plt.figure(110)
    plt.imshow(f2d)
    return f2d

def cenlastfluo():
    st = db[-1].start['scan']
    if st['fast_axis']['motor_name'] == 'zpssx':
        px = db.reg.retrieve(db[-1].table()['inenc3_val'][1])
        px = (px - np.mean(px))*9.7e-5
    else:
        px = db.reg.retrieve(db[-1].table()['inenc4_val'][1])
        px = -(px - np.mean(px))*1.006e-4
    scan_size = [st['scan_input'][2],st['scan_input'][5]]
    py = np.linspace(st['scan_input'][3],st['scan_input'][4],scan_size[0]*scan_size[1])
    fluo = np.zeros(scan_size[1]*scan_size[0])
    for roi in xspress3.enabled_rois:
        if 'Ni' in roi.name:
            fluo += roi.settings.array_data.get()[:len(fluo)]
    return get_masscenter(px,py,fluo)


def zp_tomo_scan_rapid(angle_start, angle_end, angle_step, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure, elem,save_file,ic_0=None):
    #if os.path.isfile('rotCali'):
    #    caliFile = open('rotCali','rb')
    #    y = pickle.load(caliFile)
    angle_start = float(angle_start)
    angle_end = float(angle_end)
    angle_step = float(angle_step)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
    angle_num = int(np.ceil(np.abs((angle_end-angle_start)/angle_step)))

    from hxntools.motor_info import motor_table

    # x_scale_factor = 0.9542
    # z_scale_factor = 1.0309

    x_scale_factor = 1
    z_scale_factor = 1

    if ic_0 is None:
        ic_0 = sclr2_ch2.get()
    for i in range(angle_num + 1):
        yield from bps.mov(zpssy,0)

        angle = angle_start + i * angle_step * np.sign(angle_end-angle_start)
        yield from bps.mov(zps.zpsth, angle)

        #yield from bps.mov(zpssx,0)
        #yield from bps.mov(zpssy,0)
        #yield from bps.mov(zpssz,0)

        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC1 is lower than 1000, waiting...')
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
        #yield from bps.sleep(3)
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
        #yield from bps.sleep(3)

        angle_offset = -0.2
        RE.md['tomo_angle_offset'] = angle_offset
        RE.md['x_scale_factor'] = x_scale_factor
        RE.md['z_scale_factor'] = z_scale_factor

        if np.abs(angle-angle_offset) <= 45.:
            #yield from bps.movr(zpssy,-1)
            yield from fly2dcontpd([fs,eiger2,xspress3],zpssx,-8,8,20,zpssy,-8,8,20,0.01,dead_time = 0.001)
            yield from bps.sleep(0.5)
            plotlastfluo();
            plt.pause(0.05)
            plt.show()
            cen = cenlastfluo()
            if not np.isnan(cen[0]):
                yield from bps.movr(smarx,cen[0]/1000)
            if not np.isnan(cen[1]):
                yield from bps.movr(smary,(cen[1]+2.0)/1000)
        else:
            yield from fly2dcontpd([fs,eiger2,xspress3],zpssz,-8,8,20,zpssy,-8,8,20,0.01,dead_time = 0.001)
            yield from bps.sleep(0.5)
            plotlastfluo();
            cen = cenlastfluo()
            if not np.isnan(cen[0]):
                yield from bps.movr(smarz,cen[0]/1000)
            if not np.isnan(cen[1]):
                yield from bps.movr(smary,(cen[1]+2.0)/1000)
        #eiger2.hdf5.warmup()


        if np.abs(angle-angle_offset) <= 45.0:
            # yield from fly2d(dets1,zpssx,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.cos((angle-angle_offset) * np.pi / 180.)/x_scale_factor
            x_end_real = x_end / np.cos((angle-angle_offset) * np.pi / 180.)/x_scale_factor
            y_start_real = y_start
            y_end_real = y_end
            #yield from fly2d([fs, zebra, sclr1, xspress3], zpssy, y_start, y_end, y_num,
            #                 zpssx, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssx, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2dcontpd([fs,eiger2],zpssx,x_start_real, x_end_real, x_num,zpssy,y_start_real,y_end_real,y_num,exposure)

        else:
            # yield from fly2d(dets1,zpssz,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.abs(np.sin((angle-angle_offset) * np.pi / 180.))/z_scale_factor
            x_end_real = x_end / np.abs(np.sin((angle-angle_offset) * np.pi / 180.))/z_scale_factor
            y_start_real = y_start
            y_end_real = y_end
            #yield from fly2d([fs, zebra, sclr1, xspress3],zpssy, y_start, y_end, y_num,
            #                 zpssz, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssz, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2dcontpd([fs,eiger2],zpssz,x_start_real, x_end_real, x_num,zpssy,y_start_real,y_end_real,y_num,exposure)

        #mov_to_image_cen_smar(-1)
        #yield from mov_to_image_cen_dsx(-1)
        #plot2dfly(-1,elem,'sclr1_ch4')
        #insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
        #plt.close()
        #merlin2.unstage()
        #xspress3.unstage()
        #yield from bps.sleep(5)
        #insert_xrf_map_to_pdf(-1, elem, title_=['zpsth'])
        flog = open(save_file,'a')
        flog.write('%d %.2f\n'%(db[-1].start['scan_id'],zpsth.position))
        flog.close()
        #if (sclr2_ch2.get() < (0.85*ic_0)):
        #    yield from peak_the_flux()
        #if np.remainder(i+1,5)==0:
        #    yield from peak_bpm_x(-20, 20, 10)
        #    yield from peak_bpm_y(-10, 10, 10)
    save_page()


class PandaLivePlot():
    def __init__(self):
        self.do_plot = False
        self.fig, self.ax = plt.subplots()
        self.ntotal = len(live_plot_elems)
        self.nrow = int(np.sqrt(self.ntotal))
        self.ncol = int(np.ceil(self.ntotal/self.nrow))
        self.scan_id = 0

    def setup_plot(self,scan_input,det,sclr=None):
        self.xsp = det
        self.fig.clear()
        self.axs = []
        self.axs_names = []
        self.elems = []

        for i in range(self.ntotal):
            self.axs.append(self.fig.add_subplot(self.nrow,self.ncol,i+1))
            self.elems.append([])
            self.axs_names.append(live_plot_elems[i])

        for r in self.xsp.enabled_rois:
            for i in range(self.ntotal):
                if live_plot_elems[i].startswith('sclr') and len(self.elems[i]) == 0:
                    match = re.search(r'sclr(\d+)_ch(\d+)',live_plot_elems[i])
                    ch_num = int(match.group(2))
                    self.elems[i].append(sclr.mca_by_index[ch_num])
                else:
                    if r.name.endswith(live_plot_elems[i]) and not r.name in [roi.name for roi in self.elems[i]]:
                        self.elems[i].append(r)

        self.scan_input = scan_input.copy()
        if len(self.scan_input)<2:
            self.total_points = int(scan_input[0])
        elif len(self.scan_input)<6:
            self.total_points = int(scan_input[2])
        else:
            self.total_points = int(scan_input[2] * scan_input[5])
        self.do_plot = True

    def update_plot(self, finished = False):
        if not self.do_plot:
            return
        #Live plot
        for i in range(self.ntotal):
            fluo_data = np.zeros(self.total_points)
            set_nan = False
            for roi in self.elems[i]:
                if roi.name.startswith('sclr'):
                    fluo_tmp = roi.spectrum.get()
                    set_nan = True
                else:
                    fluo_tmp = roi.settings.array_data.get()
                if len(fluo_tmp) > self.total_points:
                    return
                fluo_data[:len(fluo_tmp)] += fluo_tmp
            if finished:
                fluo_data[len(fluo_tmp):] = fluo_data[len(fluo_tmp)-1]
                self.do_plot = False
            if set_nan:
                fluo_data[fluo_data==0] = np.nan
            #    if hasattr(roi,'settings'):
            #        fluo_data = roi.settings.array_data.get()
            #    else:
            #        fluo_data = roi.ts_total.get()
            self.axs[i].clear()
            self.axs[i].set_title(self.axs_names[i])
            if len(self.scan_input)>=6 and self.scan_input[5]>1:
                self.axs[i].imshow(fluo_data.reshape((int(self.scan_input[5]),int(self.scan_input[2]))),extent = [self.scan_input[0],self.scan_input[1],self.scan_input[4],self.scan_input[3]])
                self.axs[i].set_aspect('equal','box')
            elif len(self.scan_input)>1:
                coordx = np.linspace(self.scan_input[0],self.scan_input[1],int(self.scan_input[2]))
                self.axs[i].plot(coordx[:len(fluo_tmp)],fluo_data[:len(fluo_tmp)])
            else:
                self.axs[i].plot(fluo_data[:len(fluo_tmp)])
        self.fig.canvas.manager.set_window_title('Scan %d'%(self.scan_id))
        self.fig.suptitle('Scan %d'%(self.scan_id))
        self.fig.canvas.manager.show()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
    
def panda_zero_all_encoders():
    print("Make sure to move all piezo motors to zero position when running this command!")
    panda1.inenc1.setp.put(0)
    panda1.inenc2.setp.put(0)
    panda1.inenc3.setp.put(0)
    panda1.inenc4.setp.put(0)
    print("All panda encoders set to zero at current piezo position.")

panda_live_plot = PandaLivePlot()

time.sleep(0.05)
plt.close(panda_live_plot.fig)

