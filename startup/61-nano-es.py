import os
if os.path.isfile('/data/users/startup_parameters/USE_RASMI'):
    USE_RASMI = True
else:
    USE_RASMI = False

if not USE_RASMI:
    print(f"RASMI not used, skipping {__file__!r} ...")
    import sys
    sys.exit()
    
print(f"Loading {__file__!r} ...")

class HXN_NanoStage(Device):
    ssx = Cpt(EpicsMotor, '{PT:Smpl-Ax:ssx}Mtr')  # Scanning piezo X
    ssy = Cpt(EpicsMotor, '{PT:Smpl-Ax:ssy}Mtr')
    ssz = Cpt(EpicsMotor, '{PT:Smpl-Ax:ssz}Mtr')
    th = Cpt(EpicsMotor, '{PT:Smpl-Ax:th}Mtr')
    cx = Cpt(EpicsMotor, '{PT:Smpl-Ax:cx}Mtr')
    cz = Cpt(EpicsMotor, '{PT:Smpl-Ax:cz}Mtr')

    bs_x = Cpt(EpicsMotor, '{PT:BS-Ax:X}Mtr')
    bs_y = Cpt(EpicsMotor, '{PT:BS-Ax:Y}Mtr')
    bs_z = Cpt(EpicsMotor, '{PT:BS-Ax:Z}Mtr')
    bs_rz = Cpt(EpicsMotor, '{PT:BS-Ax:rz}Mtr')

    hm_x = Cpt(EpicsMotor, '{PT:HM-Ax:X}Mtr')
    hm_y = Cpt(EpicsMotor, '{PT:HM-Ax:Y}Mtr')
    hm_z = Cpt(EpicsMotor, '{PT:HM-Ax:Z}Mtr')
    hm_ry = Cpt(EpicsMotor, '{PT:HM-Ax:ry}Mtr')

    zp_x = Cpt(EpicsMotor, '{PT:OP-Ax:X}Mtr')
    zp_y = Cpt(EpicsMotor, '{PT:OP-Ax:Y}Mtr')
    zp_z = Cpt(EpicsMotor, '{PT:OP-Ax:Z}Mtr')
    zp_rx = Cpt(EpicsMotor, '{PT:OP-Ax:rx}Mtr')
    zp_ry = Cpt(EpicsMotor, '{PT:OP-Ax:ry}Mtr')

    osa_x = Cpt(EpicsMotor, '{PT:OSA-Ax:X}Mtr')
    osa_y = Cpt(EpicsMotor, '{PT:OSA-Ax:Y}Mtr')
    osa_z = Cpt(EpicsMotor, '{PT:OSA-Ax:Z}Mtr')

    sb_x = Cpt(EpicsMotor, '{PT:SmplBase-Ax:X}Mtr')
    sb_y = Cpt(EpicsMotor, '{PT:SmplBase-Ax:Y}Mtr')
    sb_z = Cpt(EpicsMotor, '{PT:SmplBase-Ax:Z}Mtr')

    vm_x = Cpt(EpicsMotor, '{PT:VM-Ax:X}Mtr')
    vm_y = Cpt(EpicsMotor, '{PT:VM-Ax:Y}Mtr')
    vm_z = Cpt(EpicsMotor, '{PT:VM-Ax:Z}Mtr')
    vm_rx = Cpt(EpicsMotor, '{PT:VM-Ax:rx}Mtr')
    vm_rz = Cpt(EpicsMotor, '{PT:VM-Ax:rz}Mtr')

    slt_vgap = Cpt(EpicsMotor, '{Slt:4-Ax:X}Mtr')
    slt_vcen = Cpt(EpicsMotor, '{Slt:4-Ax:Y}Mtr')
    slt_hgap = Cpt(EpicsMotor, '{Slt:4-Ax:Z}Mtr')
    slt_hcen = Cpt(EpicsMotor, '{Slt:4-Ax:Top}Mtr')

    p1_pos0 = Cpt(EpicsSignalRO, '{Pico:1}POS_0')
    p1_pos1 = Cpt(EpicsSignalRO, '{Pico:1}POS_1')
    p1_pos2 = Cpt(EpicsSignalRO, '{Pico:1}POS_2')


pt_tomo = HXN_NanoStage('XF:03IDC-ES', name='pt_tomo')

class HXN_KBStage(Device):
    hm_ry = Cpt(EpicsMotor,'{Mir:KB-Ax:1}Mtr')
    hm_x = Cpt(EpicsMotor,'{Mir:KB-Ax:2}Mtr')
    vm_rx = Cpt(EpicsMotor,'{Mir:KB-Ax:3}Mtr')
    vm_z = Cpt(EpicsMotor,'{Mir:KB-Ax:4}Mtr')
    vm_y = Cpt(EpicsMotor,'{Mir:KB-Ax:5}Mtr')
    vm_rz = Cpt(EpicsMotor,'{Mir:KB-Ax:6}Mtr')

    hpitch_coarse = Cpt(EpicsMotor,'{Mir:KBh-Ax:fp}Mtr')
    hvitch_coarse = Cpt(EpicsMotor,'{Mir:KBv-Ax:fp}Mtr')

kb_stage = HXN_KBStage('XF:03IDC-ES', name='kb_stage')

# Temporary disable a motor (e.g. if the motor is not functioning and PVs are not accessible)
setattr(pt_tomo.ssx, "is_disabled", False)
setattr(pt_tomo.ssy, "is_disabled", False)
setattr(pt_tomo.ssz, "is_disabled", True)

sd.baseline.extend([
    kb_stage.hm_ry,
    kb_stage.hm_x,
    kb_stage.vm_rx,
    kb_stage.vm_z,
    kb_stage.vm_y,
    kb_stage.vm_rz]
)

# KB sample stage
sd.baseline.extend([
    p_sbx,
    p_sby,
    p_sbz]
)

sd.baseline.extend([
    pt_tomo.ssx,
    pt_tomo.ssy,
    # pt_tomo.ssz,
    pt_tomo.cx,
    pt_tomo.cz,
    pt_tomo.th,

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
    pt_tomo.zp_rx,
    pt_tomo.zp_ry,

    pt_tomo.osa_x,
    pt_tomo.osa_y,
    pt_tomo.osa_z,

    pt_tomo.sb_x,
    pt_tomo.sb_y,
    pt_tomo.sb_z,

    pt_tomo.vm_x,
    pt_tomo.vm_y,
    pt_tomo.vm_z,
    pt_tomo.vm_rx,
    pt_tomo.vm_rz,

    pt_tomo.slt_vgap,
    pt_tomo.slt_vcen,
    pt_tomo.slt_hgap,
    pt_tomo.slt_hcen,
])

ptssx = pt_tomo.ssx
ptssy = pt_tomo.ssy
ptssz = pt_tomo.ssz

# # Interferometers
# class SRXNanoInterferometer(Device):
#     posX = Cpt(EpicsSignalRO, 'POS_0')
#     posY = Cpt(EpicsSignalRO, 'POS_1')
#     posZ = Cpt(EpicsSignalRO, 'POS_2')


# nanoKB_interferometer = SRXNanoInterferometer('XF:05IDD-ES:1{PICOSCALE:1}', name='nanoKB_interferometer')


stages_to_move = [pt_tomo.ssx, pt_tomo.ssy, pt_tomo.ssz]
velocity_slow = 30
velocity_fast = 300

def set_scanner_velocity(velocity=velocity_slow):
    for d in stages_to_move:
        if not getattr(d, "is_disabled", False):
            yield from bps.mv(d.velocity, velocity)

def reset_scanner_velocity():
    for d in stages_to_move:
        if not getattr(d, "is_disabled", False):
            yield from bps.mv(d.velocity, velocity_fast)


