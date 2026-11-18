print(f"Loading {__file__!r} ...")

import json
import numpy as np
import tqdm
from datetime import datetime
from pathlib import Path
from hxntools.motor_info import motor_table


# ============================================================================
# PLAN LOGGING SYSTEM
# ============================================================================
# Tracks execution of run_* plans to enable recovery if interrupted.
# Logs are saved to /nsls2/data/hxn/legacy/users/json_plans_log/ in JSONL 
# format with monthly rotation (plan_name_MMYYYY.jsonl) to prevent files 
# from becoming too large.
# ============================================================================

class PlanLogger:
    """Logger for tracking plan executions to JSONL files organized by month/year.
    
    This class manages execution history for run_* plans, enabling recovery and
    debugging if plans are interrupted. Logs are automatically organized by plan
    name and month to keep file sizes manageable.
    
    Usage:
        from 72-json-plans import PlanLogger
        
        # At plan start
        PlanLogger.log_plan_start(
            plan_name="run_diff_json",
            json_path=path_to_json,
            extra_params={"do_confirm": do_confirm}
        )
        
        # At plan end
        try:
            # ... plan execution ...
            PlanLogger.log_plan_end(
                plan_name="run_diff_json",
                status="completed",
                extra_data={"angles_completed": len(angles)}
            )
        except Exception as e:
            PlanLogger.log_plan_end(
                plan_name="run_diff_json",
                status="failed",
                error_msg=str(e)
            )
            raise
    
    Log Format (JSONL):
        Each line is a complete JSON object with:
        - timestamp: ISO format datetime of the event
        - event: 'started', 'completed', or 'failed'
        - json_path: Path to the JSON configuration file (start event only)
        - params: Additional parameters (optional)
        - error: Error message if status is 'failed' (optional)
        - data: Additional data like scan IDs (optional)
        
        Example:
            {"timestamp": "2026-11-04T15:30:45.123456", "event": "started", 
             "json_path": "/data/users/current_user/diff_params.json"}
            {"timestamp": "2026-11-04T15:45:30.654321", "event": "completed", 
             "data": {"angles_completed": 45}}
    
    File Organization:
        /nsls2/data/hxn/legacy/users/json_plans_log/
        ├── run_tomo_json_112026.jsonl         (November 2026)
        ├── run_diff_json_112026.jsonl
        ├── run_repeat_2d_json_112026.jsonl
        ├── run_tomo_json_122026.jsonl         (December 2026)
        └── ...
    
    Recovery Workflow:
        1. Check logs to identify failure point:
           tail /nsls2/data/hxn/legacy/users/json_plans_log/run_diff_json_*.jsonl
        
        2. Review parameters and last completed event
        
        3. Modify JSON config if needed (e.g., change start angle)
        
        4. Re-run plan - new entries will be appended to the same month's file
    """
    
    LOG_BASE_PATH = "/nsls2/data/hxn/legacy/users/json_plans_log"
    
    @classmethod
    def ensure_log_directory(cls):
        """Create log directory if it doesn't exist.
        
        Returns:
            bool: True if directory exists or was created successfully, False otherwise
        """
        try:
            log_dir = Path(cls.LOG_BASE_PATH)
            log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Warning: Could not create log directory {cls.LOG_BASE_PATH}: {e}")
            return False
    
    @classmethod
    def get_log_filepath(cls, plan_name):
        """Get the JSONL filepath for a plan, named with month/year.
        
        Args:
            plan_name (str): Name of the plan (e.g., 'run_diff_json')
        
        Returns:
            str: Full path to the JSONL log file
        
        Examples:
            run_diff_json -> /nsls2/data/.../run_diff_json_112026.jsonl (Nov 2026)
            run_tomo_json -> /nsls2/data/.../run_tomo_json_112026.jsonl
        """
        now = datetime.now()
        month_year = now.strftime("%m%Y")  # Format: MMYYYY
        filename = f"{plan_name}_{month_year}.jsonl"
        return Path(cls.LOG_BASE_PATH) / filename
    
    @classmethod
    def log_plan_start(cls, plan_name, json_path, extra_params=None):
        """Log the start of a plan execution.
        
        Args:
            plan_name (str): Name of the plan (e.g., 'run_diff_json')
            json_path (str): Path to the JSON configuration file
            extra_params (dict, optional): Additional parameters to log
                (e.g., {'do_confirm': True, 'n_repeat': 10})
        
        Returns:
            None
        
        Example:
            PlanLogger.log_plan_start(
                plan_name="run_repeat_2d_json",
                json_path="/data/users/current/diff_params.json",
                extra_params={"n_repeat": 10, "scan_angle": 45.5}
            )
        """
        if not cls.ensure_log_directory():
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "started",
            "json_path": str(json_path),
        }
        if extra_params:
            log_entry["params"] = {
                key: str(value) if isinstance(value, Path) else value
                for key, value in extra_params.items()
            }
        
        try:
            log_filepath = cls.get_log_filepath(plan_name)
            with open(log_filepath, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error logging plan start: {e}")
    
    @classmethod
    def log_plan_end(cls, plan_name, status="completed", error_msg=None, extra_data=None):
        """Log the completion or failure of a plan.
        
        Args:
            plan_name (str): Name of the plan (e.g., 'run_diff_json')
            status (str): 'completed' or 'failed' (default: 'completed')
            error_msg (str, optional): Error message if status is 'failed'
            extra_data (dict, optional): Additional data like scan IDs, angles completed, etc.
        
        Returns:
            None
        
        Example - Successful completion:
            PlanLogger.log_plan_end(
                plan_name="run_diff_json",
                status="completed",
                extra_data={
                    "scan_ids": [100, 101, 102],
                    "angles_completed": 45,
                    "total_angles": 50
                }
            )
        
        Example - Failure:
            PlanLogger.log_plan_end(
                plan_name="run_diff_json",
                status="failed",
                error_msg="Beam dump occurred at angle 30.5"
            )
        """
        if not cls.ensure_log_directory():
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": status,
        }
        if error_msg:
            log_entry["error"] = error_msg
        if extra_data:
            log_entry["data"] = extra_data
        
        try:
            log_filepath = cls.get_log_filepath(plan_name)
            with open(log_filepath, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error logging plan end: {e}")


# Initialize logging directory on startup
if PlanLogger.ensure_log_directory():
    print(f"Plan logger initialized: {PlanLogger.LOG_BASE_PATH}")
else:
    print(f"Warning: Plan logger disabled - could not access {PlanLogger.LOG_BASE_PATH}")


# ============================================================================
# PLAN LOGGING INTEGRATION GUIDE
# ============================================================================
# The PlanLogger class above is ready to use. To integrate logging into the
# run_* functions (run_tomo_json, run_diff_json, run_repeat_2d_json):
#
# STEP 1: At the start of each run_* function (after docstring), add:
#     PlanLogger.log_plan_start(
#         plan_name="run_diff_json",
#         json_path=path_to_json,
#         extra_params={"do_confirm": do_confirm}  # optional
#     )
#
# STEP 2: At the end of each function, wrap in try/except:
#     try:
#         # ... existing function code ...
#         PlanLogger.log_plan_end(
#             plan_name="run_diff_json",
#             status="completed",
#             extra_data={"angles_completed": len(angles)}  # optional
#         )
#     except Exception as e:
#         PlanLogger.log_plan_end(
#             plan_name="run_diff_json",
#             status="failed",
#             error_msg=str(e)
#         )
#         raise
#
# TESTING:
#   1. Verify syntax: python3 -m py_compile startup/72-json-plans.py
#   2. Run a test plan
#   3. Check logs: ls -la /nsls2/data/hxn/legacy/users/json_plans_log/
#   4. View logs: tail run_diff_json_*.jsonl
#   5. Verify JSON: python3 -c "import json; [json.loads(l) for l in open('run_diff_json_*.jsonl')]"
#
# RECOVERY WORKFLOW:
#   1. Check logs: tail /nsls2/data/hxn/legacy/users/json_plans_log/run_diff_json_*.jsonl
#   2. Review parameters and identify failure point
#   3. Modify JSON config if needed (e.g., change start angle)
#   4. Re-run plan - new entries will be appended to same month's file
#
# FUNCTIONS NEEDING LOGGING:
#   • run_tomo_json(path_to_json, tracking_file=None) - Line ~575
#   • run_diff_json(path_to_json, tracking_file=None, do_confirm=True) - Line ~1094
#   • run_repeat_2d_json(path_to_json, n_repeat=10, tracking_file=None, do_confirm=True) - Line ~1445
#
# ============================================================================
# END PLAN LOGGING INTEGRATION GUIDE
# ============================================================================

det_dict = {"dets1":dets1,
            "dets2":dets2,
            "dets_fs":dets_fs}

mll_fly_motors= ["dssx", "dssy","dssz"]
mll_th_motor= "dsth"

zp_fly_motors= ["zpssx", "zpssy","zpssz"]
zp_th_motor= "zpsth"




#tomo_use_panda = False

def make_tomo_plan(save_as = "/nsls2/data/hxn/legacy/user_macros/HXN_GUI/Scan/temp_files/tomo_params.json" ):

    tomo_scan =     {"flying_panda":True,
                     "fly_motors":["dssx", "dssy","dssz"],
                     "th_motor":"dsth",
                    "angle_info":{"start":-90,
                                "end":90,
                                "angle_step":2},

                    "fly2d_scan":{'det':'dets1',
                                "x_start":-1,
                                "x_end":1,
                                "x_num":100,
                                "y_start":-1,
                                "y_end":1,
                                "y_num":100,
                                "exposure":0.03},

                    "xalign": {
                        "do_align": True,
                        "start": -10,
                        "end": 10,
                        "num": 300,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False
                    },
                    "yalign": {
                        "do_align": True,
                        "start": -4,
                        "end": 4,
                        "num": 200,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5
                    },
                    "align_2d_com": {
                        "do_align": False,
                        "x_start": -5,
                        "x_end": 5,
                        "x_num": 50,
                        "y_start": -2,
                        "y_end": 2,
                        "y_num": 20,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "threshold": 0.5,
                        "move_x": True,
                        "move_y": True,
                        "x_offset": -0.95,
                        "y_offset": -0.2,
                        "zero_before_scan": False
                    },

                    "stop_iter":False,
                    "add_angles":[ ],
                    "remove_angles":[-90,-91],
                    "stop_pdf":False,
                    "pdf_elems":["Au_L"],
                    "pause_scan":False,
                    "test":False,
                    "ic_threshold":0.9,
                    "do_y_offset": True,
                    "th_init": 58.99987099999999,
                    "y_init": -0.18154,
                    "scan_label":"HXN_Tomo_Scan",
                    "Notes": 'My sample # 10'
                }

    with open(save_as,"w") as fp:
            json.dump(tomo_scan,fp, indent=6)

    fp.close()

def align_scan(mtr, start, end, num, exp, elem_, align_with="line_center",
               threshold=0.5, move_coarse=False, neg_flag=False, offset=0,
               tomo_use_panda=True, reset_piezos_to_zero=False, initial_position=0, 
               align_movement_limit=0, line_center_mode='binary', on_fit_error=None):

    """
    Scan to align samples to field of view using fly1d scan

    Parameters
    ----------
    mtr : Motor
        Scanning motor (dssx, dssy, dssz, etc.)
    start, end, num, exp : float
        Flyscan parameters
    elem_ : str
        Element to use for alignment
    align_with : str, optional
        Choose between "edge" or "line_center" (default: "line_center")
    on_fit_error : tuple or None, optional
        Fallback value if edge fit fails. Must be 2-tuple (edge_pos, fwhm).
        If None (default), skips motor movement on fit failure.
        Pass (x_value, y_value) to move to that position on failure.
    
    Returns
    -------
    float
        Final motor position set by alignment
    """
    fly_to_coarse = {"zpssx":smarx,
                     "zpssy":smary,
                     "zpssz":smarz,
                     "dssx":dsx,
                     "dssy":dsy,
                     "dssz":dsz}

    if reset_piezos_to_zero:
            yield from bps.mov(mtr,0,wait=True)

    if not tomo_use_panda:
        yield from fly1d(dets_fs,
                        mtr,
                        start,
                        end,
                        num,
                        exp
                        )
    else:
        print("uses panda scan")
        yield from fly1dpd([fs,xspress3],
                        mtr,
                        start,
                        end,
                        num,
                        exp
                        )
    if align_with == "line_center":
        yield from bps.sleep(1)
        xc = return_line_center(-1,elem_,
                                threshold, 
                                neg_flag=neg_flag, 
                                mode=line_center_mode)
        xc = xc+offset
        
    elif align_with == "edge":
        yield from bps.sleep(1)
        xc, fwhm = erf_fit(-1,
                           elem_,
                           linear_flag=False,
                           )
        
        if xc is None:
            print(f"Warning: Edge fit failed for alignment. on_fit_error={on_fit_error}")
            if on_fit_error is not None:
                # User provided fallback - unpack and use
                xc, fwhm = on_fit_error
                print(f"Using fallback value: xc={xc}, fwhm={fwhm}")
                xc = xc + offset
            else:
                # No fallback provided - skip movement, return current position
                print(f"Skipping motor movement. Motor remains at {mtr.position}")
                return mtr.position
        else:
            print("xc", xc, "initial_position", initial_position, 
                  "align_movement_limit", align_movement_limit)
            if abs(xc) - abs(initial_position) > align_movement_limit:
                xc = mtr.position + offset
                print("xc", xc, "mtr.position", mtr.position, "offset", offset)
            else:
                xc = xc + offset
                print("xc", xc, "offset", offset)
         
    else:
        xc = mtr.position

    if move_coarse:
        coarse_stage = fly_to_coarse[mtr.name]
        print(f"move {coarse_stage.name} relative {xc}")
        yield from bps.movr(coarse_stage,xc)

    else:
        yield from bps.sleep(1)
        print(f"move {mtr.name} to {xc}")
        yield from bps.mov(mtr,xc)
    
    return xc


def tomo_2d_scan(angle,dets_,fly_motors,
                 x_start,x_end,x_num,
                 y_start,y_end,y_num,exp, 
                 tomo_use_panda = False, 
                 axis_switch_angle = 44.99,
                 scale_scan_range = False):
    
    '''
    fly_motors = [dssx,dssy,dssz]
    fly_motors = [zpssx,zpssy,zpssz]
    '''
    if abs(angle) < axis_switch_angle:

        if scale_scan_range:

            x_start_real = x_start / np.cos(angle * np.pi / 180.)
            x_end_real = x_end / np.cos(angle * np.pi / 180.)
            x_num_real = x_num


            if fly_motors[0].name == 'zpssx':
                x_scale_factor = 1
                x_start_real /= x_scale_factor
                x_end_real /= x_scale_factor
            
            print(x_start_real,x_end_real)

        else:

            x_num_real = round(x_num * np.cos(angle * np.pi / 180.))
            x_start_real = x_start
            x_end_real = x_end


        print("#"*30)
        print(f"{fly_motors[0].name = } @ {angle = :.2f}\n")
        print(f"{x_start_real = :.2f},{x_end_real = :.2f},{x_num_real = :.2f}")
        print("#"*30)  

        if not tomo_use_panda:
            yield from fly2d(dets_,
                            fly_motors[0],
                            x_start_real,
                            x_end_real,
                            x_num_real,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp
                            )
        else:
            yield from fly2dpd(dets_,
                            fly_motors[0],
                            x_start_real,
                            x_end_real,
                            x_num_real,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp,
                            position_supersample = 10
                            )

    else:

        if scale_scan_range:

            x_start_real = x_start / abs(np.sin(angle * np.pi / 180.))
            x_end_real = x_end / abs(np.sin(angle * np.pi / 180.))
            x_num_real = x_num
            if fly_motors[2].name == 'dssz':
                pass
                # print('WARNING!!: Applying temporary scaling correction ratio to dssz motor.')
                # x_start_real *= 0.955
                # x_end_real *= 0.955

            elif fly_motors[2].name == 'zpssz':
                

                # x_scale_factor = 0.9542
                # z_scale_factor = 1.0309

                
                z_scale_factor = 1
                x_start_real /= z_scale_factor
                x_end_real /= z_scale_factor

                x_num_real = x_num

                print(x_start_real,x_end_real)

        else:
            x_num_real = round(x_num * np.sin(angle * np.pi / 180.))
            x_start_real = x_start
            x_end_real = x_end
        
        
        print("#"*30)
        print(f"{fly_motors[2].name = } @ {angle = :2f}\n")
        print(f"{x_start_real = :.2f},{x_end_real = :.2f},{x_num_real = :.2f}")
        print("#"*30)  

        if not tomo_use_panda:
            yield from fly2d(dets_,
                            fly_motors[2],
                            x_start_real,
                            x_end_real,
                            x_num_real,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp
                            )
        else:
            yield from fly2dpd(dets_,
                            fly_motors[2],
                            x_start_real,
                            x_end_real,
                            x_num_real,
                            fly_motors[1],
                            y_start,
                            y_end,
                            y_num,
                            exp,
                            position_supersample = 10
                            )

def align_2d_com_scan(mtr1,x_s,x_e,x_n,mtr2,y_s,y_e,y_n,exp,elem_,
                      threshold,move_x=False,move_y=False, 
                      x_offset = 0, y_offset = 0,tomo_use_panda = True,
                      zero_before_scan = False
                      ):


    """
    @aaron removed 'angle' from first argument
    scan to align samples to field of view using using fly1d scan

    mtr1, mtr2--> scanning motor, dssx, dssy, dssz etc.
    xs,xe,xn,y_s,y_e,y_n,exp --> flyscan paramters
    elem_ --> element to use for alignemnt

    threshold --> threshold for center of mass
    move_x,move_y --> moves piezos to the com if true

    """
    #peform fly2d

    if zero_before_scan:
            yield from bps.mov(mtr1,0,wait=True)
            yield from bps.mov(mtr2,0,wait=True)



    if not tomo_use_panda:
        yield from fly2dpd([fs,xspress3],
                        mtr1,
                        x_s,
                        x_e,
                        x_n,
                        mtr2,
                        y_s,
                        y_e,
                        y_n,
                        exp)
    else:
        yield from fly2dpd([fs,xspress3],
                        mtr1,
                        x_s,
                        x_e,
                        x_n,
                        mtr2,
                         y_s,
                        y_e,
                        y_n,
                        exp)
            

    #find com
    cx,cy = return_center_of_mass(-1,
                                elem_,
                                threshold
                                )
    
    cx = cx + x_offset
    cy = cy + y_offset

    #move if true
    if move_x:
        yield from bps.mov(mtr1,cx)
    if move_y:
        yield from bps.mov(mtr2,cy)

def tomo_scan_to_loop(angle, 
                      tomo_params, 
                      ic_init, 
                      do_y_offset = True,
                      tracking_file = None, 
                      axis_swap_flag = False):

        #caput("XF:03IDC-ES{Merlin:2}HDF1:NDArrayPort","ROI1") #patch for merlin2 issuee

        #get parameters from json
        xalign = tomo_params["xalign"]
        yalign = tomo_params["yalign"]
        align_2d = tomo_params["align_2d_com"]
        image_scan = tomo_params["fly2d_scan"]
        dets = eval(image_scan["det"])
        elems_to_pdf = tomo_params["pdf_elems"]
        fly_motors= [eval(item) for item in tomo_params["fly_motors"]]
        axis_switch_angle = tomo_params["axis_switch_angle"]


        yield from bps.mov(eval(tomo_params["th_motor"]), angle)

        if do_y_offset:

            # precalculated y offset, mll only
            y_init = tomo_params["y_init"]
            th_init = tomo_params["th_init"]
            y_offset1 = sin_func(angle, 0.110, -0.586, 7.85,1.96)
            y_offset2 = sin_func(th_init, 0.110, -0.586, 7.85,1.96)
            yield from bps.mov(dssy,y_init+y_offset1-y_offset2)



        #yield from bps.mov(dssx,0,dssz,0)
        print(f'{tomo_params["flying_panda"] = }')
        #1d alignment sequence, based on angle x or z will be scanned
        if abs(angle) < axis_switch_angle:
            print(f'{fly_motors[0].name}scanning')
            if xalign["do_align"]:
                if axis_swap_flag and xalign["zero_before_scan"]:
                    yield from bps.mov(fly_motors[2],0,wait=True)
                yield from align_scan(fly_motors[0],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                tomo_params["flying_panda"],
                                xalign["zero_before_scan"],
                                xalign["initial_position"],
                                xalign["align_movement_limit"]
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:
                if axis_swap_flag and xalign["zero_before_scan"]:
                    yield from bps.mov(fly_motors[2],0,wait=True)
                x_start_real = align_2d["x_start"] / np.cos(angle * np.pi / 180.)
                x_end_real = align_2d["x_end"] / np.cos(angle * np.pi / 180.)


                yield from align_2d_com_scan(   fly_motors[0],
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                tomo_params["flying_panda"],
                                                align_2d["zero_before_scan"])

            else:
                pass

        else:
            print(f'{fly_motors[2].name}scanning')
            if xalign["do_align"]:
                if axis_swap_flag and xalign["zero_before_scan"]:
                    yield from bps.mov(fly_motors[0],0,wait=True)
                yield from align_scan(  fly_motors[2],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                tomo_params["flying_panda"],
                                xalign["zero_before_scan"],
                                xalign["initial_position"],
                                xalign["align_movement_limit"]
                                )

            #2d alignemnt using center of mass if condition is true
            elif align_2d["do_align"]:
                if axis_swap_flag and xalign["zero_before_scan"]:
                    yield from bps.mov(fly_motors[0],0,wait=True)
                x_start_real = align_2d["x_start"] / abs(np.sin(angle * np.pi / 180.))
                x_end_real = align_2d["x_end"] / abs(np.sin(angle * np.pi / 180.))

                yield from align_2d_com_scan(   fly_motors[2],
                                                x_start_real,
                                                x_end_real,
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                tomo_params["flying_panda"],
                                                align_2d["zero_before_scan"]
                                                )
            else:
                pass

        #1d y alignemnt scan
        if yalign["do_align"]:
            yield from align_scan(  fly_motors[1],
                                    yalign["start"],
                                    yalign["end"],
                                    yalign["num"],
                                    yalign["exposure"],
                                    yalign["elem"],
                                    yalign["center_with"],
                                    yalign["threshold"],
                                    yalign["move_coarse"],
                                    yalign["neg_flag"],
                                    yalign["offset"],
                                    tomo_params["flying_panda"],
                                    yalign["zero_before_scan"],
                                    yalign["initial_position"],
                                    yalign["align_movement_limit"]
                )

        else:
            pass

        #2d scan sequence, based on angle x or z are scanned
        yield from tomo_2d_scan(    angle,
                                    dets,
                                    fly_motors,
                                    image_scan["x_start"],
                                    image_scan["x_end"],
                                    image_scan["x_num"],
                                    image_scan["y_start"],
                                    image_scan["y_end"],
                                    image_scan["y_num"],
                                    image_scan["exposure"],
                                    tomo_params["flying_panda"],
                                    axis_switch_angle = tomo_params["axis_switch_angle"],
                                    scale_scan_range = tomo_params["scale_scan_range"]
                                    )

        #xspress3.unstage()

        #save images to pdf if
        if not tomo_params["stop_pdf"]:

            try:
                insert_xrf_map_to_pdf(-1,
                                      elements = elems_to_pdf,
                                      title_=['energy', tomo_params["th_motor"]],
                                      note = tomo_params["scan_label"])
                plt.close()

            except Exception as pdf_error:
                print(f"Warning: Failed to insert XRF map to PDF: {pdf_error}")
                print("Scan completed but PDF may not contain images. Check /nsls2/data/hxn/legacy/users/PDFCreator.log for details.")
        if tracking_file is not None:
            flog = open(tracking_file,'a')
            flog.write("%d %.3f\n"%(db[-1].start['scan_id'],angle))
            flog.close()

def run_tomo_json(path_to_json,tracking_file = None):


    """mll_tomo_scan by taking parameters from a json file,
    TODO add angles smartly

    """
    # Log plan start
    # Log plan start (graceful failure - won't block plan execution)
    try:
        PlanLogger.log_plan_start(
            plan_name="run_tomo_json",
            json_path=path_to_json,
            extra_params={"tracking_file": tracking_file}
        )
    except Exception as log_error:
        print(f"  Warning: Failed to log plan start: {log_error}")
    
    beamDumpOccured = False

    #open json file for angle info first
    with open(path_to_json,"r") as fp:
        tomo_params = json.load(fp)
    fp.close()
    print("json file loaded")

    #create angle list for iteration
    angle_info = tomo_params["angle_info"]
    print(angle_info)
    # angles = np.arange(angle_info["start"],
    #                     angle_info["end"]+angle_info["angle_step"],
    #                     angle_info["angle_step"]
    #                     )

    angles = np.linspace(angle_info["start"],
                        angle_info["end"],
                        int(1+abs(angle_info["end"] - angle_info["start"])/angle_info["angle_step"])
                        )
    if "split_tomo" in angle_info:
        split = int(angle_info["split_tomo"])
        angles0 = angles.copy()
        angles = angles0[0::split]
        for i in range(1,split):
            angles = np.concatenate((angles,angles0[i::split]))
    if "start_angle" in angle_info:
        angst = angle_info["start_angle"]
        for i,ang in enumerate(angles):
            if abs(ang-angst)<1e-3:
                angles = angles[i:]
                break

    angle_list = pd.DataFrame(columns= ['scan_id', 'angle'])

    angle_list["angle"] = angles

    print(angle_list)


    yield from bps.sleep(2)
    fly_motors= [eval(item) for item in tomo_params["fly_motors"]]
    th_motor = eval(tomo_params["th_motor"])
    
    
    #get some initial parameters
    ic_0 = sclr2_ch2.get()
    th_init = th_motor.position
    y_init = fly_motors[1].position
    do_y_offset = tomo_params["do_y_offset"]
    tomo_params["th_init"] = th_init
    tomo_params["y_init"] = y_init
    

    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    yield from bps.sleep(2)

    logger.info("Reading IC3 value")

    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates

     #Ic values are useful for calibration

         #add real energy to the dataframe
    angle_list['energy_rbv'] = np.nan
    #add scan_id to the dataframe
    angle_list['scan_id'] = np.nan
    #record time
    angle_list['TimeStamp'] = pd.Timestamp.now()
    #record if peak beam happed before the scan
    angle_list['Peak Flux'] = False
    angle_list['IC3'] = float(ic_3_init)
    angle_list['IC0'] = float(ic_0)
    angle_list[fly_motors[1].name] = np.nan
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)


    #set the pause and stop inter keys to False before the loop
    #to reverse the abort scan and pause when using the gui
    tomo_params["stop_iter"] = False
    tomo_params["pause_scan"] = False

    with open(path_to_json,"w") as fp:
            json.dump(tomo_params,fp, indent=6)

    fp.close()
    
    fluxPeaked = False

    

    #loop with list of angles
    angle_bef = angles[0]
    axis_swap_flag = False
    first_sid = int(caget('XF:03IDC-ES{Status}ScanID-I') + 1)
    for n,angle in enumerate(tqdm.tqdm(angles,desc = 'Tomo Scan')):
        yield from bps.sleep(1)

        #open the json file to catch any updates
        with open(path_to_json,"r") as fp:
            tomo_params = json.load(fp)
            fp.close()

        #stop data collection if necessary.user input taken
        if tomo_params["stop_iter"]:
            save_page()
            break

        while tomo_params["pause_scan"]:
            yield from bps.sleep(10) #check if this freezes the gui or not
            with open(path_to_json,"r") as fp:
                tomo_params = json.load(fp)
                fp.close()

            if not tomo_params["pause_scan"]:
                break

        if tomo_params["remove_angles"]==None:
            tomo_params["remove_angles"] = []

        if not tomo_params["test"]:
            if sclr2_ch2.get()<1000:
                beamDumpOccured = True
                yield from check_for_beam_dump()


            if beamDumpOccured:
                angle = angles[n-1]
                yield from bps.sleep(60)
                yield from recover_from_beamdump()
                beamDumpOccured = False

        #look for beam dump and ic3 threshold, ignores for code tests using json
        if not tomo_params["test"]:
            #opening fast shutter for initial ic3 reading
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
            yield from bps.sleep(2)
            if (sclr2_ch4.get() < (tomo_params["ic_threshold"]*ic_3_init)):
                 yield from peak_the_flux()
                 ic_0 = sclr2_ch2.get()
                 fluxPeaked = True

        if not angle in np.array(tomo_params["remove_angles"]):
            # flag when the scan axis changes (tomo_scan_to_loop picks the axis by abs(angle))
            switch_angle = tomo_params['axis_switch_angle']
            axis_swap_flag = (abs(angle_bef) < switch_angle) != (abs(angle) < switch_angle)
            if axis_swap_flag:
                print("axis swap flagged")
            angle_bef = angle

            #tomo scan at a single angle
            yield from tomo_scan_to_loop(angle,tomo_params,ic_0,
                                         do_y_offset = do_y_offset,
                                         tracking_file = tracking_file, 
                                         axis_swap_flag=axis_swap_flag,
                                         )

            last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
            print(last_sid)

            # Add more info to the dataframe
            angle_list.at[n, 'energy_rbv'] = e.position #add real energy to the dataframe
            angle_rbv = th_motor.position
            angle_list.at[n, "angle"] = angle_rbv
            angle_list.at[n, 'scan_id'] = int(last_sid) #add scan_id to the dataframe
            angle_list.at[n, 'TimeStamp'] = pd.Timestamp.now()
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            angle_list.at[n, 'IC3'] = ic_3 #Ic values are useful for calibration
            angle_list.at[n, 'IC0'] = ic_0 #Ic values are useful for calibration
            angle_list.at[n, 'Peak Flux'] = fluxPeaked # record if peakflux was excecuted
            #angle_list.at[n, 'IC3_before_peak'] = ic3 #ic3 right after e change, no peaking
            fluxPeaked = False #reset
            print("name", fly_motors[1].name, "n", n, "position", fly_motors[1].position)
            angle_list.at[n, fly_motors[1].name] = fly_motors[1].position
            
            #close c shutter
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

            # save the DF in the loop so quitting a scan won't affect
            filename = f"{tomo_params.get('scan_label','')}_startID{first_sid}"
            angle_list.to_csv(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename+'.csv'),
                              float_format= '%.5f')
            
            flog = open(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename+'.txt'),'a')
            flog.write("%d %.3f\n"%(int(last_sid),angle_rbv))
            flog.close()
            
        else:
            #close c shutter opened for the ic3 reading
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
            print(f"{angle} skipped")


    #TODO add angles to scan; need to be better
    #sort based on what current angle is
    if not tomo_params["add_angles"]==None:

        added_angles = tomo_params["add_angles"]

        for nn,angle in enumerate(tqdm.tqdm(added_angles,desc = 'Tomo Scan; Additional Angles')):

            #open the json file to catch any updates
            with open(path_to_json,"r") as fp:
                tomo_params = json.load(fp)
                fp.close()

            #stop data collection if necessary.user input taken
            if tomo_params["stop_iter"]:
                save_page()
                break

            while tomo_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_json,"r") as fp:
                    tomo_params = json.load(fp)
                    fp.close()

                if not tomo_params["pause_scan"]:
                    break

            if tomo_params["remove_angles"]==None:
                tomo_params["remove_angles"] = []

            # skip removed angles before any beam checks or shutter changes
            if angle in np.array(tomo_params["remove_angles"]):
                print(f"{angle} skipped")
                continue

            #look for beam dump and ic3 threshold, ignores for code tests using json
            if not tomo_params["test"]:
                if sclr2_ch2.get()<1000:
                    yield from check_for_beam_dump()
                    yield from bps.sleep(60)
                    yield from recover_from_beamdump()

                #opening fast shutter for initial ic3 reading
                caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
                yield from bps.sleep(2)
                if (sclr2_ch4.get() < (tomo_params["ic_threshold"]*ic_3_init)):
                    yield from peak_the_flux()
                    ic_0 = sclr2_ch2.get()
                    fluxPeaked = True

            # angle_bef is the last scanned angle, carried over from the main loop
            switch_angle = tomo_params['axis_switch_angle']
            axis_swap_flag = (abs(angle_bef) < switch_angle) != (abs(angle) < switch_angle)
            if axis_swap_flag:
                print("axis swap flagged")
            angle_bef = angle

            yield from tomo_scan_to_loop(angle, 
                                         tomo_params,ic_0,
                                         do_y_offset = do_y_offset,
                                         tracking_file = tracking_file,
                                         axis_swap_flag = axis_swap_flag)

            last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

            angle_rbv = th_motor.position
            ic_3 = sclr2_ch4.get()
            ic_0 = sclr2_ch2.get()
            print("name", fly_motors[1].name, "position", fly_motors[1].position)

            # append one complete row after the main-loop rows
            new_row = {'energy_rbv': e.position,
                       'angle': angle_rbv,
                       'scan_id': int(last_sid),
                       'TimeStamp': pd.Timestamp.now(),
                       'IC3': float(ic_3),
                       'IC0': float(ic_0),
                       'Peak Flux': fluxPeaked,
                       fly_motors[1].name: fly_motors[1].position}
            angle_list = pd.concat([angle_list, pd.DataFrame([new_row])], ignore_index=True)
            fluxPeaked = False #reset

            #close c shutter
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

            # save the DF in the loop so quitting a scan won't affect
            filename = f"{tomo_params.get('scan_label','')}_startID{first_sid}"
            angle_list.to_csv(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename+'.csv'),
                            float_format= '%.5f')
            flog = open(os.path.join(tomo_params.get("save_log_to", "/data/users/current_user"), filename+'.txt'),'a')
            flog.write("%d %.3f\n"%(int(last_sid),angle_rbv))
            flog.close()
                



    else:
        pass

    #save pdf
    save_page()
    
    # Log plan completion (graceful failure - won't block plan execution)
    try:
        PlanLogger.log_plan_end(
            plan_name="run_tomo_json",
            status="completed",
            extra_data={"total_angles": len(angles)}
        )
    except Exception as log_error:
        print(f"  Warning: Failed to log plan completion: {log_error}")

###################Diffraction######################

def make_diff_plan(save_as = "/nsls2/data/hxn/legacy/user_macros/HXN_GUI/Scan/temp_files/diff_params.json" ):

    diff_scan =     {"flying_panda":False,
                     "fly_motors":["dssx", "dssy"],
                     "th_motor":"dsth",
                    "angle_info":{"start":70,
                                "end":71,
                                "angle_step":0.025,
                                "custom_angle_list":[]},

                    "fly2d_scan":{'det':'dets4',
                                "x_start":-1,
                                "x_end":1,
                                "x_num":100,
                                "y_start":-1,
                                "y_end":1,
                                "y_num":100,
                                "exposure":0.03},

                    "xalign": {
                        "do_align": True,
                        "start": -10,
                        "end": 10,
                        "num": 300,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5,
                        "line_center_mode": "as-is"
                    },
                    "yalign": {
                        "do_align": True,
                        "start": -4,
                        "end": 4,
                        "num": 200,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "center_with": "line_center",
                        "threshold": 0.1,
                        "move_coarse": False,
                        "neg_flag": False,
                        "offset": 0,
                        "zero_before_scan": False,
                        "initial_position": 0,
                        "align_movement_limit": 1.5,
                        "line_center_mode": "as-is"
                    },
                    "align_2d_com": {
                        "do_align": False,
                        "x_start": -5,
                        "x_end": 5,
                        "x_num": 50,
                        "y_start": -2,
                        "y_end": 2,
                        "y_num": 20,
                        "exposure": 0.005,
                        "elem": "Au_L",
                        "threshold": 0.5,
                        "move_x": True,
                        "move_y": True,
                        "x_offset": -0.95,
                        "y_offset": -0.2,
                        "zero_before_scan": False
                    },

                    "stop_iter":False,
                    "add_angles":[ ],
                    "remove_angles":[-90,-91],
                    "stop_pdf":False,
                    "pdf_elems":["Au_L", "Pt_L"],
                    "pause_scan":False,
                    "test":False,
                    "ic_threshold":0.9,
                    "scan_label":"HXN_Tomo_Scan",
                    "Notes": 'My sample # 10'
                }

    with open(save_as,"w") as fp:
            json.dump(diff_scan,fp, indent=6)

    fp.close()


def diff_2d_scan(angle,dets_,fly_motors,x_start,x_end,x_num,y_start,y_end,y_num,exp, 
                     diff_use_panda = False):
    
    '''
    fly_motors = [dssx,dssy,dssz]
    fly_motors = [zpssx,zpssy,zpssz]
    '''



    if not diff_use_panda:
        yield from fly2d(dets_,
                        fly_motors[0],
                        x_start,
                        x_end,
                        x_num,
                        fly_motors[1],
                        y_start,
                        y_end,
                        y_num,
                        exp
                        )
    else:
        yield from fly2dpd(dets_,
                        fly_motors[0],
                        x_start,
                        x_end,
                        x_num,
                        fly_motors[1],
                        y_start,
                        y_end,
                        y_num,
                        exp,
                        position_supersample = 10
                        )

def diff_scan_to_loop(angle, diff_params, ic_init,tracking_file = None):

        #caput("XF:03IDC-ES{Merlin:2}HDF1:NDArrayPort","ROI1") #patch for merlin2 issuee

        #get parameters from json
        xalign = diff_params["xalign"]
        yalign = diff_params["yalign"]
        align_2d = diff_params["align_2d_com"]
        image_scan = diff_params["fly2d_scan"]
        dets = eval(image_scan["det"])
        elems_to_pdf = diff_params["pdf_elems"]
        fly_motors= [eval(item) for item in diff_params["fly_motors"]]


        # yield from bps.mov(eval(diff_params["th_motor"]), angle)

        # #yield from bps.mov(dssx,0,dssz,0)
        # print(f'{diff_params["flying_panda"] = }')
        # #1d alignment sequence, based on angle x or z will be scanned
        

        # if xalign["do_align"]:
        #     yield from align_scan(fly_motors[0],
        #                     xalign["start"],
        #                     xalign["end"],
        #                     xalign["num"],
        #                     xalign["exposure"],
        #                     xalign["elem"],
        #                     xalign["center_with"],
        #                     xalign["threshold"],
        #                     xalign["move_coarse"],
        #                     xalign["neg_flag"],
        #                     xalign["offset"],
        #                     diff_params["flying_panda"],
        #                     xalign["zero_before_scan"],
        #                     xalign["initial_position"],
        #                     xalign["align_movement_limit"]
        #                     )

        #     #2d alignemnt using center of mass if condition is true
        # if align_2d["do_align"]:

        #     yield from align_2d_com_scan(   fly_motors[0],
        #                                     align_2d["x_start"],
        #                                     align_2d["x_end"],
        #                                     align_2d["x_num"],
        #                                     fly_motors[1],
        #                                     align_2d["y_start"],
        #                                     align_2d["y_end"],
        #                                     align_2d["y_num"],
        #                                     align_2d["exposure"],
        #                                     align_2d["elem"],
        #                                     align_2d["threshold"],
        #                                     align_2d["move_x"],
        #                                     align_2d["move_y"],
        #                                     align_2d["x_offset"],
        #                                     align_2d["y_offset"],
        #                                     diff_params["flying_panda"])

        # #1d y alignemnt scan
        # if yalign["do_align"]:
        #     yield from align_scan(  fly_motors[1],
        #                             yalign["start"],
        #                             yalign["end"],
        #                             yalign["num"],
        #                             yalign["exposure"],
        #                             yalign["elem"],
        #                             yalign["center_with"],
        #                             yalign["threshold"],
        #                             yalign["move_coarse"],
        #                             yalign["neg_flag"],
        #                             yalign["offset"],
        #                             diff_params["flying_panda"],
        #                             yalign["zero_before_scan"],
        #                             yalign["initial_position"],
        #                             yalign["align_movement_limit"]
        #         )

            
        #     insert_xrf_map_to_pdf(-1,
        #                             elements = elems_to_pdf,
        #                             title_=['energy', diff_params["th_motor"]],
        #                             note = diff_params["scan_label"])
        #     plt.close()


        
        # else:
        #     pass

        #2d scan sequence, based on angle x or z are scanned
        yield from diff_2d_scan(    angle,
                                    dets,
                                    fly_motors,
                                    image_scan["x_start"],
                                    image_scan["x_end"],
                                    image_scan["x_num"],
                                    image_scan["y_start"],
                                    image_scan["y_end"],
                                    image_scan["y_num"],
                                    image_scan["exposure"],
                                    diff_params["flying_panda"]
                                    )

        #save images to pdf if
        if not diff_params["stop_pdf"]:

            try:
                insert_xrf_map_to_pdf(-1,
                                      elements = elems_to_pdf,
                                      title_=['energy', diff_params["th_motor"]],
                                      note = diff_params["scan_label"])
                plt.close()

            except Exception as pdf_error:
                print(f"Warning: Failed to insert XRF map to PDF: {pdf_error}")
                print("Scan completed but PDF may not contain images. Check /nsls2/data/hxn/legacy/users/PDFCreator.log for details.")
        if tracking_file is not None:
            flog = open(tracking_file,'a')
            flog.write("%d %.3f\n"%(db[-1].start['scan_id'],angle))
            flog.close()


def run_diff_json(path_to_json,tracking_file = None,do_confirm =True):


    """diff_scan by taking parameters from a json file,
    TODO add angles smartly

    """
    # Log plan start (graceful failure - won't block plan execution)
    try:
        PlanLogger.log_plan_start(
            plan_name="run_diff_json",
            json_path=path_to_json,
            extra_params={"tracking_file": tracking_file, "do_confirm": do_confirm}
        )
    except Exception as log_error:
        print(f"  Warning: Failed to log plan start: {log_error}")
    
    beamDumpOccured = False

    #open json file for angle info first
    with open(path_to_json,"r") as fp:
        diff_params = json.load(fp)
    fp.close()
    print("json file loaded")

    

    #create angle list for iteration
    angle_info = diff_params["angle_info"]
    print(angle_info)

    # A non-empty custom_angle_list (in angle_info or top level) takes priority
    # over generating angles from start/end/angle_step
    custom_angles = angle_info.get("custom_angle_list") or diff_params.get("custom_angle_list")

    if custom_angles:
        angles = np.array(custom_angles, dtype=float)
        print(f"Using custom angle list: {angles = }")
    else:
        angles = np.arange(angle_info["start"],
                             angle_info["end"]+(angle_info["angle_step"]/2),
                             angle_info["angle_step"]
                             )

        print(f"{angles = }")

        #angles = np.linspace(angle_info["start"],
        #                   angle_info["end"],
        #                    int(1+abs(angle_info["end"] - angle_info["start"])/angle_info["angle_step"])
        #                   )
        if "split_diff" in angle_info:
            split = int(angle_info["split_diff"])
            angles0 = angles.copy()
            angles = angles0[0::split]
            for i in range(1,split):
                angles = np.concatenate((angles,angles0[i::split]))
        if "start_angle" in angle_info:
            angst = angle_info["start_angle"]
            for i,ang in enumerate(angles):
                if abs(ang-angst)<1e-3:
                    angles = angles[i:]
                    break

    angle_list = pd.DataFrame(columns= ['scan_id', 'angle'])

    angle_list["angle"] = angles

    print(angle_list)


    yield from bps.sleep(2)
    fly_motors= [eval(item) for item in diff_params["fly_motors"]]
    th_motor = eval(diff_params["th_motor"])
    
    
    #get some initial parameters
    ic_0 = sclr2_ch2.get()

    #opening fast shutter for initial ic3 reading
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    yield from bps.sleep(2)

    logger.info("Reading IC3 value")

    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
    #open the json file to catch any updates

     #Ic values are useful for calibration

         #add real energy to the dataframe
    angle_list['energy_rbv'] = np.nan
    #add scan_id to the dataframe
    angle_list['scan_id'] = np.nan
    #record time
    angle_list['TimeStamp'] = pd.Timestamp.now()
    #record if peak beam happed before the scan
    angle_list['Peak Flux'] = False
    angle_list['IC3'] = float(ic_3_init)
    angle_list['IC0'] = float(ic_0)
    angle_list[fly_motors[1].name] = np.nan
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)


    #set the pause and stop inter keys to False before the loop
    #to reverse the abort scan and pause when using the gui
    diff_params["stop_iter"] = False
    diff_params["pause_scan"] = False

    with open(path_to_json,"w") as fp:
            json.dump(diff_params,fp, indent=6)

    fp.close()
    
    fluxPeaked = False
    image_scan_i = diff_params["fly2d_scan"]

    tot_time_ = (image_scan_i["x_num"]*image_scan_i["y_num"]*image_scan_i["exposure"]*len(angle_list))
    tot_time = tot_time_/3600
    overhead = 1.2
    end_datetime = time.ctime(time.time()+tot_time_*overhead)
    print("add angles of ", diff_params["add_angles"])
    print("remove angles of ", diff_params["remove_angles"])
    
    if do_confirm:
        check = 'n'
        check = input(f"This plan takes about {tot_time*overhead :.1f} hours,"
                    f"Projected to {end_datetime} continue (y/n)?")
    else:
        check = 'y'
    
    if check == "y":

        #loop with list of angles
        for n,angle in enumerate(tqdm.tqdm(angles,desc = 'diff Scan')):
            print(f"{angle = }")
            yield from bps.sleep(1)

            #open the json file to catch any updates
            with open(path_to_json,"r") as fp:
                diff_params = json.load(fp)
                fp.close()

            #stop data collection if necessary.user input taken
            if diff_params["stop_iter"]:
                save_page()
                break

            #get parameters from json
            xalign = diff_params["xalign"]
            yalign = diff_params["yalign"]
            align_2d = diff_params["align_2d_com"]
            image_scan = diff_params["fly2d_scan"]
            dets = eval(image_scan["det"])
            elems_to_pdf = diff_params["pdf_elems"]
            fly_motors= [eval(item) for item in diff_params["fly_motors"]]


            yield from bps.mov(eval(diff_params["th_motor"]), angle)

            #yield from bps.mov(dssx,0,dssz,0)
            print(f'{diff_params["flying_panda"] = }')
            #1d alignment sequence, based on angle x or z will be scanned
            

            if xalign["do_align"]:
                yield from align_scan(fly_motors[0],
                                xalign["start"],
                                xalign["end"],
                                xalign["num"],
                                xalign["exposure"],
                                xalign["elem"],
                                xalign["center_with"],
                                xalign["threshold"],
                                xalign["move_coarse"],
                                xalign["neg_flag"],
                                xalign["offset"],
                                diff_params["flying_panda"],
                                xalign["zero_before_scan"],
                                xalign["initial_position"],
                                xalign["align_movement_limit"],
                                line_center_mode=xalign.get(
                                    "line_center_mode",
                                    diff_params.get("line_center_mode", "as-is"))
                                )

                #2d alignemnt using center of mass if condition is true
            if align_2d["do_align"]:

                yield from align_2d_com_scan(   fly_motors[0],
                                                align_2d["x_start"],
                                                align_2d["x_end"],
                                                align_2d["x_num"],
                                                fly_motors[1],
                                                align_2d["y_start"],
                                                align_2d["y_end"],
                                                align_2d["y_num"],
                                                align_2d["exposure"],
                                                align_2d["elem"],
                                                align_2d["threshold"],
                                                align_2d["move_x"],
                                                align_2d["move_y"],
                                                align_2d["x_offset"],
                                                align_2d["y_offset"],
                                                diff_params["flying_panda"])

            #1d y alignemnt scan
            if yalign["do_align"]:
                yield from align_scan(  fly_motors[1],
                                        yalign["start"],
                                        yalign["end"],
                                        yalign["num"],
                                        yalign["exposure"],
                                        yalign["elem"],
                                        yalign["center_with"],
                                        yalign["threshold"],
                                        yalign["move_coarse"],
                                        yalign["neg_flag"],
                                        yalign["offset"],
                                        diff_params["flying_panda"],
                                        yalign["zero_before_scan"],
                                        yalign["initial_position"],
                                        yalign["align_movement_limit"],
                                        line_center_mode=yalign.get(
                                            "line_center_mode",
                                            diff_params.get("line_center_mode", "as-is"))
                    )

                
                # insert_xrf_map_to_pdf(-1,
                #                         elements = elems_to_pdf,
                #                         title_=['energy', diff_params["th_motor"]],
                #                         note = diff_params["scan_label"])
                plt.close()


            
            else:
                pass


            yield from bps.sleep(5)
            while diff_params["pause_scan"]:
                yield from bps.sleep(10) #check if this freezes the gui or not
                with open(path_to_json,"r") as fp:
                    diff_params = json.load(fp)
                    fp.close()

                if not diff_params["pause_scan"]:
                    break

            if diff_params["remove_angles"]==None:
                diff_params["remove_angles"] = []

            if not diff_params["test"]:
                if sclr2_ch2.get()<1000:
                    beamDumpOccured = True
                    yield from check_for_beam_dump()


                if beamDumpOccured:
                    angle = angles[n-1]
                    yield from bps.sleep(60)
                    yield from recover_from_beamdump()
                    beamDumpOccured = False

            #look for beam dump and ic3 threshold, ignores for code tests using json
            if not diff_params["test"]:
                #opening fast shutter for initial ic3 reading
                caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
                yield from bps.sleep(2)
                if (sclr2_ch4.get() < (diff_params["ic_threshold"]*ic_3_init)):
                    yield from peak_the_flux()
                    ic_0 = sclr2_ch2.get()
                    fluxPeaked = True
            
            if not angle in np.array(diff_params["remove_angles"]):
                #diff scan at a single angle
                yield from diff_scan_to_loop(angle,diff_params,ic_0,tracking_file = tracking_file)

                last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

                angle_list.at[n, "energy_rbv"] = e.position
                angle_list.at[n, "angle"] = th_motor.position
                angle_list.at[n, "scan_id"] = int(last_sid)
                angle_list.at[n, "TimeStamp"] = pd.Timestamp.now()

                ic_3 = sclr2_ch4.get()
                ic_0 = sclr2_ch2.get()

                angle_list.at[n, "IC3"] = ic_3
                angle_list.at[n, "IC0"] = ic_0
                angle_list.at[n, "Peak Flux"] = fluxPeaked
                angle_list.at[n, fly_motors[1].name] = fly_motors[1].position
                fluxPeaked = False

                logger.info("Recorded scan_id=%s at row=%s", last_sid, n)

                
                #close c shutter
                caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)

                scan_id_val = angle_list['scan_id'].iloc[0]
                scan_id_str = str(int(scan_id_val)) if not pd.isna(scan_id_val) else "unknown"
                filename = f"{diff_params.get('scan_label','')}_startID{scan_id_str}.csv"
                angle_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                float_format= '%.5f')
            else:
                print(f"{angle} skipped")
                pass


        #TODO add angles to scan; need to be better
        #sort based on what current angle is
        if not diff_params["add_angles"]==None:

            added_angles = diff_params["add_angles"]

            for nn,angle in enumerate(tqdm.tqdm(added_angles,desc = 'diff Scan; Additional Angles')):

                #open the json file to catch any updates
                with open(path_to_json,"r") as fp:
                    diff_params = json.load(fp)
                    fp.close()

                #stop data collection if necessary.user input taken
                if diff_params["stop_iter"]:
                    save_page()
                    break

                while diff_params["pause_scan"]:
                    yield from bps.sleep(10) #check if this freezes the gui or not
                    with open(path_to_json,"r") as fp:
                        diff_params = json.load(fp)
                        fp.close()

                    if not diff_params["pause_scan"]:
                        break

                if not angle in np.array(diff_params["remove_angles"]):
                    yield from diff_scan_to_loop(angle, diff_params,ic_0,tracking_file = tracking_file)

                    last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))

                    ic_3 = sclr2_ch4.get()
                    ic_0 = sclr2_ch2.get()

                    # append one complete row after the main-loop rows
                    new_row = {'energy_rbv': e.position,
                               'angle': th_motor.position,
                               'scan_id': int(last_sid),
                               'TimeStamp': pd.Timestamp.now(),
                               'IC3': float(ic_3),
                               'IC0': float(ic_0),
                               'Peak Flux': fluxPeaked,
                               fly_motors[1].name: fly_motors[1].position}
                    angle_list = pd.concat([angle_list, pd.DataFrame([new_row])], ignore_index=True)
                    fluxPeaked = False #reset

                    # save the DF in the loop so quitting a scan won't affect
                    filename = f"hxn_zp_diff_{diff_params.get('scan_label','')}_startID{int(angle_list['scan_id'][0])}.csv"
                    angle_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                                    float_format= '%.5f')

                else:
                    print(f"{angle} skipped")
                    pass

        else:
            pass

        #go back to the initial angle    
        yield from bps.mov(eval(diff_params["th_motor"]), angles[0])

        #save pdf
        save_page()
        
        # Log plan completion (graceful failure - won't block plan execution)
        try:
            PlanLogger.log_plan_end(
                plan_name="run_diff_json",
                status="completed",
                extra_data={"total_angles": len(angles)}
            )
        except Exception as log_error:
            print(f" Warning: Failed to log plan completion: {log_error}")




def run_repeat_2d_json(path_to_json, n_repeat=10, tracking_file=None, do_confirm=True):
    """
    Perform repeated diffraction scans (n_repeat times) at a single angle using
    parameters from a JSON file, including x/y/2D alignment scans before each run.

    Example:
        RE(run_diff_json_repeat('/path/to/diff_params.json', n_repeat=10))
    """
    # Log plan start (graceful failure - won't block plan execution)
    try:
        PlanLogger.log_plan_start(
            plan_name="run_repeat_2d_json",
            json_path=path_to_json,
            extra_params={"n_repeat": n_repeat, "tracking_file": tracking_file, "do_confirm": do_confirm}
        )
    except Exception as log_error:
        print(f"  Warning: Failed to log plan start: {log_error}")
    
    beamDumpOccured = False
    fluxPeaked = False

    # Load JSON
    with open(path_to_json, "r") as fp:
        diff_params = json.load(fp)
    print("json file loaded")

    # Motors and detectors
    fly_motors = [eval(item) for item in diff_params["fly_motors"]]
    th_motor = eval(diff_params["th_motor"])

    # Determine scan angle
    if "angle_info" in diff_params and "start" in diff_params["angle_info"]:
        scan_angle = diff_params["angle_info"]["start"]
    else:
        scan_angle = th_motor.position

    # Initial IC readings
    ic_0 = sclr2_ch2.get()
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 1)
    yield from bps.sleep(2)
    ic_3_init = sclr2_ch4.get()
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 0)

    # Create DataFrame
    repeat_list = pd.DataFrame(columns=['scan_id', 'iteration', 'energy_rbv', 'IC3', 'IC0',
                                        'Peak Flux', 'TimeStamp', fly_motors[1].name])
    repeat_list['iteration'] = np.arange(1, n_repeat + 1)

    # Estimate time
    image_scan_i = diff_params["fly2d_scan"]
    tot_time_ = (image_scan_i["x_num"] * image_scan_i["y_num"] *
                 image_scan_i["exposure"] * n_repeat)
    tot_time = tot_time_ / 3600
    overhead = 1.2
    end_datetime = time.ctime(time.time() + tot_time_ * overhead)

    if do_confirm:
        check = input(f"This plan will take about {tot_time*overhead:.1f} hours, "
                      f"projected to finish {end_datetime}. Continue (y/n)? ")
    else:
        check = 'y'

    if check.lower() != 'y':
        print("Scan aborted by user.")
        return

    print(f"Running {n_repeat} repeated scans at angle = {scan_angle:.3f}")

    # Set pause/stop flags
    diff_params["stop_iter"] = False
    diff_params["pause_scan"] = False
    with open(path_to_json, "w") as fp:
        json.dump(diff_params, fp, indent=6)

    for n in range(n_repeat):
        print(f"=== Scan {n+1}/{n_repeat} ===")

        # Re-read JSON in case user edited mid-scan
        with open(path_to_json, "r") as fp:
            diff_params = json.load(fp)

        # stop/pause logic
        if diff_params.get("stop_iter", False):
            save_page()
            print("Scan stopped by user.")
            break

        while diff_params.get("pause_scan", False):
            yield from bps.sleep(5)
            with open(path_to_json, "r") as fp:
                diff_params = json.load(fp)

        # Move to scan angle
        yield from bps.mov(th_motor, scan_angle)

        # --- Alignment Scans ---
        xalign = diff_params["xalign"]
        yalign = diff_params["yalign"]
        align_2d = diff_params["align_2d_com"]

        # X alignment
        if xalign["do_align"]:
            yield from align_scan(
                fly_motors[0],
                xalign["start"], xalign["end"], xalign["num"],
                xalign["exposure"], xalign["elem"], xalign["center_with"],
                xalign["threshold"], xalign["move_coarse"], xalign["neg_flag"],
                xalign["offset"], diff_params["flying_panda"],
                xalign["zero_before_scan"], xalign["initial_position"],
                xalign["align_movement_limit"]
            )

        # 2D alignment
        if align_2d["do_align"]:
            yield from align_2d_com_scan(
                fly_motors[0],
                align_2d["x_start"], align_2d["x_end"], align_2d["x_num"],
                fly_motors[1],
                align_2d["y_start"], align_2d["y_end"], align_2d["y_num"],
                align_2d["exposure"], align_2d["elem"], align_2d["threshold"],
                align_2d["move_x"], align_2d["move_y"],
                align_2d["x_offset"], align_2d["y_offset"],
                diff_params["flying_panda"]
            )

        # Y alignment
        if yalign["do_align"]:
            yield from align_scan(
                fly_motors[1],
                yalign["start"], yalign["end"], yalign["num"],
                yalign["exposure"], yalign["elem"], yalign["center_with"],
                yalign["threshold"], yalign["move_coarse"], yalign["neg_flag"],
                yalign["offset"], diff_params["flying_panda"],
                yalign["zero_before_scan"], yalign["initial_position"],
                yalign["align_movement_limit"]
            )

        yield from bps.sleep(2)

        # --- Beam Check and Flux Peaking ---
        if not diff_params["test"]:
            if sclr2_ch2.get() < 1000:
                beamDumpOccured = True
                yield from check_for_beam_dump()

            if beamDumpOccured:
                yield from bps.sleep(60)
                yield from recover_from_beamdump()
                beamDumpOccured = False

            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 1)
            yield from bps.sleep(2)
            if (sclr2_ch4.get() < (diff_params["ic_threshold"] * ic_3_init)):
                yield from peak_the_flux()
                ic_0 = sclr2_ch2.get()
                fluxPeaked = True
            caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0', 0)

        # --- Run Diffraction Scan ---
        yield from diff_scan_to_loop(scan_angle, diff_params, ic_0, tracking_file=tracking_file)

        # --- Record Results ---
        last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
        repeat_list.at[n, 'scan_id'] = last_sid
        repeat_list.at[n, 'energy_rbv'] = e.position
        repeat_list.at[n, 'IC3'] = sclr2_ch4.get()
        repeat_list.at[n, 'IC0'] = sclr2_ch2.get()
        repeat_list.at[n, 'Peak Flux'] = fluxPeaked
        repeat_list.at[n, 'TimeStamp'] = pd.Timestamp.now()
        repeat_list.at[n, fly_motors[1].name] = fly_motors[1].position
        fluxPeaked = False

        # Save after each repeat
        filename = f"{diff_params.get('scan_label','repeat_diff')}_n{n_repeat}_startID{int(repeat_list['scan_id'][0])}.csv"
        repeat_list.to_csv(os.path.join(diff_params.get("save_log_to", "/data/users/current_user"), filename),
                           float_format='%.5f')

        print(f"Repeat scan {n+1}/{n_repeat} done and logged.")

    # Final save
    save_page()
    print("All repeated scans completed successfully.")
    
    # Log plan completion (graceful failure - won't block plan execution)
    try:
        PlanLogger.log_plan_end(
            plan_name="run_repeat_2d_json",
            status="completed",
            extra_data={"repeats_completed": n_repeat}
        )
    except Exception as log_error:
        print(f" Warning: Failed to log plan completion: {log_error}")
