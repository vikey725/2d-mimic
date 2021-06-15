# Clone 2 repos.
git clone https://github.com/facebookresearch/detectron2.git
conda create -n alsome1 python==3.7 -y
conda activate alsome1
pip install -r requirements.txt
pip install -e detectron2
pip install 'git+https://github.com/facebookresearch/fvcore.git'
wget https://dl.fbaipublicfiles.com/densepose/densepose_rcnn_R_50_FPN_WC1_s1x/173862049/model_final_289019.pkl -P checkpoints/model_final_289019.pkl
wget https://github.com/italojs/facial-landmarks-recognition/blob/master/shape_predictor_68_face_landmarks.dat?raw=true -P checkpoints/shape_predictor_68_face_landmarks.dat
git clone https://github.com/umlaeute/v4l2loopback.git
cd v4l2loopback
make
