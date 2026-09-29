@echo off
title GdzieLokum - Wszystkie Mieszkania w Jednym Miejscu
echo ========================================================
echo   Uruchamianie aplikacji GdzieLokum...
echo ========================================================
echo.
cd /d "%~dp0"
start http://localhost:8501
python -m streamlit run app.py --server.headless false
pause
