::Turn off echoing
@ECHO OFF

::Check standard path first
IF EXIST "C:\Program Files\pfx\jobtypes\maya\qbMayaRender.pl" GOTO STANDARD

::Check derived path
IF EXIST "%PFXDIR%\jobtypes\maya\qbMayaRender.pl" GOTO DERIVE

::Check local path
IF EXIST "qbMayaRender.pl" GOTO LOCAL


ECHO. Unable to locate qbMayaRender.pl
ECHO. PFXDIR not set to valid location


:STANDARD
:: Execute Module using standard path
perl "C:\Program Files\pfx\jobtypes\maya\qbMayaRender.pl" %*
GOTO DONE

:DERIVE
:: Execute Module using derived path
perl "%PFXDIR%\jobtypes\maya\qbMayaRender.pl" %*
GOTO DONE

::LOCAL
:: Execute Module using local path
perl "qbMayaRender.pl" %*
GOTO DONE

:DONE


