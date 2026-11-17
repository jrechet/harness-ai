@echo off
rem Starts counter on the shop PC
cd /d %~dp0
node src\server.js
pause
