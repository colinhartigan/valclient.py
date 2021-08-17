@echo off
@RD /S /Q "D:\colin\programming\VALORANT\valclient.py\dist"
python -m build
python -m twine upload dist/*
pause