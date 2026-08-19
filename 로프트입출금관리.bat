@echo off
chcp 65001 > nul
title (주)로프트프라퍼티스 입출금 관리

echo ========================================
echo   (주)로프트프라퍼티스 입출금 관리 프로그램
echo ========================================
echo.

cd /d C:\loftproperties

echo 프로그램을 시작합니다...
echo 브라우저가 자동으로 열립니다.
echo.
echo 종료하려면 이 창을 닫지 말고
echo 브라우저에서 작업이 끝난 후
echo 이 창에서 Ctrl + C 를 누르세요.
echo.

python -m streamlit run app.py

pause