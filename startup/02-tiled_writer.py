if TILED_OFF:
    print(f"Tiled is disabled, skipping {__file__!r} ...")
    import sys
    sys.exit()

print(f"Loading {__file__!r} ...")

import copy

from bluesky.callbacks.tiled_writer import TiledWriter, RunNormalizer
from bluesky.callbacks.buffer import BufferingWrapper

from tiled.client import from_uri
import os
import logging

logger = logging.getLogger(__name__)

# Suppress size and datatype mismatch user warnings.
import warnings
warnings.filterwarnings("ignore",module="bluesky.callbacks.tiled_writer")

def patch_descriptor(doc):
    # Issue #1: data keys for 'scaler_alive', 'sclr1_ch2' .. 'sclr1_ch8' have incorrect "dtype": "array"  and "shape": [1].
    #   Replace the values with "dtype": "number" and "shape": []. Also set "dtype_str": "<i8" for "sclr1_ch.." to get rid of warnings.
    # Issue #2: Fix for incorrect shape and type of merlin1 data.
    DATA_KEY_PREFIXES = ["scaler_alive", "sclr1_ch"]
    for k in doc["data_keys"].keys():
        if k == "scaler_alive":
            doc["data_keys"][k]["dtype"] = "number"
            doc["data_keys"][k]["shape"] = []
        elif k.startswith("sclr"):
            doc["data_keys"][k]["dtype"] = "number"
            doc["data_keys"][k]["dtype_str"] = "<f4"
        elif k == "merlin1":
            doc["data_keys"][k]["dtype_str"] = "<u4"
            # doc["data_keys"][k]["shape"] = [1, 209, 203]     # The shape is inconsistent; need to validate
        elif k == "eiger1" or k == "eiger_mobile_image":
            # doc["data_keys"][k]["shape"] = [1, 409, 412]     # or [1, 394, 338]? in "TPX_HDF5" spec
            doc["data_keys"][k]["dtype_str"] = "<u2"           # Inconsistent? Need to validate
        elif k == "eiger2_image":
            doc["data_keys"][k]["dtype_str"] = "<u4"           # Could be "<u4" or "<u2"
        elif k.startswith("Det"):
            doc["data_keys"][k]["dtype_str"] = "<f4"

    return doc

def patch_datum(doc):
    if "datum_kwargs" in doc.keys():
        dataset = doc['datum_kwargs'].pop("det_elem", None) \
                or doc['datum_kwargs'].pop("column", None) \
                or doc['datum_kwargs'].pop("field", None)
        if dataset:
            doc["datum_kwargs"]["dataset"] = dataset
        
        if channel := doc["datum_kwargs"].get("channel", None):
            doc["datum_kwargs"]["slice"] = f"(:,{channel-1},:)"
            doc["datum_kwargs"]["squeeze"] = True
    return doc

def patch_resource(doc):
    if doc["resource_path"].startswith(doc["root"]):
        doc["resource_path"] = doc["resource_path"].replace(doc["root"], '')
    if doc["root"].startswith("/data"):
        doc["root"] = doc["root"].replace("/data", "/nsls2/data/hxn/legacy")
    # doc["root"] = re.sub(r"^/data", "/nsls2/data/hxn/legacy", doc["root"])
    doc["resource_path"] = doc["resource_path"].replace("nsls2/data2/hxn", "nsls2/data/hxn")
    
    # Replace 'frame_per_point' with 'multiplier'
    if frame_per_point := doc["resource_kwargs"].pop("frame_per_point", None):
        doc["resource_kwargs"]["multiplier"] = frame_per_point

    # Sey default chunk_shape to (1,)
    if "chunk_shape" not in doc["resource_kwargs"].keys():
        doc["resource_kwargs"]["chunk_shape"] = (1, )

    spec = doc["spec"]
    if spec in ["MERLIN_FLY_STREAM_V2", "TPX3", "TPX_HDF5", "EIGER2_STREAM", "MERLIN_HDF5_BULK"]:
        doc["resource_kwargs"].update({"dataset": '/entry/data/data', "chunk_shape": (1, ), "join_method": "concat"})
    elif spec == "PANDA":
        doc["resource_kwargs"].update({"chunk_shape": (1024, ), "join_method": "concat"})
    elif spec == "ROI_HDF5_FLY":
        doc["resource_kwargs"].update({"chunk_shape": (1024, ), "join_method": "concat"})
    elif spec in ["XSP"]:
        # NOTE: here data is accessed by "channel"
        doc["resource_kwargs"].update({"dataset": 'entry/instrument/detector/data', "chunk_shape": (1, ), "join_method": "concat"})
    elif spec == "XSP3_BULK":
        # NOTE: here data is accessed by "channel"
        # NOTE: "XSP3_BULK" does not declare the number of rows in the descriptor -- need to validate (see below)
        doc["resource_kwargs"].update({"dataset": 'entry/instrument/detector/data',
                                       "chunk_shape": (1, ),
                                       "join_method": "stack"})
    elif spec == "XSP3":
        # NOTE: here data is accessed by "channel" -- need to decide how to handle it in Tiled
        doc["resource_kwargs"].update({"dataset": 'entry/instrument/detector/data', "chunk_shape": (1, ), "join_method": "stack"})
    elif spec == "SIS_HDF51_FLY_STREAM_V1":
        # These correspond to 'sclr1_ch*' data_keys
        doc["resource_kwargs"].update({"chunk_shape": (1024, ), "join_method": "concat"})

    # Validate the structure if e.g. the datum shape is not declared in the descriptor
    # NOTE: Flyscannning specs often do not include the total number recorded points, only points per frame
    # NOTE: TPX_HDF5 has inconsistent shape definitions for eiger1 and merlin (stackable T/F)
    if spec in ["XSP3_BULK", "MERLIN_HDF5_BULK", "ROI_HDF5_FLY", "SIS_HDF51_FLY_STREAM_V1",
                "MERLIN_FLY_STREAM_V2", "PANDA"] + ["TPX_HDF5"]:
        doc["resource_kwargs"].update({"_validate": True,"locking": False})

    return doc

class RunNormalizerHXN(RunNormalizer):
    """
    This normalizer is used to fix xspress3 data where all Datum documents following the first Event has
    the same datum_id and datum_kwargs. This is a workaround for the issue and may not capture all edge cases.

    The Datum and Event documents are modified to include consecutive ids and rotating channel numbers
    in the `datum_kwargs`.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rebuild_stream = False   # Indicator of whether this is a faulty run that needs to be fixed
        self._resource_uid = None      # Resource UID for the xspress3 data
        self._descriptor_uid = None    # Descriptor UID for the xspress3 data
        self._channel_nums = []        # List of channel numbers for xspress3 data, e.g. [1, 2, 3]
        self._datum_counter = 0        # Counter for the datum documents, used to generate unique datum_id
        self._event_counter = 0        # Counter for the event documents, used to check the number of datums

    def start(self, doc):
        if (doc.get('scan_name') == 'NMC_1') and (doc.get('plan_name') == 'rel_scan') and ('xspress3' in doc.get('detectors',[])):
            self._rebuild_stream = True

        return super().start(doc)
    
    def descriptor(self, doc):
        if self._rebuild_stream and (doc["name"] == "primary"):
            self._descriptor_uid = doc["uid"]
            # Determine the channel numbers from the data keys, e.g. xspress3_ch1 --> int(1), 1-based index
            self._channel_nums = sorted([int(k[-1]) for k in doc['data_keys'].keys() if k.startswith('xspress3_ch')])

        return super().descriptor(doc)

    def resource(self, doc):
        if self._rebuild_stream and (doc["spec"] == "XSP3"):
            self._resource_uid = doc["uid"]

        return super().resource(doc)
    
    def event(self, doc):
        if self._rebuild_stream and (doc["descriptor"] == self._descriptor_uid):
            for ch in self._channel_nums:
                indx = (doc["seq_num"]-1) * len(self._channel_nums) + (ch - 1)
                doc["data"][f"xspress3_ch{ch}"] = f"{self._resource_uid}/{indx}"
                self._event_counter += 1

        return super().event(doc)
    
    def datum(self, doc):
        if self._rebuild_stream and (doc["resource"] == self._resource_uid):
            doc = copy.deepcopy(doc)
            doc["datum_id"] = f"{self._resource_uid}/{self._datum_counter}"
            doc["datum_kwargs"]["channel"] = self._datum_counter % len(self._channel_nums)
            doc["datum_kwargs"].pop("frame", None)  # Rely on seq_num from Event. May not always work!
            self._datum_counter += 1

        return super().datum(doc)
    
    def stop(self, doc):
        if self._rebuild_stream:
            doc = copy.deepcopy(doc)
            for indx in range(self._datum_counter, self._event_counter):
                # Some Events have no corresponding Datums, so we need to emit them
                datum_doc = {
                    "resource": self._resource_uid,
                    "datum_id": f"{self._resource_uid}/{indx}",
                    "datum_kwargs": {"channel": indx % len(self._channel_nums)},
                }
                super().datum(datum_doc)
            doc["note"] = doc.get("note", "") + "This run was modified to have unique datum_ids and channel numbers for xspress3 data."

        return super().stop(doc)


api_key = os.environ.get("TILED_BLUESKY_WRITING_API_KEY_HXN")
tiled_writing_client = from_uri("https://tiled.nsls2.bnl.gov", api_key=api_key)['hxn']['migration']
RE.md["tiled_access_tags"] = ["hxn_beamline"]

tw = TiledWriter(client = tiled_writing_client,
                 normalizer=RunNormalizerHXN,
                 backup_directory="/tmp/tiled_backup",
                 patches = {"descriptor": patch_descriptor,
                           "datum": patch_datum,
                           "resource": patch_resource})
tw = BufferingWrapper(tw)      # Thread-safe wrapper for TiledWriter

def cache_retriever(name, doc):
    """Replay all received datum documents from the cache when the scan finishes. Wraps TiledWriter."""
    if name in ("stop", "start"):
        # Clear the cache when the Stop document is received and at the start of a new run.
        # The latter is a safeguard to prevent the cache from overfilling; normally it should be empty.
        while True:
            if item := tiled_document_cache.popleft():
                tw(*item)    # item is a tuple (name, doc) or None
            else:
                break        # No more items in the cache, we are done
    # else:
    #     if item := tiled_document_cache.popleft():
    #         print(f"Document is {item}")
    #         tw(*item)     # While we're here, we can also process (one?) cached document -- this is debatable...
    tw(name, doc)

# Subscribe the cache_retriever + TW
RE.subscribe(cache_retriever)
