#Requires AutoHotkey v2.0
#SingleInstance Force

; Single file with all states: q,x1,x2 (1=on,0=off)
stateFile := A_ScriptDir . "\state.txt"

; Initialize if doesn't exist
if !FileExist(stateFile)
    FileAppend "0,0,0", stateFile

; Read states every 100ms
SetTimer CheckStates, 100

CheckStates() {
    global states := StrSplit(FileRead(stateFile), ",")
    global q := states[1] = "1"
    global x1 := states[2] = "1"
    global x2 := states[3] = "1"
}

; Individual toggles control hotkeys
#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && q
q::{
    SendInput "{q}"
    Sleep 60
    SendInput "{RButton}"
}

#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && x1
XButton1::SendInput "{9}"

#HotIf WinActive("ahk_exe RobloxPlayerBeta.exe") && x2
XButton2::SendInput "{8}"

#HotIf

End::ExitApp