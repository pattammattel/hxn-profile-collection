print(f"Loading {__file__!r} ...")

import logging
import scipy
import pickle
import json
import math
import numpy as np
import pandas as pd
#mpl.use('agg')

from scipy.optimize import curve_fit, minimize
from epics import caget, caput
from PyQt5 import  QtTest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
from hxntools.scan_info import get_scan_positions

def erfunc3(z,a,b,c,d,e):
    return d+e*z+c*(scipy.special.erf((z-a)/(b*np.sqrt(2.0)))+1.0)
def erfunc4(z,a,b,c,d,e):
    return d+e*z+c*(1.0-scipy.special.erf((z-a)/(b*np.sqrt(2.0))))

def erfunc1(z,a,b,c):
    return c*(scipy.special.erf((z-a)/(b*np.sqrt(2.0)))+1.0)
def erfunc2(z,a,b,c):
    return c*(1.0-scipy.special.erf((z-a)/(b*np.sqrt(2.0))))
def sicifunc(z,a,b,c):
    si, ci = scipy.special.sici(2.0*b*(z-a))
    #return c*((-1.0+np.cos(2.0*b*(a-z))+2.0*b*(a-z)*si)/(2.0*(b*b)*(z-a))+np.pi/(2.0*b))*b
    return c*(-scipy.sinc(b*(z-a)/np.pi)*scipy.sin(b*(z-a))+si+np.pi/2.0)/np.pi
def squarefunc(z,c,a1,b1,a2,b2):
    return c*(scipy.special.erf((z-a1)/(b1*np.sqrt(2.0)))-scipy.special.erf((z-a2)/(b2*np.sqrt(2.0))))

def is_close_to_reference(value, reference, rel_tol=0.05):
    # Check if the value is within 5% (default) relative tolerance of the reference
    if not math.isclose(value, reference, rel_tol=rel_tol):
        raise ValueError(f"{value} is not within 5% of {reference}")
    

def get_xrf_data(h,elem ="Cr",mon ='sclr1_ch4'):

    """returns scan positions and xrf data of 1d scans
        useful for line fitting, erf etc."""
    
    sid = h.start['scan_id']
    df2 = h.table()

        
    x_motor = h.start['motors']
    try:
        xdata = np.array(df2[x_motor[0]])
    except:
        xdata = np.array(get_scan_positions(h))

    if xdata.ndim>1:
        raise ValueError ("not a 1d scan")

    channels = [1,2,3]
    xrf = None
    for i in channels:
        fluo_data = np.array(list(h.data('Det%d_'%i+elem))).squeeze()
        if xrf is None:
            xrf = fluo_data.copy()
        else:
            xrf = xrf + fluo_data
    
    if mon is not None:
        mon_data = np.array(list(h.data(mon))).squeeze()
        xrf = xrf/mon_data
        xrf[xrf==np.nan] = np.nanmean(xrf)#patch for ic3 returns zero
        xrf[xrf==np.inf] = np.nanmean(xrf)#patch for ic3 returns zero
        
    return xdata,xrf

def erf_fit(sid, elem, mon='sclr1_ch4', linear_flag=True,show_figure = True):
    h = db[sid]
    sid = h.start['scan_id']
    xdata, ydata = get_xrf_data(h,
                            elem = elem,
                            mon = mon)
    ydata[0] = ydata[1] #patch for drop point issue
    ydata[-1] = ydata[-2]#patch for drop point issue
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    if show_figure:
        plt.figure()
        plt.plot(xdata,ydata,'bo')
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc1,xdata,ydata, p0=[edge_pos,0.05,0.5])
            fit_data=erfunc1(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc3,xdata,ydata, p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc3(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc2,xdata,ydata,p0=[edge_pos,0.05,0.5])
            fit_data=erfunc2(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc4,xdata,ydata,p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc4(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    if show_figure:
        plt.plot(xdata,fit_data, 'r')
        plt.title(f'{sid = }, edge = {popt[0] :.3f}, FWHM = {popt[1]*2354.8 :.2f} nm')
    return (popt[0],popt[1]*2.3548*1000.0)

def erf_fit_to_delete(sid, elem, mon='sclr1_ch4', linear_flag=True):
    h = db[sid]
    sid = h.start['scan_id']
    df2 = h.table()
    channels = [1,2,3]
    xrf = None
    for i in channels:
        fluo_data = np.array(list(h.data('Det%d_'%i+elem))).squeeze()
        if xrf is None:
            xrf = fluo_data.copy()
        else:
            xrf = xrf + fluo_data
    #xrf = np.array(df2['Det2_' + elem]+df2['Det1_' + elem] + df2['Det3_' + elem])

    xrf[xrf==np.nan] = np.nanmean(xrf)#patch for ic3 returns zero
    xrf[xrf==np.inf] = np.nanmean(xrf)#patch for ic3 returns zero

    #threshold = np.max(xrf)/10.0
    x_motor = h.start['motors']
    try:
        xdata = np.array(df2[x_motor[0]])
    except:
        xdata = get_scan_positions(h)
    ydata = xrf
    ydata[0] = ydata[1] #patch for drop point issue
    ydata[-1] = ydata[-2]#patch for drop point issue
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    plt.figure()
    plt.plot(xdata,ydata,'bo')
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc1,xdata,ydata, p0=[edge_pos,0.05,0.5])
            fit_data=erfunc1(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc3,xdata,ydata, p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc3(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc2,xdata,ydata,p0=[edge_pos,0.05,0.5])
            fit_data=erfunc2(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc4,xdata,ydata,p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc4(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    plt.plot(xdata,fit_data)
    plt.title(f'{sid = }, edge = {popt[0] :.3f}, FWHM = {popt[1]*2354.8 :.2f} nm')
    return (popt[0],popt[1]*2.3548*1000.0)


def get_knife_edge_data(sid,elem,z_mtr_name, mon='sclr1_ch4',linear_flag=True):
    
    """ returns knife edge scan data and fit along with z_motor position """

    h = db[sid]
    bl = h.table('baseline')
    z_mtr_pos = bl[z_mtr_name].to_numpy()[0]
    xdata, ydata = get_xrf_data(h,
                                elem = elem,
                                mon = mon)
    
    ydata[0] = ydata[1] #patch for drop point issue
    ydata[-1] = ydata[-2]#patch for drop point issue
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc1,xdata,ydata, p0=[edge_pos,0.05,0.5])
            fit_data=erfunc1(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc3,xdata,ydata, p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc3(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc2,xdata,ydata,p0=[edge_pos,0.05,0.5])
            fit_data=erfunc2(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc4,xdata,ydata,p0=[edge_pos,0.05,0.5,0,0])
            fit_data=erfunc4(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);

    return popt[0],popt[1]*2.3548*1000.0,xdata,ydata,fit_data, z_mtr_pos


def sici_fit(sid,elem,mon='sclr1_ch4',linear_flag=True):
    h=db[sid]
    sid=h['start']['scan_id']
    df=h.table()
    mots=h.start['motors']
    xdata=df[mots[0]]
    xdata=np.array(xdata,dtype=float)
    ydata=(df['Det1_'+elem]+df['Det2_'+elem]+df['Det3_'+elem])/df[mon]
    ydata=np.array(ydata,dtype=float)
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    plt.figure()
    plt.plot(xdata,ydata,'bo')
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(sicifunc,xdata,ydata, p0=[edge_pos,0.05,1/np.pi])
            fit_data=sicifunc(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(sicifunc,xdata,ydata, p0=[edge_pos,0.05,1/np.pi,0,0])
            fit_data=sicifunc(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(sicifunc,-xdata,ydata,p0=[-edge_pos,0.05,1/np.pi])
            fit_data=sicifunc(-xdata,-popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(sicifunc,-xdata,ydata,p0=[-edge_pos,0.05,1/np.pi,0,0])
            fit_data=sicifunc(-xdata,-popt[0],popt[1],popt[2],popt[3],popt[4]);
    plt.plot(xdata,fit_data)
    plt.title('sid= %d edge = %.3f, FWHM = %.2f nm' % (sid,popt[0], 1.39156*2*1000.0/popt[1]))
    return (popt[0],1.39156*2*1000.0/popt[1])


def find_double_edge2(xdata,ydata):
    l = np.size(ydata)
    der = np.zeros(l-1)
    for i in range(l-1):
        der[i]=ydata[i+1]-ydata[i]
    ind1 = scipy.argmax(der)
    ind2 = scipy.argmin(der)
    return(xdata[ind1],xdata[ind2])

def square_fit(sid,elem,mon='sclr1_ch4',linear_flag=True):

    h=db[sid]
    sid=h['start']['scan_id']
    df=h.table()
    mots=h.start['motors']

    #threshold = np.max(xrf)/10.0
    x_motor = h.start['motors']
    try:
        xdata = np.array(df[x_motor[0]])
    except:
        xdata = get_scan_positions(h)
        
    #x = get_scan_positions(h)
    #xdata=df[mots[0]]
    #xdata=np.array(xdata,dtype=float)
    #df[mon][df[mon]==np.inf] = np.mean(df[mon])
    #ydata=(df['Det1_'+elem]+df['Det2_'+elem]+df['Det3_'+elem])/(df[mon]+1e-8)

    channels = [1,2,3]
    xrf = None
    for i in channels:
        fluo_data = np.array(list(h.data('Det%d_'%i+elem))).squeeze()
        if xrf is None:
            xrf = fluo_data.copy()
        else:
            xrf = xrf + fluo_data
    #xrf = np.array(df2['Det2_' + elem]+df2['Det1_' + elem] + df2['Det3_' + elem])

    xrf[xrf==np.nan] = np.nanmean(xrf)#patch for ic3 returns zero
    xrf[xrf==np.inf] = np.nanmean(xrf)#patch for ic3 returns zero
    ydata=xrf
    ydata=np.array(ydata,dtype=float)
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    plt.figure()
    plt.plot(xdata,ydata,'bo')
    edge_pos_1, edge_pos_2 = find_double_edge(xdata,ydata,10)
    #print('sid={}  e1={}  e2={}'.format(sid,edge_pos_1,edge_pos_2))
    popt,pcov=curve_fit(squarefunc,xdata,ydata,p0=[0.5,edge_pos_1,0.1,edge_pos_2,0.1])
    fit_data=squarefunc(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);

    #print('a={} b={} c={}'.format(popt[0],popt[1],popt[2]))
    plt.plot(xdata,fit_data)
    plt.title('sid= %d cen = %.3f e1 = %.3f e2 = %.3f ' % (sid,(popt[1]+popt[3])*0.5, popt[1],popt[3]))
    plt.xlabel(mots[0])
    return (popt[1],popt[3],(popt[1]+popt[3])*0.5)
    #return(xdata, ydata, fit_data)



def data_erf_fit(sid,xdata,ydata,linear_flag=True):

    xdata=np.array(xdata,dtype=float)
    ydata=np.array(ydata,dtype=float)
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    plt.figure()
    plt.plot(xdata,ydata,'bo')
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc1,xdata,ydata, p0=[edge_pos,0.5,0.5])
            fit_data=erfunc1(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc3,xdata,ydata, p0=[edge_pos,0.5,0.5,0,0])
            fit_data=erfunc3(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(erfunc2,xdata,ydata,p0=[edge_pos,0.5,0.5])
            fit_data=erfunc2(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(erfunc4,xdata,ydata,p0=[edge_pos,0.5,0.5,0,0])
            fit_data=erfunc4(xdata,popt[0],popt[1],popt[2],popt[3],popt[4]);

    #print('a={} b={} c={}'.format(popt[0],popt[1],popt[2]))
    #plt.figure(1000)
    plt.plot(xdata,fit_data)
    plt.title('sid = %d, edge = %.3f, FWHM = %.2f nm' % (sid, popt[0], popt[1]*2.3548*1000.0))
    return (popt[0],popt[1]*2.3548*1000.0)
def data_sici_fit(xdata,ydata,linear_flag=True):

    xdata=np.array(xdata,dtype=float)
    ydata=np.array(ydata,dtype=float)
    y_min=np.min(ydata)
    y_max=np.max(ydata)
    ydata=(ydata-y_min)/(y_max-y_min)
    plt.figure(1000)
    plt.plot(xdata,ydata,'bo')
    y_mean = np.mean(ydata)
    half_size = int (len(ydata)/2)
    y_half_mean = np.mean(ydata[0:half_size])
    edge_pos=find_edge(xdata,ydata,10)
    if y_half_mean < y_mean:
        if linear_flag == False:
            popt,pcov=curve_fit(sicifunc,xdata,ydata, p0=[edge_pos,20,1])
            fit_data=sicifunc(xdata,popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(sicifunc,xdata,ydata, p0=[edge_pos,20,1])
            fit_data=sicifunc(xdata,popt[0],popt[1],popt[2]);
    else:
        if linear_flag == False:
            popt,pcov=curve_fit(sicifunc,-xdata,ydata,p0=[-edge_pos,20,1])
            fit_data=sicifunc(-xdata,-popt[0],popt[1],popt[2]);
        else:
            popt,pcov=curve_fit(sicifunc,-xdata,ydata,p0=[-edge_pos,20,1])
            fit_data=sicifunc(-xdata,-popt[0],popt[1],popt[2]);
    plt.plot(xdata,fit_data)
    plt.title('edge = %.3f, FWHM = %.2f nm' % (popt[0], 1.39156*2*1000.0/popt[1]))
    return (popt[0],1.39156*2*1000.0/popt[1])

def find_2D_edge(sid, axis, elem):
    df2 = db.get_table(db[sid],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    motors = db[sid].start['motors']
    x = np.array(df2[motors[0]])
    y = np.array(df2[motors[1]])
    #I0 = np.asfarray(df2.sclr1_ch4)
    I0 = np.asfarray(df2['sclr1_ch4'])
    scan_info=db[sid]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']
    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))
    #l = np.linspace(y[0],y[-1],ny)
    #s = xrf.sum(1)
    if axis == 'x':
        l = np.linspace(x[0],x[-1],nx)
        s = xrf.sum(0)
    else:
        l = np.linspace(y[0],y[-1],ny)
        s = xrf.sum(1)
    edge,fwhm = data_erf_fit(l, s)
    return edge


def find_edge(xdata,ydata,size):
    set_point=0.5
    j=int (np.ceil(size/2.0))
    l=len(ydata)
    local_mean=np.zeros(l-size)
    for i in range(l-size):
        local_mean[i]=np.mean(ydata[i:i+size])
    zdata=abs(local_mean-np.array(set_point))
    index=np.argmin(zdata)
    index=index+j
    return xdata[index]

def find_double_edge(xdata, ydata, size):
    edge_1 = find_edge(xdata, ydata, size)
    l = np.size(ydata)
    index = np.argmax(ydata)
    cen = xdata[index]
    if cen > edge_1:
        edge_2 = find_edge(xdata[index:l],ydata[index:l],size)
        #edge_2 = (cen-edge_1) + cen
        return(edge_1,edge_2)
    else:
        #edge_2 = cen - (edge_1 - cen)
        edge_2 = find_edge(xdata[1:index],ydata[1:index],size)
        return(edge_2,edge_1)

def movr_zpz1(dz):
    yield from bps.movr(zp.zpz1, dz)
    #movr(zp.zpx, dz * 3.75)
    # yield from bps.movr(zp.zpy, (-0.002)*dz) #follow the sign for corr factors
    # yield from bps.movr(zp.zpx, dz*(0.0009795))

    # For chamber at 700 mmHg
    yield from bps.movr(zp.zpy, (-0.002)*dz) #follow the sign for corr factors
    yield from bps.movr(zp.zpx, dz*(0.0009795+0.00036))

def mov_zpz1(pos):

    c_zpz1 = zp.zpz1.position
    dz = pos - c_zpz1
    yield from movr_zpz1(dz)

def mll_z_alignment(z_motor, z_start, z_end, z_num, mot, start, end, num, acq_time, elem='Pt_L',mon='sclr1_ch4',lin_flag = False):

    """usage: <mll_z_alignment(sbz,-20,20,10,dssy,-0.5,0.5,100,0.05, elem = 'Pt_L')"""

    z_pos=np.zeros(z_num+1)
    fit_size=np.zeros(z_num+1)
    z_step = (z_end - z_start)/z_num
    init_sz = z_motor.position
    mot_init = mot.position
    yield from bps.movr(z_motor, z_start)
    for i in range(z_num + 1):

        yield from fly1dpd(dets_fast_fs, mot, start, end, num, acq_time)

        edge_pos,fwhm=erf_fit(-1,elem,mon,linear_flag=lin_flag)
        fit_size[i]= fwhm
        z_pos[i]=z_motor.position
        if abs(edge_pos)<12:
            yield from bps.mov(mot, edge_pos)
        yield from bps.movr(z_motor, z_step)
    yield from bps.mov(z_motor, init_sz)
    yield from bps.mov(mot, mot_init)
    plt.figure()
    plt.plot(z_pos,fit_size,'bo')
    plt.xlabel(z_motor.name)


def hmll_z_alignment(z_start, z_end, z_num, start, end, num, acq_time, elem='Pt_L',mon='sclr1_ch4'):

    """ usage:hmll_z_alignment(-10, 10, 10, -0.5, 0.5, 100, 0.05) """

    yield from mll_z_alignment(hz, 
                               z_start, 
                               z_end, 
                               z_num, 
                               dssx, 
                               start, 
                               end, 
                               num, 
                               acq_time, 
                               elem=elem,
                               mon='mon')
    

def vmll_z_alignment(z_start, z_end, z_num, start, end, num, acq_time, elem='Pt_L',mon='sclr1_ch4'):
    """ usage:vmll_z_alignment(-10, 10, 10, -0.5, 0.5, 100, 0.05) """
    
    yield from mll_z_alignment(vz, 
                               z_start, 
                               z_end, 
                               z_num, 
                               dssy, 
                               start, 
                               end, 
                               num, 
                               acq_time, 
                               elem=elem,
                               mon='mon')

def mll_vchi_alignment(vchi_start, vchi_end, vchi_num, mot, start, end, num, acq_time, elem='Pt_L',mon='sclr1_ch4'):
    vchi_pos = np.zeros(vchi_num+1)
    fit_size = np.zeros(vchi_num+1)
    vchi_step = (vchi_end - vchi_start)/vchi_num
    init_vchi = vmll.vchi.position
    yield from bps.movr(vmll.vchi, vchi_start)
    for i in range(vchi_num + 1):
        yield from fly1dpd(dets_fast_fs, mot, start, end, num, acq_time,dead_time=0.002)
        edge_pos,fwhm=erf_fit(-1,elem,mon)
        fit_size[i]=fwhm
        vchi_pos[i]=vmll.vchi.position
        yield from bps.movr(vmll.vchi, vchi_step)
    yield from bps.mov(vmll.vchi, init_vchi)
    plt.figure()
    plt.plot(vchi_pos,fit_size,'bo')
    plt.xlabel('vchi')

    fig, ax = plt.subplots()
    ax.plot(vchi_pos,fit_size,'bo')
    ax.set_xlabel('vchi')
    ax.set_xticks(vchi_pos)
    ax.set_yticks(fit_size)
    plt.show()


def zp_z_alignment(z_start, z_end, z_num, mot, start, end, num, acq_time, 
                   elem=' ',linFlag = False,mon='sclr1_ch4'):

    print("moves the zone plate relatively and find the focus with a linescan at each position")

    z_pos=np.zeros(z_num+1)
    fit_size=np.zeros(z_num+1)
    z_step = (z_end - z_start)/z_num
    init_sz = zp.zpz1.position

    yield from movr_zpz1(z_start)
    for i in range(z_num + 1):

        yield from fly1dpd(dets_fast_fs, mot, start, end, num, acq_time)
        yield from bps.sleep(2)
        edge_pos,fwhm=erf_fit(-1,elem,mon,linear_flag=linFlag)
        #3yield from bps.mov(mot,edge_pos)
        yield from bps.sleep(1)
        fit_size[i]= fwhm
        z_pos[i]=zp.zpz1.position
        yield from movr_zpz1(z_step)
        merlin1.unstage()
        xspress3.unstage()
        
    yield from movr_zpz1(-1*z_end)
    #fig, ax = plt.subplots()
    fig = plt.figure()
    plt.plot(z_pos,fit_size,'bo')
    #ax.set_xlabel('zpz1')
    plt_update_figure()
    yield from bps.sleep(1)


def zp_z_alignment2(z_start, z_end, z_num, mot, start, end, num, acq_time, 
                   elem=' ',linFlag = False,mon='sclr1_ch4'):

    print("moves the zone plate relatively and find the focus with a linescan at each position")

    init_sz = zp.zpz1.position
    z_pos=np.linspace(init_sz+z_start,init_sz+z_end,z_num+1)
    fit_size=np.zeros(z_num+1)
        
    for pos in z_pos:
        yield from mov_zpz1(pos)
        yield from fly1dpd(dets_fast_fs, mot, start, end, num, acq_time)
        edge_pos,fwhm=erf_fit(-1,elem,mon,linear_flag=linFlag)
        yield from bps.sleep(1)
        fit_size[i]= fwhm
        
    yield from mov_zpz1(init_sz)
    #fig, ax = plt.subplots()
    fig = plt.figure()
    plt.plot(z_pos,fit_size,'bo')
    #ax.set_xlabel('zpz1')
    fig.canvas.manager.show()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.show()
    yield from bps.sleep(1)


def plot_z_focus_results(first_sid = -11, last_sid = -1, z_mtr ='zpz1',
                        elem = "Cr",lin_flag = False,mon='sclr1_ch4'):
    
    num_scans = abs(first_sid-last_sid)+1
    sid_list =  np.linspace(first_sid,
                            last_sid,
                            num_scans, 
                            dtype = int)
    
    z_pos_list = np.zeros_like(sid_list, dtype = float)
    fwhm_list = np.zeros_like(sid_list, dtype = float)
    
    print(sid_list)
    
    
    num_rows = 4
    num_cols = num_scans//num_rows
    if num_scans%num_rows != 0:
        num_cols+=1

    print(num_cols)

    fig, axs = plt.subplots(num_rows, num_cols)
    axs = axs.ravel()


    for i, sid in enumerate(sid_list):
        edge_pos,fwhm,x_data,y_data,y_fit,z_pos = get_knife_edge_data(int(sid),
                                                                      elem,
                                                                      z_mtr,
                                                                      mon='sclr1_ch4',
                                                                      linear_flag=True)
        
        axs[i].plot(x_data,y_data, 'bo')
        axs[i].plot(x_data, y_fit, 'r-')
        axs[i].set_xlabel("motor positions")
        axs[i].set_ylabel("norm. intensity")
        #axs[i].set_title(f"{z_mtr}_pos ={z_pos = :.3f}, {edge_pos = :.3f}, {fwhm = :.2f}")
        #plt.show()
        
        print(z_pos)
        z_pos_list[i] = z_pos
        fwhm_list[i] = fwhm

    plt.figure()
    plt.plot(z_pos_list,fwhm_list, 'bo')
    #plt.xlabel(f"{z_mtr}_pos")
    plt.ylabel("FWHM")
    plt.show()


def pos2angle(col,row):

    # old Dexelar calibration

    pix = 74.8
    R = 2.315e5
    th1 = 0.7617
    phi1 = 3.0366
    th2 = 0.1796
    phi2 = 2.5335
    phi3 = -0.1246
    alpha = 8.5*np.pi/180

    # new Dexelar calibration at position 0
    pix = 74.8
    R = 2.6244e5
    th1 = 0.7685
    phi1 = 3.0238
    th2 = 0.1398
    phi2 = 2.9292
    phi3 = -0.1486
    alpha = 8.5*np.pi/180

    det_orig = R*np.array([np.sin(th1)*np.cos(phi1),np.sin(th1)*np.sin(phi1),np.cos(th1)])
    det_z = np.array([np.sin(th2)*np.cos(phi2), np.sin(th2)*np.sin(phi2),np.cos(th2)])
    th3 = np.arctan(-1.0/(np.cos(phi2-phi3)*np.tan(th2)))
    det_x = np.array([np.sin(th3)*np.cos(phi3),np.sin(th3)*np.sin(phi3),np.cos(th3)])
    det_y = np.cross(det_z,det_x)

    pos = det_orig + (col - 1)*pix*det_x + (row -1)*pix*det_y

    M = np.array([[np.cos(alpha),-np.sin(alpha),0],[np.sin(alpha), np.cos(alpha),0],[0,0,1]])

    pos = np.dot(M,pos)

    tth = np.arccos(pos[2]/np.sqrt(pos[0]**2+pos[1]**2+pos[2]**2))*180.0/np.pi
    delta = np.arcsin(pos[1]/np.sqrt(pos[0]**2+pos[1]**2+pos[2]**2))*180.0/np.pi
    pos_xy = pos*np.array([1,0,1])
    gamma = np.arccos(pos[2]/np.sqrt(pos_xy[0]**2+pos_xy[1]**2+pos_xy[2]**2))*180.0/np.pi
    return (np.round(gamma,1),np.round(delta,1),np.round(tth,1))

def get_fluo_data(sid,elem):
    h = db[sid]

    channels = [1,2,3]
    xrf = None
    for i in channels:
        fluo_data = np.array(list(h.data('Det%d_'%i+elem))).squeeze()
        if xrf is None:
            xrf = fluo_data.copy()
        else:
            xrf = xrf + fluo_data
    return get_scan_positions(h),xrf


def return_line_center(sid,elem='Cr',threshold=0.2, neg_flag=0):
    h = db[sid]

    df2 = h.table()

    channels = [1,2,3]
    xrf = None
    for i in channels:
        fluo_data = np.array(list(h.data('Det%d_'%i+elem))).squeeze()
        if xrf is None:
            xrf = fluo_data.copy()
        else:
            xrf = xrf + fluo_data
    #xrf = np.array(df2['Det2_' + elem]+df2['Det1_' + elem] + df2['Det3_' + elem])

    xrf[xrf==np.nan] = np.nanmean(xrf)#patch for ic3 returns zero
    xrf[xrf==np.inf] = np.nanmean(xrf)#patch for ic3 returns zero

    #threshold = np.max(xrf)/10.0
    x_motor = h.start['motors']

    if len(x_motor)>1:
        raise ValueError (f"Require a Line Scan: num motors = {len(x_motor)}")

    try:
        x = np.array(df2[x_motor])
    except:
        x = get_scan_positions(h)
    if neg_flag == 1:
        xrf = xrf * -1
        xrf = xrf - np.min(xrf)

    #print(x)
    #print(xrf)
    xrf[xrf<(np.max(xrf)*threshold)] = 0.
    #index = np.where(xrf == 0.)
    #xrf[:index[0][0]] = 0.
    xrf[xrf>=(np.max(xrf)*threshold)] = 1.
    mc = find_mass_center_1d(xrf[:-2],x[:-2])
    return mc


def return_tip_pos(sid,elem='Cr'):
    h = db[sid]

    df2 = h.table()
    xrf = np.array(df2['Det2_' + elem]+df2['Det1_' + elem] + df2['Det3_' + elem])
    threshold = np.max(xrf)/10.0
    x_motor = h.start['motor']
    x = np.array(df2[x_motor])
    #print(x)
    #print(xrf)
    #xrf[xrf<(np.max(xrf)*0.5)] = 0.
    #xrf[xrf>=(np.max(xrf)*0.5)] = 1.
    #mc = find_mass_center_1d(xrf,x)
    xrf_d = np.diff(xrf)
    #peak_index = np.where(xrf_d == np.max(xrf_d))
    peak_index = np.where(xrf == np.max(xrf))
    #print(x[peak_index[0][0]+1])
    return x[peak_index[0][0]+1]


def zp_rot_alignment(a_start, a_end, a_num, start, end, num, acq_time, 
                     elem='Pt_L', threshold = 0.5, neg_flag = 0, edge_flag = 0, move_flag=0, use_x_only = False):

    """
    <zp_rot_alignment(-30,30,5, -10, 10, 200, 0.03, 'Ni', 0.1)
    """
    a_step = (a_end - a_start)/a_num
    x = np.zeros(a_num+1)
    y = np.zeros(a_num+1)
    orig_th = zps.zpsth.position
    fig,ax = plt.subplots(1)
    plt_update_figure(fig)
    ax.set_title('Alignment 1D scans')
    for i in range(a_num+1):
        x[i] = a_start + i*a_step
        yield from bps.mov(zps.zpsth, x[i])
        yield from bps.sleep(2)
        if np.abs(x[i]) > 44.99 and not use_x_only:
            yield from fly1dpd(dets_fast_fs,zpssz,start,end,num,acq_time)
            yield from bps.sleep(0.5)
            if edge_flag:
                tmp,_ = erf_fit(-1, elem, show_figure=False)
            else:
                tmp = return_line_center(-1, elem=elem,threshold=threshold,neg_flag=neg_flag)
            points,fluo = get_fluo_data(-1,elem)
            points*= np.sin(x[i]*np.pi/180.0)
            #tmp = return_tip_pos(-1, elem=elem)
            #tmp,fwhm = erf_fit(-1,elem = elem,linear_flag=False)
            y[i] = tmp*np.sin(x[i]*np.pi/180.0)
        else:
            yield from fly1dpd(dets_fast_fs,zpssx,start,end,num,acq_time)
            yield from bps.sleep(0.5)
            if edge_flag:
                tmp,_ = erf_fit(-1, elem, show_figure=False)
            else:
                tmp = return_line_center(-1, elem=elem,threshold=threshold,neg_flag=neg_flag)
            points,fluo = get_fluo_data(-1,elem)
            points*= np.cos(x[i]*np.pi/180.0)
            #tmp = return_tip_pos(-1, elem=elem)
            #tmp,fwhm = erf_fit(-1,elem = elem,linear_flag=False)
            y[i] = tmp*np.cos(x[i]*np.pi/180.0)
        print('y=',y[i])
        ax.plot(points,fluo)
        plt_update_figure(fig)
    y = -1*np.array(y)
    x = np.array(x)
    r0, dr, offset = rot_fit_2(x,y)
    dx = -dr*np.sin(offset*np.pi/180)
    dz = -dr*np.cos(offset*np.pi/180)

    print(f'{dx = :.4f} um,   {dz = :.4f} um')

    print(f'MOVE relative: smarx = {dx :.1f} um, smarz = {dz :.1f} um')
    print('Optional move relative: zpsx %.4f mm, zpsz %.4f mm'%(-r0/1000,-dz/1000))

    yield from bps.mov(zps.zpsth, orig_th)

    if move_flag:
        yield from bps.movr(zps.smarx, dx*1000)
        yield from bps.movr(zps.smarz, dz*1000)


    # return dx,dz

def get_zp_rot_alignment_result(scans, elem='Pt_L', threshold=0.5,
                            neg_flag=0, edge_flag=0, skip_scans=None, plot_flag=True):
    """
    Compute dx and dz from rotation alignment scans.
    Supports relative scan numbers (e.g., -10 means scans [-10 ... -1]).

    Parameters
    ----------
    scans : list[int] or int
        - List of scan numbers, e.g. [401, 402, 403]
        - Or a single negative integer, e.g. -10, meaning [-10, -9, ..., -1]
    elem : str
        Element line to analyze.
    threshold, neg_flag, edge_flag : analysis parameters.
    skip_scans : list[int], optional
        List of scan numbers to skip.
    plot_flag : bool
        If True, show plots.

    Returns
    -------
    dx, dz : tuple of float
        Calculated alignment offsets (µm).
    """

    # --- interpret scans ---
    if isinstance(scans, int):
        if scans < 0:
            scan_numbers = list(range(scans, 0))  # e.g. -10 -> [-10, -9, ..., -1]
        else:
            scan_numbers = [scans]
    else:
        scan_numbers = list(scans)

    if skip_scans is None:
        skip_scans = []

    used_scans = [s for s in scan_numbers if s not in skip_scans]

    if len(used_scans) < 3:
        raise ValueError("Need at least 3 valid scans to fit rotation alignment.")

    x = []
    y = []

    if plot_flag:
        fig, ax = plt.subplots()
        ax.set_title(f"Rotation alignment (elem={elem})")
        ax.set_xlabel("Position (µm)")
        ax.set_ylabel(f"{elem} fluorescence (a.u.)")

    for sn in used_scans:
        # Get rotation angle from scan metadata or naming convention
        h = db[sn]
        angle = h.table("baseline")['zpsth'].values[0]
        #angle = get_scan_angle(sn)  # user-defined helper

        # Extract fluorescence data and compute y-value
        if edge_flag:
            tmp, _ = erf_fit(sn, elem)
        else:
            tmp = return_line_center(sn, elem=elem, threshold=threshold, neg_flag=neg_flag)

        points, fluo = get_fluo_data(sn, elem)
        points = np.array(points)
        fluo = np.array(fluo)

        proj = np.sin(np.deg2rad(angle)) if np.abs(angle) > 44.99 else np.cos(np.deg2rad(angle))
        y_val = tmp * proj

        x.append(angle)
        y.append(y_val)

        if plot_flag:
            ax.plot(points * proj, fluo, label=f"Scan {sn} (θ={angle:.1f}°)")

    x = np.array(x)
    y = -1 * np.array(y)

    r0, dr, offset = rot_fit_2(x, y)

    dx = -dr * np.sin(np.deg2rad(offset))
    dz = -dr * np.cos(np.deg2rad(offset))

    print(f"\nResults based on scans {used_scans}:")
    print(f"  dx = {dx:.4f} µm")
    print(f"  dz = {dz:.4f} µm")
    print(f"  r0 = {r0:.4f}, offset = {offset:.2f}°")

    if plot_flag:
        ax.legend()
        plt.show()

    return dx, dz

def apply_zp_rot_algn_corr(dx, dz):

    yield from bps.movr(smarx, dx, smarz, dz, zps.zpsx, -0.001*dx)


def zp_rot_scan(a_start, a_end, a_num, start, end, num, acq_time, 
                     elem='Pt_L', threshold = 0.5, neg_flag = 0, move_flag=0):

    """
    <zp_rot_alignment(-30,30,5, -10, 10, 200, 0.03, 'Ni', 0.1)
    """
    a_step = (a_end - a_start)/a_num
    x = np.zeros(a_num+1)
    y = np.zeros(a_num+1)
    orig_th = zps.zpsth.position
    fig,ax = plt.subplots(1)
    plt_update_figure(fig)
    ax.set_title('Alignment 1D scans')
    for i in range(a_num+1):
        x[i] = a_start + i*a_step
        yield from bps.mov(zps.zpsth, x[i])
        yield from bps.sleep(2)
        if np.abs(x[i]) > 44.99:
            yield from fly1dpd(dets_fast,zpssz,start,end,num,acq_time)
            yield from bps.sleep(0.5)
            tmp = return_line_center(-1, elem=elem,threshold=threshold,neg_flag=neg_flag)
            points,fluo = get_fluo_data(-1,elem)
            points*= np.sin(x[i]*np.pi/180.0)
            #tmp = return_tip_pos(-1, elem=elem)
            #tmp,fwhm = erf_fit(-1,elem = elem,linear_flag=False)
            y[i] = tmp*np.sin(x[i]*np.pi/180.0)
        else:
            yield from fly1dpd(dets_fast,zpssx,start,end,num,acq_time)
            yield from bps.sleep(0.5)
            tmp = return_line_center(-1,elem=elem,threshold=threshold,neg_flag=neg_flag )
            points,fluo = get_fluo_data(-1,elem)
            points*= np.cos(x[i]*np.pi/180.0)
            #tmp = return_tip_pos(-1, elem=elem)
            #tmp,fwhm = erf_fit(-1,elem = elem,linear_flag=False)
            y[i] = tmp*np.cos(x[i]*np.pi/180.0)
        print('y=',y[i])
        ax.plot(points,fluo)
        plt_update_figure(fig)
    y = -1*np.array(y)
    x = np.array(x)
    r0, dr, offset = rot_fit_2(x,y)
    yield from bps.mov(zps.zpsth, orig_th)
    dx = -dr*np.sin(offset*np.pi/180)
    dz = -dr*np.cos(offset*np.pi/180)

    print(f'{dx = :.4f} um,   {dz = :.4f} um')

    print(f'MOVE relative: smarx = {dx :.1f} um, smarz = {dz :.1f} um')
    print('Optional move relative: zpsx %.4f mm, zpsz %.4f mm'%(-r0/1000,-dz/1000))

    if move_flag:
        yield from bps.movr(zps.smarx, dx*1000)
        yield from bps.movr(zps.smarz, dz*1000)


def calc_rot_alignment(first_sid = -10, last_sid =-1, elem = "Cr"):

    pass


def mll_rot_alignment(a_start, a_end, a_num, start, end, num, acq_time, elem='Pt_L', move_flag=0, threshold = 0.5):

    """
    Usage <mll_rot_alignment(-30,30,6,-15,15,100,0.05,'W_L')

    """

        
    th_init = smlld.dsth.position
    y_init = dssy.position
    #y_init = -0.5 #remove this temp.
    a_step = (a_end - a_start)/a_num
    x = np.zeros(a_num+1)
    y = np.zeros(a_num+1)
    v = np.zeros(a_num+1)
    orig_th = smlld.dsth.position
    for i in range(a_num+1):
        yield from bps.mov(dssx,0)
        yield from bps.mov(dssz,0)
        x[i] = a_start + i*a_step
        yield from bps.mov(smlld.dsth, x[i])
        #angle = smlld.dsth.position
        #dy = -0.1+0.476*np.sin(np.pi*(angle*np.pi/180.0-1.26)/1.47)
        #ddy = (-0.0024*angle)-0.185
        #dy = dy+ddy
        #yield from bps.movr(dssy,dy)
        '''
        y_offset1 = sin_func(x[i], 0.110, -0.586, 7.85,1.96)
        y_offset2 = sin_func(th_init, 0.110, -0.586, 7.85,1.96)
        yield from bps.mov(dssy,y_init+y_offset1-y_offset2)
        '''

        if np.abs(x[i]) > 45.01:
            #yield from fly2dpd(dets1,dssz,start,end,num, dssy, -2,2,20,acq_time)
            #cx,cy = return_center_of_mass(-1,elem,0.3)
            #y[i] = cx*np.sin(x[i]*np.pi/180.0)
            yield from fly1dpd(dets_fast_fs,dssz,start,end,num,acq_time)
            #plot(-1, elem)
            #plt.close()
            cen = return_line_center(-1, elem=elem,threshold = threshold)
            #plt.close()
            #cen, edg1, edg2 = square_fit(-1,elem=elem)
            #cen, fwhm = erf_fit(-1,elem=elem)
            y[i] = cen*np.sin(x[i]*np.pi/180.0)
            # yield from bps.mov(dssz,cen)
        else:
            #yield from fly2dpd(dets1,dssx,start,end,num, dssy, -2,2,20,acq_time)
            #cx,cy = return_center_of_mass(-1,elem,0.3)
            #y[i] = cx*np.cos(x[i]*np.pi/180.0)
            yield from fly1dpd(dets_fast_fs,dssx,start,end,num,acq_time)
            cen = return_line_center(-1,elem=elem,threshold = threshold)
            #plot(-1, elem)
            #plt.close()
            #cen, edg1, edg2 = square_fit(-1,elem=elem)
            y[i] = cen*np.cos(x[i]*np.pi/180.0)
            #y[i] = tmp*np.cos(x[i]*np.pi/180.0)
            #y[i] = -tmp*np.cos(x[i]*np.pi/180.0)
            # yield from bps.mov(dssx,cen)

        ##v[i] = cy

        #yield from bps.mov(dssy,cy)
        #yield from fly1dpd(dets1,dssy,-2,2,100,acq_time)
        #tmp = return_line_center(-1, elem=elem)
        #yield from bps.mov(dssy,tmp)
        #v[i] = tmp
        #print('h_cen= ',y[i],'v_cen = ',v[i])
        #plot_data(-1,elem,'sclr1_ch4')
        #insertFig(note='dsth = {}'.format(check_baseline(-1,'dsth')))
        #plt.close()

    y = -1*np.array(y)
    x = np.array(x)
    r0, dr, offset= rot_fit_2(x,y)
    #insertFig(note='dsth: {} {}'.format(a_start,a_end))

    yield from bps.mov(smlld.dsth, th_init)

    dx = -dr*np.sin(offset*np.pi/180)
    dz = -dr*np.cos(offset*np.pi/180)

    #moving back to intial y position
    yield from bps.mov(dssy, y_init)
    print(f'Relative motion: {dx = :.2f}, {dz = :.2f} and sbx by {-1*dx :.2f}')

    #if move_flag:
        #yield from bps.movr(smlld.dsx, dx)
        #yield from bps.movr(smlld.dsz, dz)

    #plt.figure()
    #plt.plot(x,v)

    x = np.array(x)
    y = -np.array(y)

    # print(x)
    # print(y)
    # print(v)
    #caliFIle = open('rotCali','wb')
    #pickle.dump(y,CaliFile)
    return dx, dz


def refit_rot_align(scan_list, elem, threshold):

    y = np.zeros_like(scan_list, dtype = np.float32)
    x = np.zeros_like(scan_list, dtype = np.float32)
    
    for i, sid in enumerate(scan_list):
        h = db[int(sid)]
        cen = return_line_center(int(sid),elem=elem,threshold = 0.6)
        theta = h.table('baseline')['dsth'][1]
        x[i] = theta

        #print(f"{theta = :.2f}")

        if np.abs(theta) > 45.01:
            y[i] = cen*np.sin(x[i]*np.pi/180.0)

        else:
            y[i] = cen*np.cos(x[i]*np.pi/180.0)

        
    print(x)
    print(y)
    
    y = -1*np.array(y)
    x = np.array(x)
    r0, dr, offset = rot_fit_2(x,y)
    #insertFig(note='dsth: {} {}'.format(a_start,a_end))

    dx = -dr*np.sin(offset*np.pi/180)
    dz = -dr*np.cos(offset*np.pi/180)

    #moving back to intial y position
    print(f'{dx = :.2f}, {dz = :.2f}')


def mll_rot_alignment_2D(th_start, th_end, th_num, x_start, x_end, x_num,
                         y_start, y_end, y_num, acq_time, elem='Pt_L', move_flag=0):

    th_list = np.linspace(th_start, th_end, th_num+1)

    x = th_list
    y = np.zeros(th_num+1)
    v = np.zeros(th_num+1)
    orig_th = smlld.dsth.position
    for i, th in enumerate(th_list):
        yield from bps.mov(dssx,0, dssz,0, smlld.dsth,th)

        if np.abs(x[i]) > 45.01:
            yield from fly2dpd(dets1,
                            dssz,
                            x_start,
                            x_end,
                            x_num,
                            dssy,
                            y_start,
                            y_end,
                            y_num,
                            acq_time
                            )

            cx,cy = return_center_of_mass(-1,elem,0.5)
            y[i] = cx*np.sin(x[i]*np.pi/180.0)

        else:
            yield from fly2dpd(dets1,dssx,start,end,num, dssy, -2,2,20,acq_time)
            cx,cy = return_center_of_mass(-1,elem,0.5)
            y[i] = cx*np.cos(x[i]*np.pi/180.0)

        yield from bps.mov(dssy,cy)

    y = -1*np.array(y)
    x = np.array(x)
    r0, dr, offset = rot_fit_2(x,y)
    yield from bps.mov(smlld.dsth, 0)
    dx = -dr*np.sin(offset*np.pi/180)
    dz = -dr*np.cos(offset*np.pi/180)

    print('dx=',dx,'   ', 'dz=',dz)

    x = np.array(x)
    y = -np.array(y)
    print(x)
    print(y)
    #caliFIle = open('rotCali','wb')
    #pickle.dump(y,CaliFile)


def mll_rot_v_alignment(a_start, a_end, a_num, start, end, num, acq_time, elem='Pt_L',mon='sclr1_ch4'):
    a_step = (a_end - a_start)/a_num
    x = np.zeros(a_num+1)
    y = np.zeros(a_num+1)
    orig_th = smlld.dsth.position
    for i in range(a_num+1):
        x[i] = a_start + i*a_step
        yield from bps.mov(smlld.dsth, x[i])
        yield from fly1dpd(dets1,dssy,start,end,num,acq_time)
        edge_pos,fwhm=erf_fit(-1,elem=elem,mon=mon)
        y[i] = edge_pos
    y = -1*np.array(y)
    x = np.array(x)
    yield from bps.mov(smlld.dsth,0)
    #r0, dr, offset = rot_fit_2(x,y)
    #yield from bps.mov(smlld.dsth, 0)
    #dx = -dr*np.sin(offset*np.pi/180)
    #dz = -dr*np.cos(offset*np.pi/180)
    print(x,y)
    plt.figure()
    plt.plot(x,y)
    #print('dx=',dx,'   ', 'dz=',dz)

    return x,y

def check_baseline(sid,name):
    h = db[sid]
    bl = h.table('baseline')
    dsmll_list = ['dsx','dsy','dsz','dsth','sbx','sbz','dssx','dssy','dssz']
    vmll_list = ['vx','vy','vz','vchi','vth']
    hmll_list = ['hx','hy','hz','hth']
    mllosa_list = ['osax','osay','osaz']
    mllbs_list = ['mll_bsx','mll_bsy','mll_bsz','mll_bsth']

    if name =='dsmll':
        #print(bl[dsmll_list])
        return(bl[dsmll_list])
    elif name == 'vmll':
        #print(bl[vmll_list])
        return(bl[vmll_list])
    elif name == 'hmll':
        #print(bl[hmll_list])
        return(bl[hmll_list])
    elif name == 'mllosa':
        #print(bl[mllosa_list])
        return(bl[mllosa_list])
    elif name == 'mll':
        #print(bl[dsmll_list])
        #print(bl[vmll_list])
        #print(bl[hmll_list])
        #print(bl[mllosa_list])
        mot_pos = [bl[dsmll_list],bl[vmll_list],bl[hmll_list],bl[mllosa_list]]
        return(mot_pos)
    else:
        #print(name,bl[name])
        return(bl[name].values[0])


def check_info(sid):
    h = db[sid]
    sid = h.start['scan_id']
    scan_time = datetime.fromtimestamp(h.start['time'])
    end_time = datetime.fromtimestamp(h.stop['time'])
    scan_uid = h.start['uid']
    scan_type = h.start['plan_name']
    scan_motors = h.start['motors']
    num_motors = len(scan_motors)
    det_list = h.start['detectors']
    exp_time = h.start['exposure_time']
    print('sid = {}'.format(sid), 'uid = ', scan_uid)
    print('start time = ', scan_time, 'end time = ', end_time)
    if num_motors == 1:
        mot1 = scan_motors[0]
        s1 = h.start['scan_start1']
        e1 = h.start['scan_end1']
        n1 = h.start['num1']
        print(scan_type,mot1,s1,e1,n1,exp_time)
    elif num_motors == 2:
        mot1 = scan_motors[0]
        s1 = h.start['scan_start1']
        e1 = h.start['scan_end1']
        n1 = h.start['num1']
        mot2 = scan_motors[1]
        s2 = h.start['scan_start2']
        e2 = h.start['scan_end2']
        n2 = h.start['num2']
        print(scan_type, mot1,s1,e1,n1,mot2,s2,e2,n2,exp_time)

    print('detectors = ', det_list)

def get_scan_command(sid):
    h = db[sid]
    sid = h.start['scan_id']
    scan_type = h.start['plan_name']
    if scan_type == 'FlyPlan1D' or scan_type == 'FlyPlan2D':
        scan_motors = h.start['motors']
        num_motors = len(scan_motors)
        exp_time = h.start['exposure_time']
        if num_motors == 1:
            m1 = scan_motors[0]
            s1 = h.start['scan_start']
            e1 = h.start['scan_end']
            n1 = h.start['num']
            print (f"fly1dpd({m1},{s1:.3f},{e1:.3f},{n1},{exp_time})")
            return (f"fly1dpd({m1},{s1:.3f},{e1:.3f},{n1},{exp_time})")
        elif num_motors == 2:
            m1 = scan_motors[0]
            s1 = h.start['scan_start1']
            e1 = h.start['scan_end1']
            n1 = h.start['num1']
            m2 = scan_motors[1]
            s2 = h.start['scan_start2']
            e2 = h.start['scan_end2']
            n2 = h.start['num2']
            
            print (f"fly2dpd({m1},{s1:.3f},{e1:.3f},{n1},{m2},{s2 :.3f},{e2 :.3f},{n2},{exp_time})")
            return (f"fly2dpd({m1},{s1:.3f},{e1:.3f},{n1},{m2},{s2 :.3f},{e2 :.3f},{n2},{exp_time})")
            
                     
def repeat_scan(sid):
    h = db[sid]
    sid = h.start['scan_id']
    scan_type = h.start['plan_name']
    if scan_type == 'FlyPlan1D' or scan_type == 'FlyPlan2D':
        scan_motors = h.start['motors']
        num_motors = len(scan_motors)
        exp_time = h.start['exposure_time']
        if num_motors == 1:
            m1 = scan_motors[0]
            s1 = h.start['scan_start']
            e1 = h.start['scan_end']
            n1 = h.start['num']
            print (f"<fly1dpd({m1},{s1:.3f},{e1:.3f},{n1},{exp_time})")
            yield from fly1dpd(m1,s1,e1,n1,exp_time)
        elif num_motors == 2:
            m1 = scan_motors[0]
            s1 = h.start['scan_start1']
            e1 = h.start['scan_end1']
            n1 = h.start['num1']
            m2 = scan_motors[1]
            s2 = h.start['scan_start2']
            e2 = h.start['scan_end2']
            n2 = h.start['num2']
            
            print (f"<fly2dpd({m1},{s1:.3f},{e1:.3f},{n1},{m2},{s2 :.3f},{e2 :.3f},{n2},{exp_time})")
            yield from fly2dpd(m1,s1,e1,n1,m2,s2,e2,n2,exp_time)
            #return(mot1+' {:1.3f} {:1.3f} {:d}'.format(s1,e1,n1)+' '+mot2+' {:1.3f} {:1.3f} {:d} {:1.3f}'.format(s2,e2,n2,exp_time))


class ScanInfo:
    plan = ''
    time = ''
    command = ''
    status = ''
    det = ''
    sid = ''

def scan_info(sid):
    si = ScanInfo()
    h = db[sid]
    si.sid = '{:d}'.format(h.start['scan_id'])
    si.time = datetime.fromtimestamp(h.start['time']).isoformat()
    si.plan = h.start['plan_name']
    si.status = h.stop['exit_status']
    si.command = get_scan_command(sid)
    si.det = h.start['detectors']
    return(si)


def save_cam06_images(filename = "crl"):

    pv_filename = epics.PV("XF:03IDC-ES{CAM:06}TIFF1:FileName")

    e_ = np.round(e.position,2)
    th = caget("XF:03IDA-OP{Lens:CRL-Ax:P}Mtr.RBV")
    exp_time = caget("XF:03IDC-ES{CAM:06}cam1:AcquireTime_RBV")
    ic1 =sclr2_ch2.get()
    filename_ = f'{filename}_e_{e_}_th_{th :.2f}_exp_{exp_time}_ic1_{ic1}'
    pv_filename.put(filename_)

    for i in range(3):
        print(i)
        time.sleep(2)
        caput('XF:03IDC-ES{CAM:06}TIFF1:WriteFile',1)


def mov_diff(gamma, delta, r=500, calc=0, check_for_dexela = True):

    if check_for_dexela and caget("XF:03IDC-ES{Stg:FPDet-Ax:Y}Mtr.RBV")<380:

        raise ValueError("Dexela detector maybe IN, Please move it away and try again!")
        return

    else:

        diff_z = diff.z.position

        gamma = gamma * np.pi / 180
        delta = delta * np.pi / 180
        beta = 89.337 * np.pi / 180

        z_yaw = 574.668 + 581.20 + diff_z
        z1 = 574.668 + 395.2 + diff_z
        z2 = z1 + 380
        d = 395.2

        x_yaw = np.sin(gamma) * z_yaw / np.sin(beta + gamma)
        R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
        R1 = R_yaw - (z_yaw - z1)
        R2 = R_yaw - (z_yaw - z2)
        y1 = np.tan(delta) * R1
        y2 = np.tan(delta) * R2
        R_det = R1 / np.cos(delta) - d
        dz = r - R_det

        print('Make sure all motors are zeroed properly, '
            'otherwise calculation will be wrong.')
        if x_yaw > 825 or x_yaw < -200:

            raise ValueError(f"diff_x =  -{x_yaw :.2}, out of range, move diff_z upstream and try again")
            #print('diff_x = ', -x_yaw,
                #' out of range, move diff_z upstream and try again')
        elif dz < -250 or dz > 0:
            #print('diff_cz = ', dz,
                #' out of range, move diff_z up or down stream and try again')
            raise ValueError(f"diff_cz =  {dz :.2f}, out of range, move diff_z upstream and try again")
        elif y1 > 750:
            #print('diff_y1 = ', y1, ' out of range, move diff_z upstream '
                #'and try again')
            raise ValueError(f"diff_y1 =  {y1 :.2f}, out of range, move diff_z upstream and try again")
        elif y2 > 1000:
            #print('diff_y2 = ', y2, ' out of range, move diff_z upstream '
                #'and try again')
            raise ValueError(f"diff_y2 =  {y2 :.2f}, out of range, move diff_z upstream and try again")
        else:
            print('diff_x = ', -x_yaw, ' diff_cz = ', dz,
                ' diff_y1 = ', y1, ' diff_y2 = ', y2)
            if calc == 0:

                print('wait for 3 sec, hit Ctrl+c to quit the operation')
                yield from bps.sleep(3)
                yield from bps.mov(diff.y1,y1,
                                diff.y2,y2,
                                diff.x,-x_yaw,
                                diff.yaw,gamma*180.0/np.pi,
                                diff.cz,dz)

                while (diff.x.moving is True or diff.y1.moving is True or diff.y2.moving is True or diff.yaw.moving is True):
                    yield from bps.sleep(2)
            else:
                print('Calculation mode; no motor will be moved')


def wh_diff(scanid = None):
    if scanid is None:
        diff_z = diff.z.position
        diff_yaw = diff.yaw.position * np.pi / 180.0
        diff_cz = diff.cz.position
        diff_x = diff.x.position
        diff_y1 = diff.y1.position
        diff_y2 = diff.y2.position
    else:
        baseline = db[scanid].table('baseline')
        diff_z = baseline['diff_z'][1]
        diff_yaw = baseline['diff_yaw'][1] * np.pi / 180
        diff_cz = baseline['diff_cz'][1]
        diff_x = baseline['diff_x'][1]
        diff_y1 = baseline['diff_y1'][1]
        diff_y2 = baseline['diff_y2'][1]

    gamma = diff_yaw
    beta = 89.337 * np.pi / 180
    z_yaw = 574.668 + 581.20 + diff_z
    z1 = 574.668 + 395.2 + diff_z
    z2 = z1 + 380
    d = 395.2

    x_yaw = np.sin(gamma) * z_yaw / np.sin(beta + gamma)
    R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
    R1 = R_yaw - (z_yaw - z1)
    R2 = R_yaw - (z_yaw - z2)

    # print('x_yaw = ', x_yaw, ' diff_x = ', diff_x)
    if abs(x_yaw + diff_x) > 3:
        print('Not a pure gamma rotation')
        return -1,-1,-1

    elif abs(diff_y1 / R1 - diff_y2 / R2) > 0.01:
        print('Not a pure delta rotation')
        return -1,-1,-1
    else:
        delta = np.arctan(diff_y1 / R1)
        R_det = R1 / np.cos(delta) - d + diff_cz


    Gamma = gamma * 180 / np.pi
    Delta = delta * 180 / np.pi
    print(f'{Gamma = :.2f}, {Delta  = :.2f} , r = {R_det :.2f}')
    return Gamma, Delta, R_det

def get_diff_det_params(sid):#,export_folder):
    # save baseline, detector angle and roi setting for a scan
    bl = db[sid].table('baseline')

    diff_z = np.array(bl['diff_z'])[0]
    diff_yaw = np.array(bl['diff_yaw'])[0] * np.pi / 180.0
    diff_cz = np.array(bl['diff_cz'])[0]
    diff_x = np.array(bl['diff_x'])[0]
    diff_y1 = np.array(bl['diff_y1'])[0]
    diff_y2 = np.array(bl['diff_y2'])[0]


    gamma = diff_yaw
    beta = 89.337 * np.pi / 180
    z_yaw = 574.668 + 581.20 + diff_z
    z1 = 574.668 + 395.2 + diff_z
    z2 = z1 + 380
    d = 395.2

    x_yaw = np.sin(gamma) * z_yaw / np.sin(beta + gamma)
    R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
    R1 = R_yaw - (z_yaw - z1)
    R2 = R_yaw - (z_yaw - z2)

    if abs(x_yaw + diff_x) > 3:
        gamma = 0
        delta = 0
        #R_det = 500

        beta = 89.337 * np.pi / 180
        R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
        R1 = R_yaw - (z_yaw - z1)
        R_det = R1 / np.cos(delta) - d + diff_cz

    elif abs(diff_y1 / R1 - diff_y2 / R2) > 0.01:
        gamma = 0
        delta = 0
        #R_det = 500

        beta = 89.337 * np.pi / 180
        R_yaw = np.sin(beta) * z_yaw / np.sin(beta + gamma)
        R1 = R_yaw - (z_yaw - z1)
        R_det = R1 / np.cos(delta) - d + diff_cz

    else:
        delta = np.arctan(diff_y1 / R1)
        R_det = R1 / np.cos(delta) - d + diff_cz

    

    print('gamma, delta, dist:', gamma*180/np.pi, delta*180/np.pi, R_det)

    return bl['energy'][1], gamma*180/np.pi, delta*180/np.pi, R_det*1000
    
def diff_status():

    if diff.yaw.position>0.5:

        gma, delt, r = wh_diff()

        if gma>0 or delt>0 or diff.yaw.position>0.5 or diff.y1.position>23:
            return "diff_pos"

        elif (int(gma) == 0 and int(delt) == 0) or (diff.x.position>10 and not diff.y1.position>23):
            return "safe"

    else:
        return "safe"


def diff_to_home(move_out_later = False):

    """ home == merlin position"""

    #close c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

    if diff_status() == "diff_pos":
        gma, delt, r = wh_diff()
        print("detector stage is at a diffraction position")

        if gma>10:

            if r<450:
                try:
                    yield from mov_diff(gma-10, delt, 500)
                except:
                    pass

            yield from bps.mov(diff.z, -1,diff.y1, 0, diff.y2, 0,diff.cz,-1)
            #yield from bps.mov(diff.y1, 0, diff.y2, 0)
            #yield from bps.mov(diff.cz,-1)

            try:
                yield from mov_diff(0, 0, 500)

            except:
                yield from bps.mov(diff.yaw, 0,diff.x, 0)
                #yield from bps.mov(diff.x, 0)


        else:
            yield from mov_diff(0,0,500)

    if move_out_later:
        yield from go_det('out')

    else:
        yield from go_det("merlin") #same as 0,0,500


def do_motor_position_checks(check_list_dict, rel_tol_per = 25,abs_tol = 20, message_string = " "):


    """
    check list: motor_name:high_limit
    example: check_list = {ssa2.hgap:0.5, ssa2.vgap:0.5, s5.hgap:0.5,s5.vgap:0.5,zposa.zposay:10,mllosa.osax:10}
             do_motor_position_checks(check_list,"this could damage the detector. "
                        "Move optics/slits to nanobeam positions and try again")

    """

    assert isinstance(check_list_dict, dict), "Failed; checklist must be a python dictionary"
    assert isinstance(message_string, str), "Failed; message must be a string"

    for mtr, target_pos in check_list_dict.items():

        #case when taget is zero, use 2um absolute tolerence
        if target_pos==0:
            if not math.isclose(mtr.position, target_pos, rel_tol=0, abs_tol = abs_tol):
                raise ValueError(f"{mtr.name} is not close to the required position\n"
                                     f"{message_string}")

        else:

            if not math.isclose(mtr.position, target_pos, rel_tol=rel_tol_per*0.01):
                raise ValueError(f"{mtr.name} is not close to the required position\n"
                                         f"{message_string}")


def go_det(det, disable_checks = False, mll = True):

    if mll:
        check_list = {ssa2.hgap:0.05, ssa2.vgap:0.03, s5.hgap:0.1,s5.vgap:0.1,mllosa.osax:0}
    else:
        check_list = {ssa2.hgap:0.05, ssa2.vgap:0.03, s5.hgap:0.3,s5.vgap:0.3,zposa.zposay:0}

    if caget("XF:03IDC-ES{Stg:FPDet-Ax:Y}Mtr.RBV")<380:

        raise ValueError("Dexela detector maybe IN, Please move it away and try again!")
        
    else:

        with open("/nsls2/data/hxn/shared/config/bluesky/profile_collection/startup/diff_det_pos.json") as fp:

            diff_pos = json.load(fp)
            #print(diff_pos)

        merlin_pos = diff_pos["merlin_pos"]
        cam11_pos = diff_pos["cam11_pos"]
        diode_pos = diff_pos["diode_pos"]
        telescope_pos = diff_pos["telescope_pos"]
        out_pos = diff_pos["out"]
        fip_merlin2 = diff_pos["fip_merlin2"]
        xray_eye = diff_pos["xray_eye"]
        eiger_pos2 = diff_pos["eiger_pos2"]

        #close c shutter for safety
        caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

        if det == 'merlin':
            #while zposa.zposax.position<20:
            #yield from bps.mov(diff.x, -1.5, diff.y1,-12.9, diff.y2,-12.9, diff.z, -50, diff.cz, -24.7)

            if not disable_checks:
                do_motor_position_checks(check_list,rel_tol_per = 100,message_string = "this could damage the detector. "
                        "Move optics/slits to nanobeam positions and try again")


            yield from bps.mov(diff.x, merlin_pos['diff_x'],
                            diff.y1,merlin_pos['diff_y1'],
                            diff.y2,merlin_pos['diff_y2'],
                            diff.z, merlin_pos['diff_z'],
                            diff.cz,merlin_pos['diff_cz']
                            )
            #yield from bps.mov(diff.y1,-3.2)
            #yield from bps.mov(diff.y2,-3.2)
        elif det == 'cam11':
            #yield from bps.mov(diff.x,206.83, diff.y1, 19.177, diff.y2, 19.177,diff.z, -50, diff.cz, -24.7)
            yield from bps.mov(diff.x, cam11_pos['diff_x'],
                            diff.y1,cam11_pos['diff_y1'],
                            diff.y2,cam11_pos['diff_y2'],
                            diff.z, cam11_pos['diff_z'],
                            diff.cz,cam11_pos['diff_cz']
                            )
            #yield from bps.mov(diff.y1,22.65)
            #yield from bps.mov(diff.y2,22.65)
        elif det == 'diode':
            #yield from bps.mov(diff.x,206.83, diff.y1, 19.177, diff.y2, 19.177,diff.z, -50, diff.cz, -24.7)
            yield from bps.mov(diff.x, diode_pos['diff_x'],
                            diff.y1,diode_pos['diff_y1'],
                            diff.y2,diode_pos['diff_y2'],
                            diff.z, diode_pos['diff_z'],
                            diff.cz,diode_pos['diff_cz']
                            )
        elif det =='telescope':
            #yield from bps.mov(diff.x,-342, diff.z, -50, diff.cz, -24.7)
            yield from bps.mov(diff.x,telescope_pos['diff_x'],
                            diff.z,telescope_pos['diff_z'],
                            diff.cz,telescope_pos['diff_cz'])
            #yield from bps.mov(diff.z,-50)


        elif det=='out':

            yield from bps.mov(diff.x, out_pos['diff_x'],
                            diff.y1,out_pos['diff_y1'],
                            diff.y2,out_pos['diff_y2'],
                            diff.z, out_pos['diff_z'],
                            diff.cz,out_pos['diff_cz']
                            )


        elif det=="eiger":
            if not disable_checks:
                do_motor_position_checks(check_list,rel_tol_per = 50,message_string = "this could damage the detector. "
                        "Move optics/slits to nanobeam positions and try again")


            yield from bps.mov(diff.x, out_pos['diff_x']+150,
                diff.y1,out_pos['diff_y1'],
                diff.y2,out_pos['diff_y2'],
                diff.z, out_pos['diff_z'],
                diff.cz,out_pos['diff_cz']
                )


        elif det == "fip_merlin2":
            caput("XF:03IDC-ES{MC:10-Ax:5}Mtr.VAL",fip_merlin2["bl_y"])
            caput("XF:03IDC-ES{MC:10-Ax:6}Mtr.VAL",fip_merlin2["bl_x"])

        elif det == "xray_eye":
            caput("XF:03IDC-ES{MC:10-Ax:5}Mtr.VAL",xray_eye["bl_y"])
            caput("XF:03IDC-ES{MC:10-Ax:6}Mtr.VAL",xray_eye["bl_x"])

        elif det == "eiger_pos2":
            yield from bps.mov(diff.x, eiger_pos2['diff_x'],
                diff.y1,eiger_pos2['diff_y1'],
                diff.y2,eiger_pos2['diff_y2'],
                diff.z, eiger_pos2['diff_z'],
                diff.cz,eiger_pos2['diff_cz']
                )



        else:
            print('Input det is not defined. '
                'Available ones are merlin, cam11, telescope, eiger and tpx')


def update_det_pos(det = "merlin", do_confirm = True):

    # print("!!!Do not update position directly from function, edit  ~/.ipython/profile_collection/startup/diff_det_pos.json to modify detector positions.!!!")
    # print("Exiting...")
    # return

    if do_confirm:
        check = 'n'
        check = input(f"Are you sure you want to update {det} position?")
    else:
        check = 'y'
    
    if check == "y":



        json_path = "/nsls2/data/hxn/shared/config/bluesky/profile_collection/startup/diff_det_pos.json"

        with open(json_path, "r") as read_file:
            diff_pos = json.load(read_file)

        if det == "merlin":

            diff_pos['merlin_pos']['diff_x'] = np.round(diff.x.position,2)
            diff_pos['merlin_pos']['diff_y1'] = np.round(diff.y1.position,2)
            diff_pos['merlin_pos']['diff_y2'] = np.round(diff.y2.position,2)
            diff_pos['merlin_pos']['diff_z'] = np.round(diff.z.position,2)
            diff_pos['merlin_pos']['diff_cz'] = np.round(diff.cz.position,2)

        elif det == "cam11":

            diff_pos['cam11_pos']['diff_x'] = np.round(diff.x.position,2)
            diff_pos['cam11_pos']['diff_y1'] = np.round(diff.y1.position,2)
            diff_pos['cam11_pos']['diff_y2'] = np.round(diff.y2.position,2)
            diff_pos['cam11_pos']['diff_z'] = np.round(diff.z.position,2)
            diff_pos['cam11_pos']['diff_cz'] = np.round(diff.cz.position,2)

        elif det == "telescope":

            diff_pos['telescope_pos']['diff_x'] = np.round(diff.x.position,2)
            diff_pos['merlin_pos']['diff_z'] = np.round(diff.z.position,2)
            diff_pos['merlin_pos']['diff_cz'] = np.round(diff.cz.position,2)

        elif det == "out":
            diff_pos['out']['diff_x'] = np.round(diff.x.position,2)
            diff_pos['out']['diff_y1'] = np.round(diff.y1.position,2)
            diff_pos['out']['diff_y2'] = np.round(diff.y2.position,2)
            diff_pos['out']['diff_z'] = np.round(diff.z.position,2)
            diff_pos['out']['diff_cz'] = np.round(diff.cz.position,2)


        elif det == "fip_merlin2":

            diff_pos["fip_merlin2"]['bl_y'] = caget("XF:03IDC-ES{MC:10-Ax:5}Mtr.VAL")
            diff_pos["fip_merlin2"]['bl_x'] = caget("XF:03IDC-ES{MC:10-Ax:6}Mtr.VAL")


        elif det == "xray_eye":

            diff_pos["xray_eye"]['bl_y'] = caget("XF:03IDC-ES{MC:10-Ax:5}Mtr.VAL")
            diff_pos["xray_eye"]['bl_x'] = caget("XF:03IDC-ES{MC:10-Ax:6}Mtr.VAL")

        elif det == "eiger_pos2":
            diff_pos["eiger_pos2"]['diff_x'] = np.round(diff.x.position,2)
            diff_pos["eiger_pos2"]['diff_y1'] = np.round(diff.y1.position,2)
            diff_pos["eiger_pos2"]['diff_y2'] = np.round(diff.y2.position,2)
            diff_pos["eiger_pos2"]['diff_z'] = np.round(diff.z.position,2)
            diff_pos["eiger_pos2"]['diff_cz'] = np.round(diff.cz.position,2)



        else:
            raise KeyError ("Undefined detector name")

        read_file.close()
        ext = datetime.now().strftime('%Y-%m-%d')
        json_path_backup = f"/data/users/backup_params/diff_pos/{ext}_diff_det_pos.json"

        with open(json_path, "w") as out_file:
            json.dump(diff_pos, out_file, indent = 6)

        with open(json_path_backup, "w") as out_file:
            json.dump(diff_pos, out_file, indent = 6)

        out_file.close()


def find_45_degree(th_mtr,start_angle,end_angle,num, x_start, x_end, x_num, exp_time=0.02, elem="Pt_L"):


    ''' Usage: find_45_degree(dsth,40,50,25,-5, 5,100, exp_time=0.02,elem="Au_L") '''
    
    time_ = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_name = f"find_45_{th_mtr.name}_{start_angle}_to_{end_angle}_{time_}"
    header = "th wx wz x_sid"

    if th_mtr == dsth:
        x_mtr, z_mtr = dssx, dssz

    elif th_mtr == zpsth:
        x_mtr, z_mtr = zpssx, zpssz

    yield from bps.mov(th_mtr,start_angle)
    step = (end_angle-start_angle)/num
    x_sid = np.zeros(num+1)
    w_x = np.zeros(num+1)
    w_z = np.zeros(num+1)
    th = np.zeros(num+1)
    for i in range(num+1):
        yield from fly1dpd(dets_fast_fs,x_mtr,x_start,x_end,x_num,exp_time)
        l,r,c=square_fit(-1,elem)
        plt.close()
        w_x[i] = r-l
        x_sid[i] = db[-1].start.get('scan_id')
        yield from fly1dpd(dets_fast_fs,z_mtr,x_start,x_end,x_num,exp_time)
        l,r,c=square_fit(-1,elem)
        plt.close()
        w_z[i] = r-l
        th[i]=th_mtr.position
        yield from bps.sleep(1)
        yield from bps.movr(th_mtr,step)

        np.savetxt(f"/nsls2/data/hxn/legacy/users/Beamline_Performance/find_45_scans/{save_name}.txt",
                   np.column_stack([th,w_x,w_z,x_sid]), header = header)
    plt.figure()
    plt.plot(th,w_x,'r+',th,w_z,'g-')

    find_45_offset(f"/nsls2/data/hxn/legacy/users/Beamline_Performance/find_45_scans/{save_name}.txt")
    return th,w_x,w_z


def find_45_offset(data_path = "/nsls2/data/hxn/legacy/users/Beamline_Performance/find_45_scans/45deg_calib.txt"):

    """ usage :find_45_offset() """


    data = abs(np.loadtxt(data_path))
    # Define the objective function
    def objective(offset, data):
        # Calculate theta
        theta = np.deg2rad(data[:, 0] - offset)  # theta in radians
        
        # Calculate the sum to minimize
        result = np.sum((np.cos(theta) * data[:, 1]) - (np.sin(theta) * data[:, 2]))
        return abs(result)

    # Initial guess for the offset
    initial_guess = 0.0  # You can set this to any reasonable starting point

    # Use scipy's minimize function to find the optimal offset
    result = minimize(objective, initial_guess, args=(data,))

    # Output the optimal offset and the minimized result
    optimal_offset = result.x[0]
    minimized_value = result.fun

    print(f"Optimal offset in degree: {optimal_offset}")
    print(f"Minimized value: {minimized_value}")

    # Calculate theta with the optimal offset
    theta_raw = (data[:, 0]) * np.pi / 180
    theta_optimal = (data[:, 0] - optimal_offset) * np.pi / 180

    # Plotting the data before and after finding the optimal offset
    fig, ax = plt.subplots(1, 2, figsize=(12, 6))

    theta_raw = abs(data[:, 0]) * np.pi / 180

    # Plot before applying the offset (raw data)
    ax[0].scatter(data[:, 0], np.cos(theta_raw) * data[:, 1], label='X', color='r', alpha=0.7)
    ax[0].scatter(data[:, 0], np.sin(theta_raw) * data[:, 2], label='Z', color='b', alpha=0.7)
    ax[0].set_title("Before Applying Offset")
    ax[0].set_xlabel("Angle")
    ax[0].set_ylabel("Size")
    ax[0].legend()

    # Plot after applying the optimal offset
    ax[1].scatter(data[:, 0], np.cos(theta_optimal) * data[:, 1], label='Adjusted X', color='r', alpha=0.7)
    ax[1].scatter(data[:, 0], np.sin(theta_optimal) * data[:, 2], label='Adjusted Z', color='b', alpha=0.7)
    ax[1].set_title(f"After Applying Optimal Offset of {optimal_offset :.2f} degree")
    ax[1].set_xlabel("Angle")
    ax[1].set_ylabel("Size")
    ax[1].legend()

    plt.tight_layout()
    plt.show()
    return optimal_offset


def rot_stage_calib_scan(th_mtr,start_angle,end_angle,angle_step, x_start, x_end, x_num, exp_time=0.02, elem="Pt_L"):


    ''' Usage: find_45_degree_fullrange(zpsth,-5,5,3,-12, 12,200, exp_time=0.03,elem="Au_L") '''
    print("Diving board line of 5 um is assumed in the fitting")
    
    time_ = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_name = f"find_45_{th_mtr.name}_{start_angle}_to_{end_angle}_{time_}"
    header = "scan_motor th wx sid"

    if th_mtr == dsth:
        x_mtr, z_mtr = dssx, dssz

    elif th_mtr == zpsth:
        x_mtr, z_mtr = zpssx, zpssz

    angle_list = np.arange(start_angle, end_angle+0.1,angle_step)
    print(f"{angle_list = }")
    num = len(angle_list)
    scan_motor = np.empty(num, dtype='<U20')
    x_sid = np.zeros(num)
    w_x = np.zeros(num)
    th = np.zeros(num)
    
    for i, angle in enumerate(angle_list):
        yield from bps.mov(th_mtr,angle)
        if np.abs(angle) <= 45.:
            yield from fly1dpd(dets_fast_fs,x_mtr,x_start,x_end,x_num,exp_time)
            print(x_mtr.name)
            scan_motor[i] = str(x_mtr.name)
        else:
            yield from fly1dpd(dets_fast_fs,z_mtr,x_start,x_end,x_num,exp_time)
            scan_motor[i] = str(z_mtr.name)

        l,r,c=square_fit(-1,elem)
        plt.close()
        w_x[i] = r-l
        x_sid[i] = db[-1].start.get('scan_id')
        th[i]=th_mtr.position
        yield from bps.sleep(1)
        
        save_file = f"/nsls2/data/hxn/legacy/users/Beamline_Performance/find_45_scans/{save_name}.txt"
        np.savetxt(save_file, np.column_stack([np.array(scan_motor),th,w_x,x_sid]), header = header, fmt = '%s')
    
    ############### added for fitting ##############
    data = np.genfromtxt(
        save_file,
        skip_header=1,          # skip the column headers
        dtype=None,             # let numpy guess types (object array)
        encoding="utf-8"        # needed for Python 3 to handle strings
    )
    motor = data["f0"]
    th = np.deg2rad(data["f1"])
    w = data["f2"]

    popt, pcov = curve_fit(
        lambda x, sx, sz, b, c: xz_fitting(x, motor, sx, sz, b, c),
        th, w,
        p0=[1, 1, 0.01, 0.01],
        bounds=([0, 0, -np.pi, -np.pi], [np.inf, np.inf, np.pi, np.pi])
    )
    sx_fit,sz_fit,b_fit, c_fit = popt
    fit_y = xz_fitting(th, motor, sx_fit,sz_fit,b_fit, c_fit)
    plt.figure()
    plt.plot(np.rad2deg(th),w,'b.', np.rad2deg(th),fit_y,'r-')
    plt.show(block=False)
    plt.title(f"sx = {sx_fit:.3f}, sz = {sz_fit:.3f}, line offset = {np.rad2deg(b_fit):.3f}, stage offset = {np.rad2deg(c_fit):.3f}")
    plt.xlabel('th')
    print(f"sx = {sx_fit:.3f}, sz = {sz_fit:.3f}, line offset = {b_fit:.3f}, stage offset = {c_fit:.3f}")

    return th,w_x

# Define the model function to fit the width of diving board line
def x_fitting(x, sx, b, c):
    return sx*5.0* np.cos(x + b) / np.cos(x + c)
def z_fitting(x, sz, b, c):
    return sz*5.0* np.cos(x + b) / np.abs(np.sin(x + c))

def xz_fitting(x, motor,sx, sz,  b, c):
    out = np.empty_like(x,dtype=float)
    if "zpssx" in motor or "zpssz" in motor:
        out[motor == 'zpssz'] = z_fitting(x[motor=='zpssz'], sz, b, c)
        out[motor == 'zpssx'] = x_fitting(x[motor=='zpssx'], sx, b, c)
    elif "dssx" in motor or "zdssz" in motor:
        out[motor == 'dssz'] = z_fitting(x[motor=='dssz'], sz, b, c)
        out[motor == 'dssx'] = x_fitting(x[motor=='dssx'], sx, b, c)
    return out


def find_45_offset_scaling(data_path = "/nsls2/data/hxn/legacy/users/Beamline_Performance/45deg_calib.txt"):

    """ usage :find_45_offset() """

    data = np.loadtxt(data_path)
    # Define the objective function
    def objective(offset,xscale, yscale, data):
        # Calculate theta
        theta = np.deg2rad(data[:, 0] - offset)  # theta in radians
        
        # Calculate the sum to minimize
        result = np.sum((np.cos(theta) * (xscale*data[:, 1])) - (np.sin(theta) * (yscale*data[:, 2])))
        return abs(result)

    # Initial guess for the offset
    initial_guess = 0# You can set this to any reasonable starting point

    # Use scipy's minimize function to find the optimal offset
    result = minimize(objective, initial_guess, args=(data,0,0))
    print(result)

    '''
    # Output the optimal offset and the minimized result
    optimal_offset = result.x[0]
    minimized_value = result.fun

    print(f"Optimal offset in degree: {optimal_offset}")
    print(f"Minimized value: {minimized_value}")

    # Calculate theta with the optimal offset
    theta_raw = (data[:, 0]) * np.pi / 180
    theta_optimal = (data[:, 0] - optimal_offset) * np.pi / 180

    # Plotting the data before and after finding the optimal offset
    fig, ax = plt.subplots(1, 2, figsize=(12, 6))

    theta_raw = (data[:, 0]) * np.pi / 180

    # Plot before applying the offset (raw data)
    ax[0].scatter(data[:, 0], np.cos(theta_raw) * data[:, 1], label='X', color='r', alpha=0.7)
    ax[0].scatter(data[:, 0], np.sin(theta_raw) * data[:, 2], label='Z', color='b', alpha=0.7)
    ax[0].set_title("Before Applying Offset")
    ax[0].set_xlabel("Angle")
    ax[0].set_ylabel("Size")
    ax[0].legend()

    # Plot after applying the optimal offset
    ax[1].scatter(data[:, 0], np.cos(theta_optimal) * data[:, 1], label='Adjusted X', color='r', alpha=0.7)
    ax[1].scatter(data[:, 0], np.sin(theta_optimal) * data[:, 2], label='Adjusted Z', color='b', alpha=0.7)
    ax[1].set_title(f"After Applying Optimal Offset of {optimal_offset :.2f} degree")
    ax[1].set_xlabel("Angle")
    ax[1].set_ylabel("Size")
    ax[1].legend()

    plt.tight_layout()
    plt.show()
    return optimal_offset
    '''

def plot_45_degree_calib(filename):

    data = np.loadtxt(filename)
    print(data.shape)
    th = data[:,0]
    w_x = data[:,1]
    w_z = data[:,2]
    plt.figure()
    plt.plot(th,w_x,'r+',th,w_z,'g-')


def VMS_in():

    print("Please wait...")

    #vms

    #caput("XF:03IDA-OP{VMS:1-Ax:Y}Mtr.VAL", -0.07) #mirrorY
    #caput("XF:03IDA-OP{VMS:1-Ax:P}Mtr.VAL", 3.06) #mirror picth
    caput("XF:03IDA-OP{VMS:1-Ax:YU}Mtr.VAL", -1.46) #upstream Y
    caput("XF:03IDA-OP{VMS:1-Ax:YD}Mtr.VAL",0.39) #downstream Y
    caput("XF:03IDA-OP{VMS:1-Ax:TX}Mtr.VAL", 0) #trans. X
    #caput("XF:03IDA-OP{VMS:1-Ax:PF}Mtr.VAL", 7) #pitch fine

    #bbpm
    caput("XF:03IDB-OP{Slt:SSA1-Ax:7}Mtr.VAL", -2.4)
    caput("XF:03IDB-OP{Slt:SSA1-Ax:8}Mtr.VAL",0.25)

    #cbpm
    caput("XF:03IDC-ES{BPM:7-Ax:Y}Mtr.VAL", 1.3)

    for i in tqdm.tqdm(range(30)):
        yield from bps.sleep(1)



    #move ssa2
    yield from bps.mov(ssa2.hgap, 2, ssa2.vgap,2, ssa2.hcen,0.098,ssa2.vcen, 0)

    #move ssa1
    yield from bps.mov(ssa1.hgap, 2.0, ssa1.vgap,2.0, ssa1.hcen,0.079,ssa1.vcen, 1.7)

    print(" Aligned to VMS")

def VMS_out():


    print("Please wait...")

    #vms

    #caput("XF:03IDA-OP{VMS:1-Ax:Y}Mtr.VAL", -1.0) #mirrorY
    #caput("XF:03IDA-OP{VMS:1-Ax:P}Mtr.VAL", -0.0082) #mirror picth
    caput("XF:03IDA-OP{VMS:1-Ax:YU}Mtr.VAL", -2.2) #upstream Y
    caput("XF:03IDA-OP{VMS:1-Ax:YD}Mtr.VAL",-2.6) #downstream Y
    #caput("XF:03IDA-OP{VMS:1-Ax:TX}Mtr.VAL", 0.084) #trans. X
    caput("XF:03IDA-OP{VMS:1-Ax:PF}Mtr.VAL", 0) #pitch fine

    #bbpm
    caput("XF:03IDB-OP{Slt:SSA1-Ax:7}Mtr.VAL", -0.16)
    caput("XF:03IDB-OP{Slt:SSA1-Ax:8}Mtr.VAL",0.065)

    #cbpm
    caput("XF:03IDC-ES{BPM:7-Ax:Y}Mtr.VAL", 0.4)


    for i in tqdm.tqdm(range(0, 30), desc ="Moving..."):
        yield from bps.sleep(1)


    #move ssa2
    yield from bps.mov(ssa2.hgap, 2, ssa2.vgap,2, ssa2.hcen,0,ssa2.vcen, -0.6765)

    #move ssa1
    yield from bps.mov(ssa1.hgap, 2.64, ssa1.vgap,2.5, ssa1.hcen,-0.092,ssa1.vcen, -0.78)

    print(" VMS out")


def feedback_auto_off(wait_time_sec = 0.5):

    beam_current = "SR:C03-BI{DCCT:1}I:Real-I"
    fe_xbpm_current = "SR:C03-BI{XBPM:1}Ampl:CurrTotal-I"
    fe_shutter_status = "XF:03ID-PPS{Sh:FE}Sts:Cls-Sts"
    ugap = "SR:C3-ID:G1{IVU20:1-Ax:Gap}-Mtr.RBV"

    b_feeback_x = "XF:03ID-BI{EM:BPM1}fast_pidX.FBON"
    b_feeback_y = "XF:03ID-BI{EM:BPM1}fast_pidY.FBON"

    while True:
        if caget(beam_current)<10 or caget(fe_xbpm_current)<10 or caget(fe_shutter_status)==1:

            if caget(b_feeback_x) == 1 or caget(b_feeback_y) == 1:
                caput(b_feeback_x,0)
                caput(b_feeback_y,0)
                logger.info(f"feedback was disabled by {os.getlogin()}")

            else:
                pass

        time.sleep(wait_time_sec)


def check_for_beam_dump(
    threshold = 5000, 
    check_period = 60,
    stabilization_delay = 900):
    """
    Waits until the beam intensity (sclr2_ch2) is above a given threshold,
    and then waits for a stabilization period before running recovery.

    Parameters:
    -----------
    threshold (float): The minimum acceptable beam intensity. Defaults to 5000.
    check_period (float): The time (in seconds) to sleep between checks 
                          while the beam is off. Defaults to 60.
    stabilization_delay (float): The time (in seconds) to wait after the 
                                 beam returns for stabilization. Defaults to 900 (15 min).
    """
    
    # --- Beam-Off Loop ---
    while (sclr2_ch2.get() < threshold):
        print (f"Beam intensity ({sclr2_ch2.name}) is lower than {threshold}. Waiting...")
        yield from bps.sleep(check_period)
        
    # # --- Beam-On Recovery ---
    # logger.info("Beam is back. Waiting for %s seconds for system stabilization.", 
    #             stabilization_delay)
    # yield from bps.sleep(stabilization_delay)
    
    # # --- Execute Recovery Protocol ---
    # logger.info("Stabilization complete. Running beam dump recovery protocol.")
    # yield from recover_from_beamdump()


def find_edge_2D(scan_id, elem, left_flag=True):

    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    motors = db[scan_id].start['motors']
    x = np.array(df2[motors[0]])
    y = np.array(df2[motors[1]])
    #I0 = np.asfarray(df2.sclr1_ch4)
    I0 = np.asfarray(df2['sclr1_ch4'])
    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']
    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))
    l = np.linspace(y[0],y[-1],ny)
    s = xrf.sum(1)
    #if axis == 'x':
        #l = np.linspace(x[0],x[-1],nx)
        #s = xrf.sum(0)
    #else:
        #l = np.linspace(y[0],y[-1],ny)
        #s = xrf.sum(1)


	#plt.figure()
	#plt.plot(l,s)
	#plt.show()
	#sd = np.diff(s)
    sd = np.gradient(s)
    if left_flag:
        edge_loc1 = l[np.argmax(sd)]
    else:
        edge_loc1 = l[np.argmin(sd)]
    #plt.plot(l,sd)
	#plt.title('edge at '+np.str(edge_loc1))

    sd2 = np.diff(s)
    ll = l[:-1]
	#plt.plot(ll,sd2)
    if left_flag:
        edge_loc2 = ll[np.argmax(sd2)]
    else:
        edge_loc2 = ll[np.argmin(sd2)]
	#plt.xlabel('edge at '+np.str(edge_loc2))

	#edge_pos=find_edge(l,s,10)
	#pos = l[s == edge_pos]
	#pos = l[s == np.gradient(s).max()]
	#popt,pcov=curve_fit(erfunc1,l,s, p0=[edge_pos,0.05,0.5])
    return edge_loc1,edge_loc2


def update_xrf_elem_list(roi_elems = ['Cr', 'Ge', 'W_L', 'Se', 'Si', 'Cl', 'Ga', 'S', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Zn', 'Pt_M', 'Au_L'],
                         live_plot_elems = ['Cr', 'Ge', 'W_L', 'Se'], line_plot_elem = "Cr"):

        xrf_elems = {}
        xrf_elems["roi_elems"] = roi_elems
        xrf_elems["live_plot_elems"] = live_plot_elems
        xrf_elems["line_plot_elem"] = line_plot_elem
        json_param_file = "/nsls2/data/hxn/shared/config/bluesky/profile_collection/startup/plot_elems.json"

        with open(json_param_file, "w") as fp:
            json.dump(xrf_elems, fp, indent = 6)
            fp.close()
        reload_bsui()


def mll_sample_out(move_lens_upstream = True):

    if fdet1.x.position>-50:
        raise ValueError("XRF detector is not in OUT position. Move it out <-50 and try again")
    else:
        
        yield from bps.movr(sbz,5000)
        yield from bps.mov(dsth,0)

        if sbz.position>4800:
            yield from bps.movr(sbx,-4000)
        else:
            raise ValueError("Sbz Motion Failed. Move it out and try again")


    if move_lens_upstream:
        yield from mll_to_upstream()

def mll_sample_in(move_sbz = False, move_lens_downstream = True):

        if sbz.position>4800:
            yield from bps.movr(sbx,4000)
        else:
            raise ValueError("Sbz is not close to 5000. Move it out and try again")


        if move_sbz:
            if sbz.position<100:
                yield from bps.movr(sbz,-5000)

            else:
                raise ValueError("Sbx is not close to 0. Move it in and try again")


        if move_lens_downstream:
            yield from mll_to_downstream()


def mll_to_upstream():

    """
    vmll vz -10000 and confirm movement
    hmll hz -8000 and confirm movement

    """

    if abs(vmll.vz.position)<100:
        print("vmll.vz moving to -10000")
        yield from bps.movr(vmll.vz, -10000)
        yield from bps.sleep(2)
    else:
        raise ValueError("VZ is maybe already in out position")
        #print("VZ<-2000 um; VZ is maybe already in out position; trying to move hz")
        pass

    if abs(vmll.vz.position)>9900 and abs(hmll.hz.position)<100:
        print("hmll.hz moving to -8000")
        yield from bps.movr(hmll.hz, -8000)
    else:
        raise ValueError("VMLL is not out or HZ is not close to zero, try manual controls")

    if abs(hmll.hz.position)<7900:
        print("HMLL motion failed try manually hz=-5000")
        raise ValueError("HMLL motion failed try manually hz=-5000")
    else:
        return
    
def mll_to_upstream_no_re():

    """
    vmll vz -10000 and confirm movement
    hmll hz -8000 and confirm movement

    """

    if abs(vz.position)<100:
        print("vmll.vz moving to -10000")
        vz.move(vz.position-10000)
        QtTest.QTest.qWait(5000)
    else:
        raise ValueError("VZ is maybe already in out position")
        #print("VZ<-2000 um; VZ is maybe already in out position; trying to move hz")

    if abs(vz.position)>9900 and abs(hz.position)<100:
        print("hmll.hz moving to -8000")
        hz.move(hz.position-8000)
        QtTest.QTest.qWait(5000)

    else:
        raise ValueError("VMLL is not out or HZ is not close to zero, try manual controls")

    if abs(hz.position)<7900:
        print("HMLL motion failed try manually hz=-5000")
        raise ValueError("HMLL motion failed try manually hz=-5000")
    else:
        return


def mll_to_downstream():

    if abs(hmll.hz.position)>7980 and not mllosa.osaz.position>100:
        print("hmll.hz moving to 0")
        yield from bps.movr(hmll.hz, 8000)

    else:
        raise ValueError("HMLL motion failed bacasue hz is not OUT or OSA Z is not close to zero; try manually vz=0 if hz~0")

    if abs(vmll.vz.position)>9990 and abs(hmll.hz.position)<10:
        print("vmll.vz moving to -0")
        yield from bps.movr(vmll.vz, 10000)
    else:
        raise ValueError("VMLL motion failed bacasue hz is not home; try manually vz=0 if hz~0")
    

def mll_to_downstream_no_re():

    if abs(hz.position)>7980 and not mllosa.osaz.position>100:
        print("hmll.hz moving to 0")
        hz.move(hz.position+8000)
        QtTest.QTest.qWait(5000)

    else:
        raise ValueError("HMLL motion failed bacasue hz is not OUT or OSA Z is not close to zero; try manually vz=0 if hz~0")

    if abs(vz.position)>9990 and abs(hz.position)<10:
        print("vmll.vz moving to -0")
        vz.move(vz.position+10000)
        QtTest.QTest.qWait(5000)
        
    else:
        raise ValueError("VMLL motion failed bacasue hz is not home; try manually vz=0 if hz~0")

def mll_osa_out():

    if abs(mllosa.osax.position)<50:
        yield from bps.movr(mllosa.osax,+2600)

    else:
        raise ValueError(f"OSA_X position not close to zero osax = {mllosa.osax.position :.1f}")
    

def mll_osa_in():

    if not abs(mllosa.osax.position)<10:
        yield from bps.movr(mllosa.osax,-2600)

    else:
        raise ValueError(f"OSA_X position not close to zero osax = {mllosa.osax.position :.1f}")

def mll_bs_out_():

    if abs(mllbs.bsx.position)<10 and abs(mllbs.bsy.position)<10:
        yield from bps.movr(mllbs.bsx,500)
        yield from bps.movr(mllbs.bsy,-500)
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsx = {mllbs.bsx.position :.1f},bsy = {mllbs.bsy.position :.1f}")
    
def mll_bs_out(wait_till_finish = True):

    if abs(mllbs.bsx.position)<10 and abs(mllbs.bsy.position)<10:

        caput(mllbs.bsx.prefix,caget(mllbs.bsx.prefix)+500)
        caput(mllbs.bsy.prefix,caget(mllbs.bsy.prefix)-500)
        if wait_till_finish:
            while mllbs.bsx.moving or mllbs.bsy.moving:
                time.sleep(0.3)
        
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsx = {mllbs.bsx.position :.1f},bsy = {mllbs.bsy.position :.1f}")
    

def mll_bs_out_move(wait_till_finish = False):

    if abs(mllbs.bsx.position)<10 and abs(mllbs.bsy.position)<10:

        mllbs.bsx.move(mllbs.bsx.position+500)
        mllbs.bsy.move(mllbs.bsy.position-500)
        if wait_till_finish:
            while mllbs.bsx.moving or mllbs.bsy.moving:
                time.sleep(0.3)
        
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsx = {mllbs.bsx.position :.1f},bsy = {mllbs.bsy.position :.1f}")

def mll_bs_in():
    if not abs(mllbs.bsx.position)<10 and not abs(mllbs.bsy.position)<10:
        yield from bps.movr(mllbs.bsx,-500)
        yield from bps.movr(mllbs.bsy,500)
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsx = {mllbs.bsx.position :.1f},bsy = {mllbs.bsy.position :.1f}")

def mll_lens_in():

    if not abs(vmll.vy.position)<10 and not abs(hmll.hx.position)<10:
        yield from bps.movr(vmll.vy,-500)
        yield from bps.movr(hmll.hx,500)
    else:
        raise ValueError("lens positions are close to zero")
    
def mll_lens_out():

    if abs(vmll.vy.position)<10 and abs(hmll.hx.position)<10 and abs(fdet1.x.position)>10:
        yield from bps.movr(vmll.vy,500)
        yield from bps.movr(hmll.hx,-500)
    else:
        raise ValueError("lens positions are not close to zero or fluorescence detector is too close to hmll")
        pass

def mll_mov_zfocus(distance):
    sbz_current = sbz.user_readback.get()
    sbz_target = sbz_current + distance
    if sbz_target > -10 and sbz_target < 5000:
        yield from bps.mov(sbz,sbz_target)
        yield from bps.abs_set(sbx.user_setpoint,sbx.user_readback.get()+distance / 500 * 3,wait=True)
        yield from bps.abs_set(dsy.user_setpoint,dsy.user_readback.get()+distance / 500 * -3.3,wait=True)
        yield from bps.sleep(1)
    else:
        print('Target sbz out of range -10~5000 um')

def move_motor_caput(motor_name_value_dict):

    """move_motor_caput({mllbs.bsx:0, mllbs.bsy:0})
       put slowest motor last"""

    for key, val in motor_name_value_dict.items():
        caput(key.prefix,val)

    time.sleep(0.25)

    while key.moving:
        time.sleep(0.25)

    return 

def mlls_optics_out_for_cam11():

    """
    move the mll bsx 500 +x
    move mll bsy 500 -y'

    vmll vy + 500
    hmll hx -500
    osax +2600 um

    """

    if abs(vmll.vy.position)<10 and abs(hmll.hx.position)<10:
        yield from bps.movr(vmll.vy,500)
        yield from bps.movr(hmll.hx,-500)
    else:
        raise ValueError("lens positions are not close to zero")
        pass

    if abs(mllosa.osax.position)<10:
        yield from bps.movr(mllosa.osax,+2600)

    else:
        raise ValueError(f"OSA_X position not close to zero osax = {mllosa.osax.position :.1f}")
        pass

    if abs(mllbs.bsx.position)<10 and abs(mllbs.bsy.position)<10:
        yield from bps.movr(mllbs.bsx,500)
        yield from bps.movr(mllbs.bsy,-500)
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsx = {mllbs.bsx.position :.1f},bsy = {mllbs.bsy.position :.1f}")
        pass


def zero_child_components(parent_ = mllosa, tolerance =10):

    for comps in parent_.component_names:
        if tolerance is None:
            mtr.set_current_position(0)
        else:
            mtr = eval(f"{parent_.name}.{comps}")
            if abs(mtr.position) < abs(tolerance):
                mtr.set_current_position(0)

            else:
                raise ValueError(f'{mtr.name} is out of the tolerence limit')


def zero_mll_optics(force = False):

    if force:
        tol = None
    else:
        tol = 50

    zero_child_components(parent_ = hmll,tolerance=tol)
    zero_child_components(parent_ = vmll,tolerance=tol)
    zero_child_components(parent_ = mllosa,tolerance=tol)
    zero_child_components(parent_ = mllbs,tolerance=tol)


def zero_zp_optics():

    if zps.zpsx.position>0.2 or zps.zpsz.position>0.2:

        raise ValueError(f"zpsx or zpsz is not close to zero. Aborted")

    else:

        zps.zpsx.set_current_position(0)
        zps.zpsz.set_current_position(0)


    zero_child_components(parent_ = zposa,tolerance = 50)
    zero_child_components(parent_ = zpbs,tolerance = 50)


def mll_to_cam11_view(move_cam11 = True):

    check_list_before = {mllbs.bsx:0,mllbs.bsy:0,mllosa.osax:0,vmll.vy:0,hmll.hx:0}
    rel_target_positions = {mllbs.bsx:500,mllbs.bsy:-500,mllosa.osax:2600,vmll.vy:500,hmll.hx:-500}
    slit_positions =  {ssa2.hgap:2,ssa2.vgap:2,s5.hgap:3.5,s5.vgap:3.5}

    do_motor_position_checks(check_list_before,
                             abs_tol = 20,
                             message_string = "This script works only when the optics are in IN position for safety")
    do_motor_position_checks(slit_positions,
                             rel_tol_per = 300,
                             message_string = "Slits are not in closed positions")

    if abs(fdet1.x.position)<12:
        yield from bps.movr(fdet1.x, -6)
        yield from bps.sleep(2)

    #close c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

    if abs(fdet1.x.position)>11.9:

        for mtr, pos in rel_target_positions.items():
            if not math.isclose(mtr.position,pos,rel_tol = 0.2):
                yield from bps.movr(mtr,pos)
                yield from bps.sleep(2)

    else:
        raise ValueError("Fluorescence detector motion failed")

    yield from bps.movr(ssa2.hgap,2,ssa2.vgap,2,s5.hgap,3.5,s5.vgap,3.5)

    do_motor_position_checks(rel_target_positions,message_string ="Failed to go to cam11 position")

    if move_cam11:
        yield from go_det("cam11")


def mll_to_nanobeam():

    check_list_before  = {mllbs.bsx:500,mllbs.bsy:-500,mllosa.osax:2600,vmll.vy:500,hmll.hx:-500,
                            ssa2.hgap:2,ssa2.vgap:2,s5.hgap:3.5,s5.vgap:3.5}

    rel_target_positions = {mllbs.bsx:-500,mllbs.bsy:500,mllosa.osax:-2600,vmll.vy:-500,hmll.hx:500}
    slits = {ssa2.hgap:-2,ssa2.vgap:-2,s5.hgap:-3.5,s5.vgap:-3.5}

    check_list_after = {mllbs.bsx:-0,mllbs.bsy:0,mllosa.osax:-0,vmll.vy:0,hmll.hx:0,
                            ssa2.hgap:0.05,ssa2.vgap:0.03,s5.hgap:0.08,s5.vgap:0.08}

    do_motor_position_checks(check_list_before,
                         abs_tol = 10,
                         message_string = "This script works only when the optics are in IN position for safety")
     #close c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

    for mtr, pos in rel_target_positions.items():
        if not math.isclose(mtr.position,pos,rel_tol = 0.3):
            yield from bps.movr(mtr,pos)
            yield from bps.sleep(5)

    if abs(hmll.hx.position)<20 and not abs(fdet1.x.position)>20:
        yield from bps.movr(fdet1.x, 6)

    else:
        raise ValueError("HMLL HX motion failed")

    yield from bps.movr(ssa2.hgap,-2,ssa2.vgap,-2,s5.hgap,-3.5,s5.vgap,-3.5)

    do_motor_position_checks(check_list_after,abs_tol = 5, message_string ="Failed to go to nanobeam position")


def zp_to_nanobeam(peak_the_flux_after = False):

    #close c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

    check_points = ["zposa.zposay", "zpbs.zpbsy"]

    for mtrs in check_points:
        if abs(eval(mtrs).position)<20:
            raise ValueError (f"{eval(mtrs).name} is close to zero; expected to be in out position")

    yield from bps.mov(ssa2.hgap, 0.05,ssa2.vgap, 0.03,s5.hgap,0.3,s5.vgap,0.3,)
    yield from bps.movr(zposa.zposay, -2700,zpbs.zpbsy, -100 )
    yield from bps.sleep(3)
    #caput("XF:03IDC-ES{IO:1}DO:1-Cmd",1)

    for mtr in check_points:
        if abs(eval(mtr).position)>20:
            raise ValueError(f"{eval(mtr).name} motion failed")


    #yield from center_ssa2(ic = None)
    if peak_the_flux_after:
        yield from peak_the_flux()

def zp_to_cam11_view():

    #close c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 0)

    #cam06 out in case
    caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', -50)
    caput("XF:03IDC-ES{CAM:06}cam1:Acquire",0)

    check_points = ["zposa.zposay", "zpbs.zpbsy"]

    for mtrs in check_points:
        if not abs(eval(mtrs).position)<20:
            raise ValueError (f"{eval(mtrs).name} is not at close to zero; you maymove it in to proceed")

    yield from bps.mov(ssa2.hgap, 2, ssa2.vgap, 2,s5.hgap, 4, s5.vgap, 4)

    yield from go_det("cam11")

    zp_osa_pos = caget("XF:03IDC-ES{ANC350:5-Ax:1}Mtr.VAL")

    if zp_osa_pos<100:

        caput("XF:03IDC-ES{ANC350:5-Ax:1}Mtr.VAL", zp_osa_pos+2700)

    #open c shutter
    caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0", 1)

    #move beam stop
    zp_bsx_pos = caget("XF:03IDC-ES{ANC350:8-Ax:1}Mtr.VAL")

    if zp_bsx_pos<20:

        caput("XF:03IDC-ES{ANC350:8-Ax:1}Mtr.VAL", zp_bsx_pos+100)


def zp_bs_out():

    if abs(zpbs.zpbsx.position)<10 and abs(zpbs.zpbsy.position)<10:

        yield from bps.movr(zpbs.zpbsy, 100)
        
    else:
        raise ValueError(f"bemastop positions are not close to zero."
                        f"bsy = {zpbs.zpbsx.position :.1f}")

def zp_bs_in():

    if abs(zpbs.zpbsy.position)>80:

        yield from bps.movr(zpbs.zpbsy, -100)
        
    else:
        raise ValueError(f"bemastop positions are close to out position."
                        f"bsy = {zpbs.zpbsx.position :.1f}")
    
def zp_osa_out():
    curr_pos = zposa.zposay.position
    if curr_pos >2000:
        raise ValueError('OSAY is out of IN range')
    else:
        # qmsg = QMessageBox.information(self, "info","OSAY is moving")
        # qmsg.setAutoClose(True)
        # qmsg.exec()
        yield from bps.movr(zposa.zposay, +2700)


def zp_osa_in():
    curr_pos = zposa.zposay.position
    if curr_pos < 2000:
        raise ValueError('OSAY is already close to IN position')
    else:
        yield from bps.movr(zposa.zposay, -2700)

def stop_all_mll_motion():
    hmll.stop()
    vmll.stop()
    mllosa.stop()
    mllbs.stop()
    smlld.stop()

def stop_all_zp_motion():
    zps.stop()
    zp.stop()
    zposa.stop()
    zpbs.stop()


def center_ssa2(ic = None):
    if ic is None:
        ic = sclr2_ch4

    yield from Energy.fluxOptimizerScan(ssa2.vcen,-0.05,0.05,10, ic = ic)
    plt.close()
    yield from Energy.fluxOptimizerScan(ssa2.hcen,-0.05,0.05,10, ic = ic)
    plt.close()
    yield from Energy.fluxOptimizerScan(ssa2.vcen,-0.02,0.02,10, ic = ic)
    plt.close()

def find_beam_at_ssa2(ic1_target_k = 400, max_iter = 1):


    #disengage feedbacks
    caput("XF:03IDC-CT{FbPid:01}PID:on",0)
    caput("XF:03IDC-CT{FbPid:02}PID:on",0)

    caput("XF:03ID-BI{EM:BPM1}fast_pidX.FBON",0)
    caput("XF:03ID-BI{EM:BPM1}fast_pidY.FBON",0)

    #move out FS
    caput('XF:03IDA-OP{FS:1-Ax:Y}Mtr.VAL', -20.)
    yield from bps.sleep(10)
    caput("XF:03IDA-BI{FS:1-CAM:1}cam1:Acquire",0)

    #move in CAM06
    caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', 0)
    caput("XF:03IDC-ES{CAM:06}cam1:Acquire",1)

    #b shutter open
    caput("XF:03IDB-PPS{PSh}Cmd:Opn-Cmd", 1)

    #get ic1 sensitivity and unit
    ic_sens = caget("XF:03IDC-CT{SR570:1}sens_num.VAL")
    ic_unit = caget("XF:03IDC-CT{SR570:1}sens_unit.VAL")

    #change IC1 sensivity to 10 um
    #caput the position of the value
    caput("XF:03IDC-CT{SR570:1}sens_num.VAL",3)
    caput("XF:03IDC-CT{SR570:1}sens_unit.VAL",2)

    #close b shutter, so that first iter works
    caput("XF:03IDB-PPS{PSh}Cmd:Cls-Cmd", 1)
    yield from bps.sleep(2)

    iter=0

    while caget("XF:03IDC-ES{Sclr:2}_cts1.B")<ic1_target_k*1000 and iter<max_iter:

        #b shutter open
        caput("XF:03IDB-PPS{PSh}Cmd:Opn-Cmd", 1)
        yield from bps.sleep(2)

        #fully open ssa2
        yield from bps.mov(ssa2.hgap, 2, ssa2.vgap, 2)

        #hfm
        yield from peak_hfm_pitch(fine = False, tweak_range = 0.05)
        yield from peak_dcm_roll(0.05)

        if not caget("XF:03IDC-ES{Sclr:2}_cts1.B")<1000:

            yield from peak_hfm_pitch(fine = False, tweak_range = 0.02)
            yield from bps.mov(ssa2.hgap, 0.5)
            yield from peak_hfm_pitch(fine = False, tweak_range = 0.005)
            yield from peak_hfm_pitch(fine = True, tweak_range = 0.2)

        #dcm_roll
        yield from bps.mov(ssa2.hgap, 2 ,ssa2.vgap, 0.5)
        yield from peak_dcm_roll(0.05)

        #fully open ssa2
        yield from bps.mov(ssa2.hgap, 2, ssa2.vgap, 2)
        iter += 1

        plt.close("all")

    #change back to initial sensitivity
    caput("XF:03IDC-CT{SR570:1}sens_num.VAL",ic_sens)



def take_cam11_flatfield():
    print("make sure that beam is on an empty area")

    #disable old correction
    caput("XF:03IDC-ES{CAM:11}Proc1:EnableFlatField",0)

    #save bg
    caput("XF:03IDC-ES{CAM:11}Proc1:SaveFlatField",1)

    #enable bg
    caput("XF:03IDC-ES{CAM:11}Proc1:EnableFlatField",1)

    #set counts to 2500
    #caput("loc://Ccam_11Max(65536)",2500)


################Plans for Peaking flux with Feedbacks##############

def peak_with_voltage(start,end,n_steps, pv_name = "XF:03ID-BI{EM:BPM1}DAC0"):

    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')

    if shutter_b_cls_status == 0:

        dcm_pitch_volt = caget(pv_name)
        x = np.linspace(dcm_pitch_volt+start,dcm_pitch_volt+end,n_steps+1)
        y = np.arange(n_steps+1)

        for i in tqdm.tqdm(range(n_steps+1),desc = 'peaking flux'):

            caput(pv_name,x[i])
            yield from bps.sleep(4)
            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()
            else:
                y[i] = sclr2_ch4.get()

            if i>2:
                change = np.diff(y)
            if change[-1]<0 and change[-2]<0:
                break

        peak = x[y == np.max(y)]

        yield from bps.sleep(3)
        caput(pv_name,peak[0])
        yield from bps.sleep(3)

    else:
        print('Shutter B is Closed')
        return


def peak_xy_volt(iter = 1):

    for i in tqdm.tqdm(range(iter)):
        # yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03ID-BI{EM:BPM1}DAC0")
        # yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03ID-BI{EM:BPM1}DAC1")
        yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03IDB-BI:{NSLS2_EM:}DAC-Chan1-Sp")
        yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03IDB-BI:{NSLS2_EM:}DAC-Chan2-Sp")



def peak_bpm_x(start,end,n_steps):
    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')

    if shutter_b_cls_status == 0:

        caput('XF:03IDC-ES{Status}ScanRunning-I', 1)
        bpm_y_0 = caget('XF:03ID-BI{EM:BPM1}fast_pidX.VAL')
        x = np.linspace(bpm_y_0+start,bpm_y_0+end,n_steps+1)
        y = np.arange(n_steps+1)
        #print(x)
        for i in range(n_steps+1):
            caput('XF:03ID-BI{EM:BPM1}fast_pidX.VAL',x[i])
            if i == 0:
                yield from bps.sleep(3)
            else:
                yield from bps.sleep(2)

            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()
            else:
                y[i] = sclr2_ch4.get()


            if i>2:
                change = np.diff(y)
                if change[-1]<0 and change[-2]<0:
                    break

        peak = x[y == np.max(y)]

        #plt.figure()
        #plt.plot(x,y)
        #plt.hold(2)
        #plt.close()

        #print(peak)
        caput('XF:03ID-BI{EM:BPM1}fast_pidX.VAL',peak[0])
        yield from bps.sleep(5)

        # xbpmc_x = caget('XF:03ID-BI{EM:BPM2}PosX:MeanValue_RBV')
        # xbpmc_y = caget('XF:03ID-BI{EM:BPM2}PosY:MeanValue_RBV')
        # print(xbpmc_x,xbpmc_y)
        # caput('XF:03IDC-CT{FbPid:03}PID.VAL',xbpmc_y)
        # caput('XF:03IDC-CT{FbPid:04}PID.VAL',xbpmc_x)
        caput('XF:03IDC-ES{Status}ScanRunning-I', 0)


    else:
        print('Shutter B is Closed')

    #plt.pause(5)
    #plt.close()

def peak_bpm_y(start,end,n_steps):
    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')


    if shutter_b_cls_status == 0:

        caput('XF:03IDC-ES{Status}ScanRunning-I', 1)
        bpm_y_0 = caget('XF:03ID-BI{EM:BPM1}fast_pidY.VAL')
        x = np.linspace(bpm_y_0+start,bpm_y_0+end,n_steps+1)
        y = np.arange(n_steps+1)
        #print(x)
        for i in range(n_steps+1):
            caput('XF:03ID-BI{EM:BPM1}fast_pidY.VAL',x[i])
            if i == 0:
                yield from bps.sleep(5)
            else:
                yield from bps.sleep(2)

            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()

            else:
                y[i] = sclr2_ch4.get()

            if i>2:
                 change = np.diff(y)
                 if change[-1]<0 and change[-2]<0:
                     break


        peak = x[y == np.max(y)]
        #plt.figure()
        #plt.plot(x,y)
        #plt.hold(2)
        #plt.close()
        #print(peak)
        caput('XF:03ID-BI{EM:BPM1}fast_pidY.VAL',peak[0])
        yield from bps.sleep(2)

        # xbpmc_x = caget('XF:03ID-BI{EM:BPM2}PosX:MeanValue_RBV')
        # xbpmc_y = caget('XF:03ID-BI{EM:BPM2}PosY:MeanValue_RBV')
        # print(xbpmc_x,xbpmc_y)
        # caput('XF:03IDC-CT{FbPid:03}PID.VAL',xbpmc_y)
        # caput('XF:03IDC-CT{FbPid:04}PID.VAL',xbpmc_x)
        caput('XF:03IDC-ES{Status}ScanRunning-I', 0)


    else:
        print('Shutter B is Closed')

    #plt.pause(5)
    #plt.close()

def peak_all(x_start = -25,x_end=25,x_n_step=50, y_start = -15,y_end=15, y_n_step=30):

	peak_bpm_y(y_start,y_end,y_n_step)
	peak_bpm_x(x_start,x_end,x_n_step)
	peak_bpm_y(y_start,y_end,y_n_step)


def peak_the_flux():

    """ Scan the c-bpm set points to find IC3 maximum """
    try:
        #open c
        caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0",1)

        if abs(caget("XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.RBV")) <10:
            raise ValueError ("CAM06 is IN, move it out and try again")

        print("Peaking the flux.")
        yield from bps.sleep(2)
        yield from peak_bpm_y(-15,15,10)

        yield from bps.sleep(1)
        yield from peak_bpm_x(-15,15,6)

        yield from bps.sleep(1)
        yield from peak_bpm_y(-4,4,10)

        #close c
        caput("XF:03IDC-ES{Zeb:2}:SOFT_IN:B0",0)

    except: pass



def toggle_merlin_filter(filter_to  = "in"):

    if filter_to == "in":
        caput("XF:03IDC-ES{IO:1}DO:1-Cmd",1)
        time.sleep(2)

        if caget("XF:03IDC-ES{IO:1}DO:1-Sts") != 1:
            raise ValueError("filter motion failed")

    elif filter_to == "out":
        caput("XF:03IDC-ES{IO:1}DO:1-Cmd",0)

        time.sleep(2)
        if caget("XF:03IDC-ES{IO:1}DO:1-Sts") != 0:
            raise ValueError("filter motion failed")
        
def toggle_det_filter(pv, status_pv, filter_to  = "in"):

    if filter_to == "in":
        caput(pv,1)
        time.sleep(2)

        if caget(status_pv) != 1:
            raise ValueError("filter motion failed")

    elif filter_to == "out":
        caput(pv,0)

        time.sleep(2)
        if caget(status_pv) != 0:
            raise ValueError("filter motion failed")


def recover_from_beamdump(peak_after = True):
    for i in range(2):

        if caget("XF:03ID-BI{EM:BPM1}fast_pidX.FBON") or caget("XF:03ID-BI{EM:BPM1}fast_pidY.FBON"):

            #turn_off_b_feedbacks
            caput("XF:03ID{XBPM:17}AutoFbEn-Cmd",0)
            caput("XF:03ID-BI{EM:BPM1}fast_pidX.FBON",0)
            caput("XF:03ID-BI{EM:BPM1}fast_pidY.FBON",0)

        dcm_pitch_set = caget("XF:03IDA-OP{Mon:1-Ax:P}Mtr.VAL")
        dcm_roll_set = caget("XF:03IDA-OP{Mon:1-Ax:R}Mtr.VAL")

        mon_pf_V = caget("XF:03ID-BI{EM:BPM1}DAC0")
        mon_rf_V = caget("XF:03ID-BI{EM:BPM1}DAC1")

        caput("XF:03ID-BI{EM:BPM1}DAC0",mon_pf_V)
        yield from bps.sleep(5)
        caput("XF:03ID-BI{EM:BPM1}DAC1", mon_rf_V)
        yield from bps.sleep(5)


        yield from bps.mov(dcm.p, dcm_pitch_set,dcm.r, dcm_roll_set)
        yield from bps.sleep(5)

        if not math.isclose(dcm.p.position, dcm_pitch_set, abs_tol=0.02) or \
        not math.isclose(dcm.r.position, dcm_roll_set, abs_tol=0.02):
            raise ValueError("Failed! DCM positions not within 5% of the set values")



    caput("XF:03ID{XBPM:17}AutoFbEn-Cmd",1)

    if peak_after:

        yield from peak_the_flux()

def calc_zpz_with_energy(energy=9):

    ref_energy = 9
    ref_zpz1 = -8.205
    per_ev_corr = 6.093

    calc_zpz1 = ref_zpz1 +((ref_energy-energy)* per_ev_corr)

    return calc_zpz1


def move_zpz_with_energy(energy=9, move_zpz1 = False):

    calc_zpz1 = calc_zpz_with_energy(energy)

    print(f"Estimated ZPZ1 position = {calc_zpz1 :.3f}")

    if move_zpz1:

        if np.logical_and(calc_zpz1>-50,calc_zpz1<8):
            yield from mov_zpz1(calc_zpz1)

        else: raise ValueError(f"{calc_zpz1} is out of safe range. Try manual override")


    return calc_zpz1


plt.close()

close_he_valve = lambda: caput('XF:03IDC-ES{IO:1}DO:4-Cmd', 0)
open_he_valve = lambda: caput('XF:03IDC-ES{IO:1}DO:4-Cmd', 1)


def get_component_state(parent_ = dcm):

    return {f"{parent_.name}.{comp}.position":eval(f"parent_.{comp}.position") for comp in parent_.component_names}

def get_microscope_state():
    #TODO
    optics_included = [ugap,hcm,dcm,hfm,vms,ssa2,s5]

    state_dict = {}

def piezos_to_zero(zp_flag = True):
    
    if zp_flag:
        yield from bps.mov(zpssx,0,zpssy,0,zpssz,0)  
    else:
        yield from bps.mov(dssx,0,dssy,0,dssz,0)   

def cam06_in():
    yield from bps.sleep(1)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', 0)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:Y}Mtr.VAL', 0)

def cam06_out():
    yield from bps.sleep(1)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', -60)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:Y}Mtr.VAL', 0)

def cam06_laser_in():
    yield from bps.sleep(1)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', -32.5)
    caput('XF:03IDC-OP{Stg:CAM6-Ax:Y}Mtr.VAL', 1.5)




def move_xrf_det(taret_pos):
    yield from bps.mov(fdet1.x, taret_pos)

def xrf_det_out():
    """Returns a plan to move the XRF detector to -107."""
    # Returns a NEW generator plan every time it is called
    return move_xrf_det(-107)

# Function to move the motor forward and backward
def test_motor_motion(motor, move_percent = 1):
    """
    Move a motor forward by a specified amount and then backward by the same amount.
    Handles any errors during the process.

    Args:
        motor (Motor): The motor object.
        move_amount (float): The amount to move the motor forward and backward.
    """
    try:
        move_amount = motor.position*move_percent*0.01
        print(f"Moving {motor.name} forward by {move_amount}")
        yield from bps.movr(motor,move_amount)
    except Exception as e:
        print(f"Error during forward move: {e}")

    try:
        print(f"Moving {motor.name} backward by {-move_amount}")
        yield from bps.movr(motor,-1*move_amount)
    except Exception as e:
        print(f"Error during backward move: {e}")



def test_all_child_motors(parent_name = 'diff', move_percent = 1):

    for chld in eval(parent_name).component_names:
        motor = eval(f'{parent_name}.{chld}')
        curr_pos = motor.position
        if type(motor).__name__ == "EpicsMotor":
            print(curr_pos)
            yield from test_motor_motion(motor, move_percent = move_percent)
            

def test_all_critical_motors(check_list = ['diff','ssa2','s5','fdet1', 'm2', 'm1'
                                           'dcm', 's1', 'zp', 'zps', 'zpbs', 'zposa']):
    
    for parent in check_list:
        yield   from test_all_child_motors(parent_name = parent, 
                                           move_percent = 1)

def move_cam6(x = 0, y = 0):

    yield from bps.mov(cam6.x, x, cam6.y , y)

def cam6_out():
    return move_cam6(x = -60, y = 0)

def cam6_in():
    return move_cam6(x = 0, y = 0)

def cam6_to_laser():
    return move_cam6(x = -35.25, y = 0.45)


def move_fs1_y(target_pos):
    yield from bps.mov(fs1_y, target_pos)

def fs_out():
    """Move fs1_y out to -20."""
    # This function returns a NEW generator plan when called
    return move_fs1_y(-20)

def fs_in():
    """Move fs1_y in to -57."""
    # This function returns a NEW generator plan when called
    return move_fs1_y(-57)

def move_dexela(x = 0, y = 0):
    yield from bps.mov(dexela.x, x, dexela.y , y)










