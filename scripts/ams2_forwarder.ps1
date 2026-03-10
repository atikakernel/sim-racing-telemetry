# AMS2 UDP Forwarder for WSL
# ===========================
# Relays Automobilista 2 broadcast telemetry (port 5606) to WSL IP.

$AMS2_PORT = 5606

$host.UI.RawUI.WindowTitle = "AMS2 -> WSL Forwarder"
Clear-Host
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  AMS2 TELEMETRY FORWARDER (WSL)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# --- WSL IP Detection ---
Write-Host "Detecting WSL IP..." -NoNewline
try {
    $WSL_IP = (wsl hostname -I).Trim().Split(' ')[0]
    if ([string]::IsNullOrWhiteSpace($WSL_IP)) { throw "IP empty" }
    Write-Host " OK ($WSL_IP)" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    $WSL_IP = Read-Host "Enter WSL IP manually (hostname -I)"
}

# --- Networking Setup ---
$listener = New-Object System.Net.Sockets.UdpClient($AMS2_PORT)
$sender = New-Object System.Net.Sockets.UdpClient()
$wslEndpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Parse($WSL_IP), $AMS2_PORT)
$remoteEP = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)

Write-Host "Listening on port $AMS2_PORT..."
Write-Host "Forwarding to $WSL_IP..."
Write-Host "Press Ctrl+C to stop."
Write-Host "----------------------------------------"

$packetCount = 0

try {
    while ($true) {
        if ($listener.Available -gt 0) {
            $data = $listener.Receive([ref]$remoteEP)
            $sender.Send($data, $data.Length, $wslEndpoint) | Out-Null
            $packetCount++
            
            if ($packetCount % 60 -eq 0) {
                Write-Host "`r[<] Relaying data... Packets: $packetCount" -NoNewline -ForegroundColor Green
            }
        }
        Start-Sleep -Milliseconds 5
    }
} catch {
    Write-Host "`nError: $_" -ForegroundColor Red
} finally {
    $listener.Close()
    $sender.Close()
    Write-Host "`nStopped."
}
