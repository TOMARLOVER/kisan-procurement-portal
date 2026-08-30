@echo off
title Kisan Procurement Portal Launcher
echo Starting Kisan Procurement Portal Backend & Frontend...
echo Server running at: http://localhost:8000
start http://localhost:8000
cd /d \%~dp0backend\
python main.py
pause
