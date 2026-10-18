#!/bin/bash
# boot.sh <server_dir> : start a fresh test server, print READY or the failure summary.
# Leaves the java process running on success (stop it via RCON "stop"); kills it on failure.
cd "$1" || exit 1
rm -rf world logs crash-reports
# Java 17 that Prism downloaded (Windows), else whatever java is on PATH. MEMORY=10G bash boot.sh ... for a bigger heap
JAVA=$([ -n "$APPDATA" ] && ls "$(cygpath "$APPDATA")"/PrismLauncher/java/*jre17*/bin/java.exe 2>/dev/null | head -1)
"${JAVA:-java}" -Xms4G -Xmx"${MEMORY:-6G}" -jar fabric-server-launch.jar nogui > console.log 2>&1 &
pid=$!
fail='Failed to start the minecraft server|Incompatible mods found|Encountered an unexpected exception|This crash report has been saved'
while kill -0 $pid 2>/dev/null; do
  if grep -q 'Done (' console.log; then echo "READY: $(grep -m1 'Done (' console.log)"; exit 0; fi
  if grep -qE "$fail" console.log; then sleep 3; break; fi
  sleep 2
done
kill $pid 2>/dev/null
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { \$_.CommandLine -match 'fabric-server-launch.jar' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" 2>/dev/null
echo "FAILED"
grep -m1 -E "$fail" -A3 console.log
grep -E "provided by '|^Caused by" console.log | head -5
exit 1
