print(f"Loading {__file__!r} ...")

import numpy as np
import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

with open("/nsls2/data/hxn/shared/config/bluesky/profile_collection/startup/plot_elems.json", "r") as fp:
    xrf_elems = json.load(fp)
    fp.close()

roi_elems = xrf_elems["roi_elems"]
live_plot_elems  = xrf_elems["live_plot_elems"]
line_plot_elem = xrf_elems["line_plot_elem"]

update_elements = reload_bsui

'''
roi_elems = ['Cu','Ge','W_L','Ti','Si','Cl','Ga','S','Cr','Mn','Fe','Co','Ni','Zn','Pt_L','Au_L'] #limit = 16
live_plot_elems = roi_elems[:4] # no limts but has to be in the above roi_elems
#live_plot_elems = ['Cu','Ge','Ti','W_L'] # no limts but has to be in the above roi_elems
line_plot_elem = roi_elems[0] #only one element
'''

def create_user_dir(users_name):

    month = datetime.now().month
    year = datetime.now().year

    month_to_quarter = {1:"Q1",2:"Q1",3:"Q1",4:"Q1",
                        5:"Q2",6:"Q2",7:"Q2",8:"Q2",
                        9:"Q3",10:"Q3",11:"Q3",12:"Q3"}
    year_quarter = f"{year}{month_to_quarter[month]}"
    dir_name = f"/data/users/{year_quarter}/{users_name}_{year_quarter}"

    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        return dir_name
    else:
        print("user directory already exists")
        return dir_name

def create_user_symlink(src_dir = "/data/2023Q1/"):

    if os.path.exists(src_dir):
        
        dest = "/data/users/current_user"

        #recreate symlink
        if os.path.exists(dest):
            #os.rmdir(dest)
            os.unlink(dest)
        os.symlink(src_dir,dest)
        print(f"Successfully created a symlink for {src_dir} as {dest}")
        return

    else:
        raise FileExistsError (f"{src_dir} does not exist; Failed to create a symlink")



def setup_new_user(name = "Lastname",
                   experimenters = "HX,NU,SER",
                   sample = "Gold",
                   pdf_file_name = "elog",
                   sample_image = "/data/users/hxn_logo.png"):

    RE.md["PI"] = name
    RE.md["experimenters"] = experimenters
    RE.md["sample"] = sample
    RE.md["scan_name"] = sample+"_1"

    udir = create_user_dir(name)
    print(f"User directory is; {udir}")
    create_user_symlink(src_dir = udir)
    setup_pdf_function(sample_name = sample,
                       experimenters = experimenters,
                       img_to_add = sample_image,
                       file_name = pdf_file_name)

    return udir,pdf_file_name

def tic():
    return time.monotonic()

def toc(t0, str=''):
    dt = time.monotonic() - t0
    print('%s: dt = %f second' % (str, dt))

from bluesky_queueserver_api import BPlan
from bluesky_queueserver_api.zmq import REManagerAPI
RM = REManagerAPI()
# RM.item_execute((BPlan("fly2d", ["fs", "zebra", "sclr1", "merlin1", "xspress3"], "dssx", -1, 1, 10, "dssy", -1, 1, 10, 0.1)))
# RM.item_add((BPlan("fly2dpd", ["fs", "eiger2", "xspress3"], "dssx", -1, 1, 10, "dssy", -1, 1, 10, 0.3)))


#XF:03IDC-VA{VT:Chm-TCG:2}P-I




def get_cycle_from_date(date_obj):
    """
    Determine NSLS-II cycle (year-1/2/3) from the month of the given date.
    """
    year = date_obj.year
    month = date_obj.month

    if 1 <= month <= 4:
        cycle = f"{year}-1"
    elif 5 <= month <= 8:
        cycle = f"{year}-2"
    else:
        cycle = f"{year}-3"

    return cycle


def get_year_quarter_from_date(date_obj):
    """
    Convert month → <year><Q1/Q2/Q3> string for user directory naming.
    """
    month_to_quarter = {
        1: "Q1", 2: "Q1", 3: "Q1", 4: "Q1",
        5: "Q2", 6: "Q2", 7: "Q2", 8: "Q2",
        9: "Q3", 10: "Q3", 11: "Q3", 12: "Q3"
    }
    return f"{date_obj.year}{month_to_quarter[date_obj.month]}"


def create_user_dir_globus(users_name, date_obj = None):
    """
    Create or return the user directory under:
        /data/users/<year_quarter>/<username>_<year_quarter>
    """
    if not date_obj:
        date_obj = datetime.now()
    year_quarter = get_year_quarter_from_date(date_obj)
    dir_name = f"/data/users/{year_quarter}/{users_name}_{year_quarter}"

    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
        print(f" Created user directory: {dir_name}")
    else:
        print(f" User directory already exists: {dir_name}")

    return dir_name


def copy_user_data_for_globus(users_name, proposal_number, exp_month=None, dry_run=False):
    """
    Copy user data from /data/users/... to:
        /nsls2/data/hxn/proposals/<cycle>/pass-<proposal_number>/<username>_<cycle>/

    Parameters
    ----------
    users_name : str
        User's last name.
    proposal_number : str
        NSLS-II proposal number (e.g., '312345').
    exp_month : str or None
        Experimental month in 'YYYY-MM' (e.g., '2025-07'). Defaults to current month.
    dry_run : bool
        If True, performs a dry-run (no actual copy).

    Returns
    -------
    str or None
        Destination directory path if successful, else None.

    # Example 1: Copy current data
    copy_user_data("smith", "312345")

    # Example 2: Copy from a specific month
    copy_user_data("chen", "311234", exp_month="2024-11")

    # Example 3: Dry run
    copy_user_data("lee", "312345", exp_month="2025-07", dry_run=True)
    """
    # Determine reference date
    if exp_month:
        try:
            date_obj = datetime.strptime(exp_month, "%Y-%m")
        except ValueError:
            print(" Invalid month format. Use YYYY-MM.")
            return None
    else:
        date_obj = datetime.now()

    # Derive paths
    src_dir = create_user_dir_globus(users_name, date_obj)
    cycle = get_cycle_from_date(date_obj)

    base_dst_dir = f"/nsls2/data/hxn/proposals/{cycle}/pass-{proposal_number}"
    user_dst_dir = os.path.join(base_dst_dir, f"{users_name}_{cycle}")

    # Ensure proposal directory exists
    if not os.path.exists(base_dst_dir):
        print(f" Proposal directory not found:\n  {base_dst_dir}")
        print("Please verify the proposal number or cycle.")
        return None

    # Create user's subfolder if missing
    if not os.path.exists(user_dst_dir):
        try:
            os.makedirs(user_dst_dir, exist_ok=True)
            print(f" Created destination folder: {user_dst_dir}")
        except PermissionError:
            print(f" No permission to create folder: {user_dst_dir}")
            return None

    print(f"\n Copying data from:\n  {src_dir}\n→ to\n  {user_dst_dir}\n")

    # Build rsync command — SAFE: no deletion
    rsync_cmd = [
        "rsync",
        "-avh",
        "--progress",
        src_dir + "/",   # copy contents only
        user_dst_dir
    ]

    if dry_run:
        rsync_cmd.insert(1, "--dry-run")

    try:
        subprocess.run(rsync_cmd, check=True)
        print(" Data transfer complete.")
    except subprocess.CalledProcessError as e:
        print(f" Rsync failed: {e}")
        return None
    except FileNotFoundError:
        print(" 'rsync' not found. Please ensure it's installed.")
        return None

    return user_dst_dir


def copy_folder(
    src,
    dst,
    *,
    ignore_hidden=True,
    keep_hidden=None,
    ignore_dirs=None,
    ignore_exts=None,
    overwrite=False,
):
    from pathlib import Path
    import shutil

    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(src)

    if dst.exists():
        if overwrite:
            shutil.rmtree(dst)
        else:
            raise FileExistsError(dst)

    keep_hidden = set(keep_hidden or [])
    ignore_dirs = set(ignore_dirs or ["__pycache__"])
    ignore_exts = tuple(ignore_exts or [".pyc", ".pyo"])

    def ignore_func(_, contents):
        ignored = []
        for item in contents:
            if ignore_hidden and item.startswith(".") and item not in keep_hidden:
                ignored.append(item)
            elif item in ignore_dirs:
                ignored.append(item)
            elif item.endswith(ignore_exts):
                ignored.append(item)
        return ignored

    shutil.copytree(src, dst, ignore=ignore_func)

    return dst

def copy_diff_analysis():
    return copy_folder(
        "/nsls2/data/hxn/legacy/users/data_analysis/Nanodiffraction",
        "/nsls2/data/hxn/legacy/users/current_user/Nanodiffraction",
        overwrite=False,
        ignore_dirs=["__pycache__", "pycdc"],
        ignore_exts=[".pyc", ".pyo"],
    )