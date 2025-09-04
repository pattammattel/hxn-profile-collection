print(f"Loading {__file__!r} ...")

from ophyd import (EpicsMotor, Device, Component as Cpt)
class SigrayMll(Device):
    mll_x = Cpt(EpicsMotor, 'XF:03IDC-CT{SmarAct:Sigray1}:m10')
    mll_y = Cpt(EpicsMotor, 'XF:03IDC-CT{SmarAct:Sigray1}:m11')
    mll_z = Cpt(EpicsMotor, 'XF:03IDC-CT{SmarAct:Sigray1}:m12')
    mll_ry = Cpt(EpicsMotor,'XF:03IDC-CT{SmarAct:Sigray1}:m13')
    mll_rx = Cpt(EpicsMotor, 'XF:03IDC-CT{SmarAct:Sigray1}:m14')

class HxnPrototypeMicroscope(Device):
    vx = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:1}Mtr')
    vy = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:2}Mtr')
    vz = Cpt(EpicsMotor, 'XF:03IDC-ES{MC:4-Ax:8}Mtr')

    v_rz = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:3}Mtr')
    v_rx = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:4}Mtr')
    #v_ry = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:4-Ax:1}Mtr')

    osa_rz = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:5}Mtr')
    osa_ry = Cpt(EpicsMotor,'XF:03IDC-ES{MC:4-Ax:1}Mtr')
    osay = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:6}Mtr')
    osax = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:7}Mtr')
    osaz = Cpt(EpicsMotor, 'XF:03IDC-ES{Proto:1-Ax:8}Mtr')

    #ssx = Cpt(EpicsMotor, 'XF:03IDC-ES{Ddrive:1-Ax:2}Mtr')
    #ssy = Cpt(EpicsMotor, 'XF:03IDC-ES{Ddrive:1-Ax:3}Mtr')
    #ssz = Cpt(EpicsMotor, 'XF:03IDC-ES{Ddrive:1-Ax:1}Mtr')

    #vz = Cpt(EpicsMotor, 'XF:03IDC-ES{MMC100:1-Ax:1}Mtr')
    #cz = Cpt(EpicsMotor, 'XF:03IDC-ES{MMC100:1-Ax:2}Mtr')
    #cx = Cpt(EpicsMotor, 'XF:03IDC-ES{MMC100:1-Ax:3}Mtr')
    #cy = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:9-Ax:0}Mtr')
    #bz = Cpt(EpicsMotor, 'XF:03IDC-ES{MC:4-Ax:4}Mtr')
    #bx = Cpt(EpicsMotor, 'XF:03IDC-ES{MC:4-Ax:2}Mtr')

    # bsx = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:1}Mtr')
    # bsy = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:3}Mtr')
    # bsz = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:3-Ax:2}Mtr')

    #vth = Cpt(EpicsMotor, 'XF:03IDC-ES{MCS:4-Ax:1}Mtr')


p = HxnPrototypeMicroscope('', name='p')
sigray = SigrayMll('', name='sigray')

p_vx = p.vx
p_vy = p.vy
p_vz = p.vz
p_v_rx = p.v_rx
# p_v_ry = p.v_ry
p_v_rz = p.v_rz

p_osa_rz = p.osa_rz
p_osa_ry = p.osa_ry
p_osay = p.osay
p_osax = p.osax
p_osaz = p.osaz

#p_ssx = p.ssx
#p_ssy = p.ssy
#p_ssz = p.ssz

#p_vz = p.vz
#p_cz = p.cz
#p_cx = p.cx
#p_cy = p.cy
#p_bz = p.bz
#p_bx = p.bx

# p_bsx = p.bsx
# p_bsy = p.bsy
# p_bsz = p.bsz

#p_vth = p.vth

class HxnPrototypeSample(Device):
    sbx = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:9-Ax:3}Mtr')
    sby = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:9-Ax:2}Mtr')
    sbz = Cpt(EpicsMotor, 'XF:03IDC-ES{ANC350:9-Ax:1}Mtr')


ps = HxnPrototypeSample('', name='ps')
p_sbx = ps.sbx
p_sby = ps.sby
p_sbz = ps.sbz

class HxnPrototypePhasePlate(Device):
    pp_x = Cpt(EpicsMotor, 'XF:03IDC-ES{PPlate:X}Mtr')
    pp_y = Cpt(EpicsMotor, 'XF:03IDC-ES{PPlate:Y}Mtr')

pp = HxnPrototypePhasePlate('',name='pp')
p_pp_x = pp.pp_x
p_pp_y = pp.pp_y

