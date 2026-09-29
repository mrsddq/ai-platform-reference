param(
    [string]$BaseUrl = 'http://localhost:8000'
)

$ErrorActionPreference = 'Stop'
if (-not $env:API_KEY) { throw 'Set API_KEY before running the demo.' }
$headers = @{ 'X-API-Key' = $env:API_KEY }
$root = Split-Path $PSScriptRoot -Parent

Invoke-RestMethod "$BaseUrl/health/ready" | ConvertTo-Json -Depth 8

Get-ChildItem (Join-Path $root 'sample_data') -Filter '*.txt' -File | ForEach-Object {
    $body = @{ source_id = $_.BaseName; version = 'v1'; text = (Get-Content $_.FullName -Raw -Encoding UTF8) } | ConvertTo-Json -Depth 8
    Invoke-RestMethod "$BaseUrl/documents" -Method Post -Headers $headers -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 8
}

$query = @{ query = 'What metadata is required before a model release?'; limit = 3 } | ConvertTo-Json
Invoke-RestMethod "$BaseUrl/search" -Method Post -Headers $headers -ContentType 'application/json' -Body $query | ConvertTo-Json -Depth 8

$answer = @{ query = 'What metadata is required before a model release?' } | ConvertTo-Json
Invoke-RestMethod "$BaseUrl/answer" -Method Post -Headers $headers -ContentType 'application/json' -Body $answer | ConvertTo-Json -Depth 8
