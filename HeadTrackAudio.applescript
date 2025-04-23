-- HeadTrackAudio Launcher

on run
   set pythonScript to (path to home folder as text) & "Projects:veklo:head_track_audio.py"
   do shell script "python3 " & quoted form of POSIX path of pythonScript
end run 