import sys
import cv2
import torch
from detectron2.config import get_cfg
from typing import ClassVar, Dict

from detectron2.checkpoint import DetectionCheckpointer
from detectron2.modeling import build_model

sys.path.append("../detectron2/projects/DensePose")
from densepose import add_densepose_config
from densepose.vis.extractor import create_extractor
from densepose.vis.densepose_results import DensePoseResultsFineSegmentationVisualizer


class ModelConfig:
    cfg = get_cfg()
    add_densepose_config(cfg)
    cfg.merge_from_file('../detectron2/projects/DensePose/configs/densepose_rcnn_R_50_FPN_s1x.yaml')
    cfg.MODEL.DEVICE = 'cuda'
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
    cfg.MODEL.WEIGHTS = 'checkpoints/model_final_289019.pkl'
    CONFIG = cfg
    vis = DensePoseResultsFineSegmentationVisualizer()
    EXTRACTOR = create_extractor(vis)

    DP_MODEL = build_model(cfg)
    DP_MODEL.eval()
    checkpointer = DetectionCheckpointer(DP_MODEL)
    checkpointer.load(cfg.MODEL.WEIGHTS)
