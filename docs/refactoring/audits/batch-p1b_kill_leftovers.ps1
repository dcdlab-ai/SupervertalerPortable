# Batch P1-B leftover cleanup: kills ONLY processes whose executable/command line
# belong to this session's runs (python-embed interpreter, probe scripts under the
# batch-p1b stage dir, the SupervertalerPortable sidecar jar). Never by image name.
$cands = @()
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  $cl = $_.CommandLine
  if ($cl -like '*batch-p1b*' -or $_.ExecutablePath -like 'E:\Dev\python-embed\*') {
    $cands += [pscustomobject]@{ Id = $_.ProcessId; Why = 'python-embed/probe'; CL = $cl.Substring(0, [Math]::Min(140, $cl.Length)) }
  }
}
Get-CimInstance Win32_Process -Filter "Name='java.exe' OR Name='javaw.exe'" | ForEach-Object {
  $cl = $_.CommandLine
  if ($cl -like '*SupervertalerPortable*') {
    $cands += [pscustomobject]@{ Id = $_.ProcessId; Why = 'sidecar java'; CL = $cl.Substring(0, [Math]::Min(140, $cl.Length)) }
  }
}
$all = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='java.exe' OR Name='javaw.exe'"
foreach ($c in $cands) {
  Write-Output ("KILL {0} ({1}) :: {2}" -f $c.Id, $c.Why, $c.CL)
  Stop-Process -Id $c.Id -Force -ErrorAction SilentlyContinue
}
$survivors = $all | Where-Object { $cands.Id -notcontains $_.ProcessId }
Write-Output ("SURVIVORS: {0}" -f ($survivors | ForEach-Object { "{0}:{1}" -f $_.ProcessId, $_.Name }) -join ', ')
