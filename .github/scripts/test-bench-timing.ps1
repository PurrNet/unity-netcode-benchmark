param(
    [Parameter(Mandatory)][ValidateSet('purrnet', 'mirror', 'fishnet', 'ngo')][string]$Netcode,
    [int[]]$TickRates = @(20, 60),
    [int]$Port = 28770
)

# Local correctness smoke test, not a performance run. Build a Windows Mono player first with
# PurrNet.NetBench.Editor.CIBuild.BuildWindowsPlayer -buildOutput build/BenchReview/NetBench.exe.
$ErrorActionPreference = 'Stop'
$benchRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$benchBuild = Join-Path $benchRoot "$Netcode/build/BenchReview"
$benchPlayer = (Resolve-Path (Join-Path $benchBuild 'NetBench.exe')).Path

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

foreach ($hz in $TickRates) {
    $benchOutput = New-Item -ItemType Directory -Force -Path (Join-Path $benchBuild "smoke-$hz")
    $common = "-batchmode -nographics -port $Port -benchObjects 10 -benchSeconds 2 -warmupSeconds 1 -idleSeconds 1 -tests 1,2,3,4,5,6,7,8 -tickRate $hz -connectTimeout 25 -maxRunSeconds 100"
    $benchProcesses = @()
    try {
        foreach ($role in @('server', 'client')) {
            $argsForRole = "$common -role $role -count 1 -serverHost 127.0.0.1 -results `"$benchOutput/$role.json`" -logFile `"$benchOutput/$role.log`""
            $benchProcesses += Start-Process -FilePath $benchPlayer -ArgumentList $argsForRole -WindowStyle Hidden -PassThru
        }
        foreach ($process in $benchProcesses) {
            Require ($process.WaitForExit(110000)) "$Netcode $hz Hz process timed out; see $benchOutput"
            Require ($process.ExitCode -eq 0) "$Netcode $hz Hz process exited $($process.ExitCode); see $benchOutput"
        }
        $server = Get-Content -Raw (Join-Path $benchOutput 'server.json') | ConvertFrom-Json
        $client = Get-Content -Raw (Join-Path $benchOutput 'client.json') | ConvertFrom-Json
        foreach ($run in @($server, $client)) {
            Require ($run.completed -and -not $run.error) "$Netcode $hz Hz $($run.role) did not complete"
            Require ($run.tickRate -eq $hz) "$Netcode $($run.role) used $($run.tickRate) Hz, expected $hz"
            Require ($run.tests.Count -eq 9) "$Netcode $hz Hz $($run.role) missed a test"
            foreach ($test in $run.tests) {
                Require (-not $test.truncated) "$Netcode $hz Hz $($run.role) $($test.name) was truncated"
                Require ($test.connections -eq 1) "$Netcode $hz Hz $($run.role) $($test.name) lost its connection"
            }
        }
        foreach ($name in @('SendRPC', 'SyncVars')) {
            $s = $server.tests | Where-Object name -eq $name
            $c = $client.tests | Where-Object name -eq $name
            Require ($s.deliveryComplete -and $c.deliveryComplete) "$Netcode $hz Hz $name delivery check incomplete"
            $rate = if ($name -eq 'SendRPC') { $s.rpcsSentPerSec } else { $s.syncMutationsPerSec }
            Require ([Math]::Abs($rate / (10 * $hz) - 1) -lt 0.05) "$Netcode $hz Hz $name generated $rate/s, expected $(10 * $hz)/s"
            if ($name -eq 'SendRPC') {
                Require ($s.rpcsSent -gt 0 -and $s.rpcsSent -eq $c.rpcsReceived) "$Netcode $hz Hz RPC mismatch: sent $($s.rpcsSent), received $($c.rpcsReceived)"
            } else {
                Require ($s.finalStateObjects -eq 10 -and $c.finalStateObjects -eq 10 -and $s.finalStateHash -eq $c.finalStateHash) "$Netcode $hz Hz final state mismatch: server $($s.finalStateObjects)/$($s.finalStateHash), client $($c.finalStateObjects)/$($c.finalStateHash)"
                Require ($c.syncObservationAvailable -and $c.syncFieldSamples -gt 0) "$Netcode $hz Hz client-visible state observation missing"
                # Loopback regression tolerance only, not a published benchmark scoring threshold.
                Require ([Math]::Abs($c.syncObservedChangesPerSec / (10 * $hz) - 1) -lt 0.1) "$Netcode $hz Hz client observed $($c.syncObservedChangesPerSec) changes/s, expected $(10 * $hz)/s"
                Require ($c.syncSilenceAvgMs -ge 0 -and $c.syncSilenceMaxMs -ge $c.syncSilenceAvgMs) "$Netcode $hz Hz invalid field-silence statistics"
            }
        }
        $inputRate = ($server.tests | Where-Object name -eq 'ClientInput').inputsPerSec
        Require ([Math]::Abs($inputRate / $hz - 1) -lt 0.1) "$Netcode $hz Hz input rate $inputRate/s, expected $hz/s"
        Write-Output "PASS: $Netcode $hz Hz, all scenarios, workload rates, RPC delivery, client-visible changes, final SyncVars, final-window connection."
    } finally {
        foreach ($process in $benchProcesses) {
            if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
            $process.Dispose()
        }
    }
}
