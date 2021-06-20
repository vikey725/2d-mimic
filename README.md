# Also-Me

The repo contains source code for also-me project. Also-me creates virtual avatar like segmentation over the camera feed, so you can use in zoom, gmeet and elsewhere. 

## Install & Run Instructions with colab GPU
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/vikey725/2d-mimic/blob/main/Also_Me_collab_server.ipynb)
```
1. Setup server
Open the above colab badge and run all. It will output the command to run in local system

2. Setup local system
    a. Linux
    curl -s http://example.com/script.sh | bash

    b. 


```

## How to Use
```
# For using with Local GPU
1. cd 2d-mimic
2. python -m scripts.run_demo -bg 1

# For using with local CPU (would be very slow)
1. Change line 25 in /2d-mimic/configs/model_config.py to -> cfg.MODEL.DEVICE = 'cpu'
2. cd 2d-mimic
3. python -m scripts.run_demo -bg 1
```

### How to use (with remote GPU in google colab)

```
1. Open the code in colab using above colab badge
2. Run all cells in colab and the command to run in local system will be ouput there.
3. cd 2d-mimic
4. use the copied command from colab (ex: python -m scripts.run_demo -bg 1 -rs 1 -rsip tcp://6.tcp.ngrok.io:18106)
```

### misc commands, use if required
```
# (Optional) Check the created camera
v4l2-ctl --list-devices 
You should find something like - 
Also-Me (platform:v4l2loopback-007):
    /dev/video7

# (Optional) To see the new camera output
ffplay /dev/video7

# (Optional) To delete the secondary camera
sudo modprobe -r v4l2loopback
```

## References
https://github.com/cedriclmenard/irislandmarks.pytorch
