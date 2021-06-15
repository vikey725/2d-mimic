cd v4l2loopback
make install
sudo apt-get install v4l2loopback-utils
sudo apt-get install python3-opencv 
sudo apt-get install ffmpeg  
sudo modprobe v4l2loopback video_nr=7 card_label="Also-Me" exclusive_caps=1
