#!/bin/bash

# 建立一個新的 screen session 名稱 fish_run，第一個視窗 web，跑 001.py，並設定 TERM 環境變數
screen -dmS fish_web -t web bash -c "export TERM=xterm-256color; python3 001.py"

# 在同一個 session 新建第二個視窗 video，跑 USC_VIDEO_publish.py，啟用虛擬環境，並設定 TERM
screen -S fish_web -X screen -t video bash -c "export TERM=xterm-256color; source rtsp_to_base64_env/bin/activate && python3 USC_VIDEO_publish.py"

# 在同一個 session 新建第三個視窗 email，跑 test_error.py，啟用虛擬環境，並設定 TERM
screen -S fish_web -X screen -t email bash -c "export TERM=xterm-255color; source rtsp_to_base64_env/bin/activate && python3 test_error.py"

# 在同一個 session 新建第三個視窗 api，跑 IoTtalk_v1_py/DAI.py，並設定 TERM
screen -S fish_web -X screen -t api bash -c "export TERM=xterm-255color; python3 IoTtalk_v1_py/DAI.py"
