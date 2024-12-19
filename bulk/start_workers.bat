@REM @echo off
@REM setlocal

@REM REM Number of workers to start
@REM set NUM_WORKERS=6

@REM REM Loop to start each worker with a unique name
@REM for /L %%i in (1,1,%NUM_WORKERS%) do (
@REM     start cmd /c "celery -A bulk worker --loglevel=debug --concurrency=1 --pool=solo -n worker%%i@%COMPUTERNAME%"
@REM )

@REM endlocal
