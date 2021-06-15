# Clone 2 repos.
git clone https://github.com/facebookresearch/detectron2.git

# Create conda and activate
conda create -n alsome python==3.7
conda activate alsome

# Install dependencies
pip install -r 2d-mimic/requirements.txt
pip install -e detectron2
pip install 'git+https://github.com/facebookresearch/fvcore.git'
apt-get install python-opencv 
apt-get install ffmpeg 

# Download model & checkpoint files
wget https://dl.fbaipublicfiles.com/densepose/densepose_rcnn_R_50_FPN_WC1_s1x/173862049/model_final_289019.pkl -P 2d-mimic/checkpoints/model_final_289019.pkl
wget https://github.com/italojs/facial-landmarks-recognition/blob/master/shape_predictor_68_face_landmarks.dat?raw=true -P 2d-mimic/checkpoints/shape_predictor_68_face_landmarks.dat

# Install v4l2loopback & its utils for 2nd camera creation
git clone https://github.com/umlaeute/v4l2loopback.git
cd v4l2loopback
make
sudo make install
sudo apt-get install v4l2loopback-utils

# Create the secondary camera 
sudo modprobe v4l2loopback video_nr=7 card_label="Also-Me" exclusive_caps=1
