import numpy as np
import matplotlib.pyplot as plt
import sys
from scipy import ndimage
#from databroker import get_table, db
#from skimage.filters.rank import median
from skimage.morphology import disk
from skimage import io
# from databroker.v0 import Broker
# db = Broker.named('hxn')


def rm_pixel(data,ix,iy):
    data[ix,iy] = np.median(data[ix-1:ix+1,iy-1:iy+1])
    return data

def display_frame(index):
    #t = np.flipud(np.squeeze(np.asarray(filestore.api.get_data(df['merlin1'][np.ceil(index)]))))
    #print(index)
    t = diff_array[:,:,index]
    fig3 = plt.figure(3)
    plt.clf()
    cl = np.percentile(diff_array,15)
    ch = np.percentile(diff_array,99.95)
    #im2 = plt.imshow(np.flipud(np.log10(t+.001)), cmap = 'spectral', interpolation = 'none')
    im2 = plt.imshow(np.flipud(t.T), cmap = 'hot', interpolation = 'none',clim=[cl,ch])
    #im2 = plt.imshow(np.flipud(np.log10(t+0.001).T), cmap = 'hot', interpolation = 'none')
    iy = np.floor(index/num_x)
    ix = np.mod(index, num_x)
    index_new = (num_y-iy) * num_x + (num_x - ix)
    #plt.title('x: '+np.str(x_data[index])+'um, y: '+np.str(y_data[index])+'um')
    plt.title('x: %.3f' % x_data[index]+' um, y: %.3f' %y_data[index]+' um')
    plt.colorbar()
    plt.draw()

    '''
    t2 = diff_array_2[:,:,index]
    fig4 = plt.figure(4)
    plt.clf()
    #im2 = plt.imshow(np.flipud(np.log10(t+.001)), cmap = 'spectral', interpolation = 'none')
    im2 = plt.imshow(np.flipud(np.log10(t2+0.001).T), cmap = 'hot', interpolation = 'none')#,clim=[cl2,ch2])
    iy = np.floor(index/num_x)
    ix = np.mod(index, num_x)
    index_new = (num_y-iy) * num_x + (num_x - ix)
    #plt.title('x: '+np.str(x_data[index])+'um, y: '+np.str(y_data[index])+'um')
    plt.title('x: %.3f' % x_data[index]+' um, y: %.3f' %y_data[index]+' um')
    plt.colorbar()
    plt.draw()
    '''

def onclick(event):
    #print(w,l,event.xdata,event.ydata)
    index = w*(int(np.round(event.ydata)))  + int(np.round(event.xdata))
    fig = plt.figure(0)
    plt.clf()
    plt.imshow(xrf,interpolation = 'none',aspect='auto')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' '+elem)
    plt.draw()

    fig1 = plt.figure(1)
    plt.clf()
    plt.imshow(roi,interpolation = 'none',aspect='auto')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' Diff ROI')
    plt.draw()

    '''
    fig2 = plt.figure(2)
    plt.clf()
    im1 = plt.imshow(roi2,interpolation = 'none')
    plt.scatter(int(np.round(event.xdata)), int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' Trans ROI')
    plt.draw()
    '''
    #print(index)
    display_frame(index)


def onclick_roi(event):
    #print(w,l,event.xdata,event.ydata)
    index = w*(int(np.round(event.ydata)))  + int(np.round(event.xdata))
    fig1 = plt.figure(1)
    plt.clf()
    plt.imshow(roi,interpolation = 'none',aspect='auto')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' Diff ROI')
    plt.draw()


    fig1 = plt.figure(0)
    plt.clf()
    plt.imshow(xrf,interpolation = 'none',aspect='auto')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' '+elem)
    plt.draw()

    '''
    fig1 = plt.figure(2)
    plt.clf()
    im1 = plt.imshow(roi2,interpolation = 'none')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' Trans ROI')
    plt.draw()
    '''
    #print(index)
    display_frame(index)

def onclick_roi2(event):
    #print(w,l,event.xdata,event.ydata)
    index = w*(int(np.round(event.ydata)))  + int(np.round(event.xdata))
    fig1 = plt.figure(2)
    plt.clf()
    im1 = plt.imshow(roi2,interpolation = 'none')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' tran ROI')
    plt.draw()


    fig1 = plt.figure(0)
    plt.clf()
    im1 = plt.imshow(xrf,interpolation = 'none')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' '+elem)
    plt.draw()


    fig1 = plt.figure(1)
    plt.clf()
    im1 = plt.imshow(roi,interpolation = 'none')
    plt.scatter(int(np.round(event.xdata)),int(np.round(event.ydata)),zorder=1)
    plt.title('#'+scan_num +' Diff ROI')
    plt.draw()

    #print(index)
    display_frame(index)


def onclick_fermat(event):
    index = (np.abs(x-event.xdata)**2+np.abs(y-event.ydata)**2).argmin()+1
    fig1 = plt.figure(1)
    plt.clf()
    props = dict(alpha=0.8, edgecolors='none' )
    plt.scatter(x,y,c=xrf,s=50,marker='s',**props)
    plt.axes().set_aspect('equal')
    plt.gca().invert_yaxis()
    plt.scatter(event.xdata,event.ydata,zorder=1)
    plt.draw()
    display_frame(index)


def show_diff_data(sid,element,det_name='merlin1',fermat_flag=False, save_flag=False,zp_flag=False):

    #scan_num = sys.argv[1]
    #sid = int(scan_num)
    global elem
    elem = element
    global scan_num
    #print('start')
    '''
    #scan_num = np.str(sid)
    #scan_id, df = _load_scan(sid, fill_events=False)
    scan_num = np.str(sid)
    df = db.get_table(db[sid],fill=False)
    num_frame, count = np.shape(df)
    hdr = db[sid]
    #fermat_flag = int(sys.argv[3])
    #elem = sys.argv[2]
    #det_name = sys.argv[4]
    '''
    scan_num = str(sid)
    #print(scan_num)
    hdr = db[sid]
    #print(hdr)
    bl = db[sid].table('baseline')
    #print('done baseline')
    df = db.get_table(db[sid],fill=False)
    #print('get df')
    #images = db.get_images(db[sid],name=det_name)
    h = db[sid]
    #print('get h')
    
    #ic = np.asarray(df['sclr1_ch4'])
    ic = np.squeeze(np.asarray(list(hdr.data('sclr1_ch4'))))
    num_frame = np.size(ic)
    print(np.shape(ic))
    '''
    img = list(h.data(det_name))
    
    for i in range(num_frame):
        try:
            tmp = np.array(img[i])
            #print(i)
            if i == 0:
                tt, nnx,nny = np.shape(tmp)
                print(np.shape(tmp))
                images = np.zeros((num_frame,nnx,nny))
            images[i] = tmp
        except:
            break
    if i < num_frame-1:
        n_missing = num_frame - i
        images[20+n_missing:num_frame] = images[20:i].copy()
    '''
    images = np.array(np.squeeze(list(h.data(det_name))))

    print('image size:',np.shape(images))
    #images = np.array(np.squeeze(images))
    #plan_args = db[sid].start['plan_args']


    
    #index = np.where(ic == 0)
    #nn = np.size(index[0])
    #for i in range(nn):
    #    ii = index[0][i]
    #    ic[ii] = ic[ii-1]
    #print('done ic')
    #ic_0 = 153000

    #images = db.get_images(db[sid],name=det_name)
    #images = np.array(np.squeeze(list(hdr.data(det_name))))
    print(np.shape(images))
    num_frame,nnx,nny = np.shape(images)

    mask = np.load('/data/users/2026Q1/Shimao_2026Q1/diff_1/mask.npy')
    #mask = np.load('/data/users/2025Q2/Liu_2025Q2/diff_3_O3NCM_3.4V/mask.npy')

    for i in range(num_frame):
        if np.mod(i,500) ==0:
            print('load frame ',i, '/', num_frame)
        #t = np.flipud(images.get_frame(i)[0]).T
        t = np.flipud(images[i,:,:]).T
        t = t  #* mask
        t = t*ic[0] / ic[i]
       

        if i == 0:
            nx,ny = np.shape(t)
            global diff_array
            diff_array = np.zeros((nx,ny,num_frame))
            #diff_array = np.zeros((nx,248,num_frame))
            #diff_array_d = np.zeros((nx,245,num_frame))

        #diff_array[:,:,i] = np.flipud(t) #* mask
        tmp = np.flipud(t) #* mask
        #diff_array[:,:,i] = tmp[:,245:]
        #diff_array_d[:,:,i] = tmp[:,:245]
        diff_array[:,:,i] = np.flipud(tmp) *mask
    del images
    for i in range(num_frame):
        if i == 0:
            global roi
            #roi = np.zeros(num_frame)
            roi = np.zeros(num_frame)
            #roi_d = np.zeros(num_frame)
        #roi[i] = np.sum(diff_array[:,:,i])
        roi[i] = np.sum(diff_array[:,:,i])
        #roi_d[i] = np.sum(diff_array_d[:,:,i])

    global xrf
    if elem in df:
        xrf = np.asarray(df[elem])
    else:
        xrf = np.squeeze(np.asfarray(list(h.data('Det1_'+elem)))+np.asfarray(list(h.data('Det2_'+elem)))+np.asfarray(list(h.data('Det3_'+elem))))

        #xrf = np.asfarray(eval('df.Det1_'+elem)) + np.asarray(eval('df.Det2_'+elem)) + np.asarray(eval('df.Det3_'+elem))
    #print(np.shape(xrf),np.shape(ic))
    xrf = xrf * ic[0] / (ic + 1.e-9)


    if fermat_flag:
        x = np.asarray(df.dssx)
        y = np.asarray(df.dssy)
        fig = plt.figure(1)
        ax = fig.add_subplot(111)
        props = dict(alpha=0.8, edgecolors='none' )
        im = ax.scatter(x,y,c=xrf,s=50,marker='s',**props)
        plt.axes().set_aspect('equal')
        plt.gca().invert_yaxis()

        cid = fig.canvas.mpl_connect('button_press_event', onclick_fermat)
        fig2 = plt.figure(2)
        ax2 = fig2.add_subplot(111)
    else:
        global y_data
        global x_data
        global num_x
        global num_y
        try:
            hdr.start.plan_args['num']
            #print(hdr.start.plan_args['num'])
            xrf = np.reshape(xrf,(1,hdr.start.plan_args['num']))
            roi = np.reshape(roi,(1,hdr.start.plan_args['num']))
            #roi_d = np.reshape(roi_d,(1,hdr.start.plan_args['num']))
        except:
            if hdr.start.plan_name == 'grid_scan':
                xrf = np.reshape(xrf,(hdr.start.shape[0],hdr.start.shape[1]))
                roi = np.reshape(roi,(hdr.start.shape[0],hdr.start.shape[1]))
                x_data = df[hdr.start.motors[1]]
                y_data = df[hdr.start.motors[0]]
                num_x = hdr.start.shape[0]
                num_y = hdr.start.shape[1]
                #roi_d = np.reshape(roi_d,(hdr.start.shape[0],hdr.start.shape[1]))
                extent = (hdr.start.plan_args['args'][2], hdr.start.plan_args['args'][1],hdr.start.plan_args['args'][6],hdr.start.plan_args['args'][5])
            elif hdr.start.plan_name == 'FlyPlan2D':
                xrf = np.reshape(xrf,(hdr.start.shape[1],hdr.start.shape[0]))
                roi = np.reshape(roi,(hdr.start.shape[1],hdr.start.shape[0]))
                #roi_r = np.reshape(roi_r,(hdr.start.shape[1],hdr.start.shape[0]))
                #roi_l = np.reshape(roi_l,(hdr.start.shape[1],hdr.start.shape[0]))
                #roi_d = np.reshape(roi_d,(hdr.start.shape[1],hdr.start.shape[0]))
                extent = (hdr.start.plan_args['scan_end1'], hdr.start.plan_args['scan_start1'],hdr.start.plan_args['scan_end2'],hdr.start.plan_args['scan_start2'])
                #x_motor = hdr['motor1']
                if zp_flag:
                    x_motor = hdr.start['motors'][0]
                    x_data = np.asarray(df[x_motor])
                    #y_motor = hdr['motor2']
                    y_motor = hdr.start['motors'][1]
                    y_data = np.asarray(df[y_motor])
                else:
                    x_motor = hdr.start['motors'][0]
                    x_data = np.asarray(df[x_motor])
                    y_motor = hdr.start['motors'][1]
                    y_data = np.asarray(df[y_motor])
                #global num_x
                #global num_y
                num_x = hdr.start.shape[0]
                num_y = hdr.start.shape[1]
            else:
                #x_motor = hdr['motor1']
                #x_data = np.asarray(df[x_motor])
                #y_motor = hdr['motor2']
                #y_data = np.asarray(df[y_motor])
                x_data,y_data = get_scan_positions(hdr)
                xrf = np.reshape(xrf,(hdr.start.shape[1],hdr.start.shape[0]))
                roi = np.reshape(roi,(hdr.start.shape[1],hdr.start.shape[0]))
                #roi_d = np.reshape(roi_d,(hdr.start.shape[1],hdr.start.shape[0]))
                extent = (np.nanmin(x_data), np.nanmax(x_data),np.nanmax(y_data), np.nanmin(y_data))
                num_x = hdr.start['shape'][0]
                num_y = hdr.start['shape'][1]
                #print('no num')


    fn = '/data/users/2026Q1/Shimao_2026Q1/diff_8/'
    
    if not os.path.exists(fn):
        os.makedirs(fn)
    
    
    if save_flag:
        #print('saving data')
        io.imsave(fn+scan_num+'_roi.tif',roi.astype(np.float32))
        #io.imsave(fn+scan_num+'_roi_down.tif',roi_d.astype(np.float32))
        io.imsave(fn+scan_num+'_xrf.tif',xrf.astype(np.float32))
        io.imsave(fn+scan_num+'_diff_data.tif',diff_array.astype(np.float16))
        #io.imsave(fn+scan_num+'_diff_data_down.tif',diff_array_d.astype(np.float32))
    """
    fig=plt.figure(0)
    ax = fig.add_subplot(111)
    im = ax.imshow(xrf,interpolation = 'none',aspect='auto')
    plt.title('#'+scan_num +' '+ elem)
    global w
    w = xrf.shape[1]
    cid = fig.canvas.mpl_connect('button_press_event', onclick)

    fig1 = plt.figure(1)
    ax1 = fig1.add_subplot(111)
    im = ax1.imshow(roi,interpolation = 'none',aspect='auto')
    plt.title('#'+scan_num+' Diff ROI')
    #w = roi.shape[1]
    cid = fig1.canvas.mpl_connect('button_press_event', onclick_roi)


    fig3 = plt.figure(3)
    ax3 = fig3.add_subplot(111)


    plt.show()

    """



