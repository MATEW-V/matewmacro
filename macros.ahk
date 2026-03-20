#Requires AutoHotkey v2.0
#SingleInstance Force

; ============ AUTO-CLOSE WHEN PYTHON EXITS ============
; Monitor Python process and exit when Python GUI closes

; Method 1: Monitor PID file
SetTimer CheckPythonPID, 1000

CheckPythonPID() {
    pidFile := A_ScriptDir . "\python_pid.txt"
    if FileExist(pidFile) {
        try {
            pid := FileRead(pidFile)
            pid := Trim(pid)
            if pid ~= "^\d+$" {
                ProcessExist := ProcessExist(pid)
                if !ProcessExist {
                    ExitApp
                }
            }
        }
    }
}

; Method 2: Monitor exit signal file
SetTimer CheckExitSignal, 500

CheckExitSignal() {
    signalFile := A_ScriptDir . "\exit_signal.txt"
    if FileExist(signalFile) {
        FileDelete(signalFile)
        ExitApp
    }
}

; Method 3: Monitor Python window
SetTimer CheckPythonWindow, 1000

CheckPythonWindow() {
    if !WinExist("MATEW MACRO") {
        ExitApp
    }
}

; ============ YOUR EXISTING MACRO CODE ============
; Single file with all states: q,x1,x2,cf (1=on,0=off)
stateFile := A_ScriptDir . "\state.txt"

; Initialize if doesn't exist
if !FileExist(stateFile)
    FileAppend "0,0,0,0", stateFile

; Read states every 100ms
SetTimer CheckStates, 100

CheckStates() {
    global states := StrSplit(FileRead(stateFile), ",")
    global q := states[1] = "1"
    global x1 := states[2] = "1"
    global x2 := states[3] = "1"
    global cf := states[4] = "1"
}

; Individual toggles control hotkeys
#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && q
q::{
    SendInput "{q}"
    Sleep 60
    SendInput "{RButton}"
}

#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && cf
^f::{
    SendInput "{f}"
    SendInput "{q}"   
}

#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && x1
XButton1::SendInput "{9}"

#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && x2
XButton2::SendInput "{8}"

#HotIf

End::ExitApp