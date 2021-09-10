@echo off
@RD /S /Q "D:\colin\programming\VALORANT\valclient.py\dist"
@RD /S /Q "D:\colin\programming\VALORANT\valclient.py\build"
python -m build
python -m twine upload dist/*
pause