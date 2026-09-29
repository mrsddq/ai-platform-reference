param(
    [string]$BaseUrl = 'http://localhost:8000',
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'
function HasSource($Hits, $SourceId) {
    return @($Hits | Where-Object { $_.source_id -eq $SourceId }).Count -gt 0
}

if ($SelfTest) {
    if (-not (HasSource @([pscustomobject]@{source_id='expected'}) 'expected')) { throw 'Positive self-test failed.' }
    if (HasSource @([pscustomobject]@{source_id='other'}) 'expected') { throw 'Negative self-test failed.' }
    Write-Output 'Evaluator self-test passed.'
    return
}

if (-not $env:API_KEY) { throw 'Set API_KEY before running evaluation.' }
$headers = @{ 'X-API-Key' = $env:API_KEY }
$cases = Get-Content (Join-Path (Split-Path $PSScriptRoot -Parent) 'evaluation/cases.jsonl') |
    Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
$passedAt1 = 0
$passedAt3 = 0
foreach ($case in $cases) {
    $body = @{ query = $case.question; limit = 3 } | ConvertTo-Json
    $result = Invoke-RestMethod "$BaseUrl/search" -Method Post -Headers $headers -ContentType 'application/json' -Body $body
    $top1 = @($result.hits).Count -gt 0 -and $result.hits[0].source_id -eq $case.expected_source_id
    $top3 = HasSource $result.hits $case.expected_source_id
    if ($top1) { $passedAt1++ }
    if ($top3) { $passedAt3++ }
    [pscustomobject]@{ case = $case.id; expected = $case.expected_source_id; hit_at_1 = $top1; hit_at_3 = $top3 }
}
Write-Output "Retrieval hit@1: $passedAt1/$($cases.Count); hit@3: $passedAt3/$($cases.Count)"
if ($passedAt1 -ne $cases.Count) { throw 'Retrieval evaluation failed; inspect the per-case results.' }
