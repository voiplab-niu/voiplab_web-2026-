#!/bin/bash

# 建立一個新的 screen session 名稱 fish_run，第一個視窗 web，跑 001.py，並設定 TERM 環境變數
screen -dmS rag_web -t web bash -c "export TERM=xterm-256color; source ragenv/bin/activate && python3 app.py"
