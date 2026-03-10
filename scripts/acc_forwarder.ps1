# ACC UDP Forwarder - MODO MANUAL SEGURO
# =========================================
# Este script NO enviará nada automáticamente para evitar crashes.
# Tú controlas cuándo conectar.

$ACC_IP = "127.0.0.1"
$ACC_PORT = 9000
$WSL_PORT = 9001

# --- Configuración Visual ---
$host.UI.RawUI.WindowTitle = "ACC Forwarder - MANUAL MODE"
Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ACC FORWARDER - MODO MANUAL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Abre ACC y entra a pista."
Write-Host "2. Presiona 'H' aqui para conectar."
Write-Host "3. Si CRASHEA al presionar 'H', avísame."
Write-Host "----------------------------------------" -ForegroundColor Gray

# --- Detección de WSL ---
Write-Host "Buscando WSL..." -NoNewline
try {
    $WSL_IP = (wsl hostname -I).Trim().Split(' ')[0]
    if ([string]::IsNullOrWhiteSpace($WSL_IP)) { throw "IP vacia" }
    Write-Host " OK ($WSL_IP)" -ForegroundColor Green
} catch {
    Write-Host " ERROR" -ForegroundColor Red
    $WSL_IP = Read-Host "Ingresa IP de WSL manual"
}

# --- Networking ---
$client = New-Object System.Net.Sockets.UdpClient(0)
$client.Client.ReceiveTimeout = 100  # 100ms para que la UI responda rápido
$client.Client.Blocking = $false

$accEndpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Parse($ACC_IP), $ACC_PORT)
$wslEndpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Parse($WSL_IP), $WSL_PORT)

function Send-Handshake {
    Write-Host "`n[>] Enviando Handshake..." -ForegroundColor Yellow
    try {
        $packet = New-Object System.Collections.Generic.List[byte]
        $packet.Add(1); $packet.Add(4) 
        
        $name = "Man_Fw"
        $nameBytes = [System.Text.Encoding]::Unicode.GetBytes($name)
        $packet.AddRange([BitConverter]::GetBytes([uint16]$name.Length))
        $packet.AddRange($nameBytes)
        
        $packet.AddRange([BitConverter]::GetBytes([uint16]0)) 
        $packet.AddRange([BitConverter]::GetBytes([int]250)) 
        $packet.AddRange([BitConverter]::GetBytes([uint16]0)) 
        
        $bytes = $packet.ToArray()
        $client.Send($bytes, $bytes.Length, $accEndpoint) | Out-Null
        Write-Host "    Enviado." -ForegroundColor Green
    } catch {
        Write-Host "    Error: $_" -ForegroundColor Red
    }
}

# --- Loop Principal ---
$running = $true
$packetCount = 0

while ($running) {
    # 1. Leer Teclado (No bloqueante)
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        if ($key.Key -eq 'H') {
            Send-Handshake
        }
        elseif ($key.Key -eq 'Q' -or $key.Key -eq 'Escape') {
            $running = $false
        }
    }

    # 2. Leer UDP
    try {
        $remoteEP = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
        if ($client.Available -gt 0) {
            $data = $client.Receive([ref]$remoteEP)
            if ($data.Length -gt 0) {
                # Forward
                $client.Send($data, $data.Length, $wslEndpoint) | Out-Null
                $packetCount++
                if ($packetCount % 50 -eq 0) {
                    Write-Host "`r[<] Recibiendo datos... Packets: $packetCount" -NoNewline -ForegroundColor Green
                }
            }
        }
    } catch {
        # Ignorar errores de socket temporales
    }

    Start-Sleep -Milliseconds 10
}

$client.Close()
Write-Host "`nCerrado."
