@echo off
rem Lance comptoir sur le PC de la boutique
cd /d %~dp0
node src\server.js
pause
