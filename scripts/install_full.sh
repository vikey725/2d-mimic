#!/usr/bin/env bash

CONDA_ENV_NAME=alsome
VIRT_CAM_ID=7
VIRT_CAM_NAME=Also-me

mkdir alsome
cd alsome
# check prerequisites
command -v conda >/dev/null 2>&1 || { echo >&2 "conda not found. Please refer to the README and install Miniconda."; exit 1; }
command -v git >/dev/null 2>&1 || { echo >&2 "git not found. Please refer to the README and install Git."; exit 1; }

git clone https://github.com/alievk/v4l2loopback.git
echo "--- Installing v4l2loopback (sudo privelege required)"
cd v4l2loopback
make && sudo make install
sudo depmod -a
cd ..

git clone https://github.com/vikey725/Also-Me.git
git clone https://github.com/facebookresearch/detectron2.git

source $(conda info --base)/etc/profile.d/conda.sh
conda create -y -n $CONDA_ENV_NAME python=3.7
conda activate $CONDA_ENV_NAME

pip install -r Also-Me/requirements.txt
pip install -e detectron2
pip install 'git+https://github.com/facebookresearch/fvcore.git'
sudo apt-get install python-opencv 
sudo apt-get install ffmpeg 

wget https://dl.fbaipublicfiles.com/densepose/densepose_rcnn_R_50_FPN_WC1_s1x/173862049/model_final_289019.pkl -P 2d-mimic/checkpoints/model_final_289019.pkl
wget https://github.com/italojs/facial-landmarks-recognition/blob/master/shape_predictor_68_face_landmarks.dat?raw=true -P 2d-mimic/checkpoints/shape_predictor_68_face_landmarks.dat

sudo modprobe v4l2loopback video_nr=VIRT_CAM_ID card_label=VIRT_CAM_NAME exclusive_caps=1

