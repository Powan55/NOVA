<#
.SYNOPSIS
    Generates DOCX and PDF deliverables from the Markdown document set.

.DESCRIPTION
    Markdown under docs/ is the source of truth. This script renders it to distributable
    formats in docs/dist/. Generated files are never edited directly.

    Mermaid diagrams are pre-rendered to PNG where the mermaid CLI is available. Where it is
    not, the diagram source is emitted as a code block and a warning is issued.

    PDF is produced by driving Word through COM, which avoids requiring a LaTeX installation.

.PARAMETER Format
    docx, pdf, or all. Defaults to all.

.PARAMETER SkipDiagrams
    Skip Mermaid pre-rendering even where the CLI is available.

.EXAMPLE
    powershell -File tools/build-docs.ps1
    powershell -File tools/build-docs.ps1 -Format docx
#>
[CmdletBinding()]
param(
    [ValidateSet('docx', 'pdf', 'all')][string]$Format = 'all',
    [switch]$SkipDiagrams
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docs = Join-Path $root 'docs'
$dist = Join-Path $docs 'dist'
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("nova-docs-" + [guid]::NewGuid().ToString('N').Substring(0, 8))

function Resolve-Tool([string]$name, [string[]]$extraPaths) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in $extraPaths) { if (Test-Path $p) { return $p } }
    return $null
}

$pandoc = Resolve-Tool 'pandoc' @(
    "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
    "$env:ProgramFiles\Pandoc\pandoc.exe"
)
if (-not $pandoc) {
    throw "Pandoc not found. Install it with: winget install --id JohnMacFarlane.Pandoc"
}

$mmdc = $null
if (-not $SkipDiagrams) {
    $mmdc = Resolve-Tool 'mmdc' @("$env:APPDATA\npm\mmdc.cmd")
    if (-not $mmdc) {
        Write-Warning "Mermaid CLI not found. Diagrams will render as code blocks."
        Write-Warning "Install with: npm install -g @mermaid-js/mermaid-cli"
    }
}

New-Item -ItemType Directory -Force -Path $dist, $work | Out-Null

# Source files, in the order they should appear if bound together.
$order = @(
    'README.md'
    'vision-and-scope.md'
    'srs.md'
    'architecture.md'
    'test-plan.md'
    'threat-model.md'
    'sdp.md'
    'risk-register.md'
    'decision-log.md'
    'ui-design.md'
)
$sources = @()
foreach ($f in $order) {
    $p = Join-Path $docs $f
    if (Test-Path $p) { $sources += Get-Item $p }
}
# A new top-level document that nobody added to $order would otherwise be skipped silently.
Get-ChildItem $docs -Filter '*.md' | Where-Object { $order -notcontains $_.Name } | ForEach-Object {
    Write-Warning "$($_.Name) is not in the ordered list; appending it at the end."
    $sources += $_
}
$sources += Get-ChildItem (Join-Path $docs 'adr') -Filter '*.md' | Sort-Object Name
$sources += Get-ChildItem (Join-Path $docs 'spikes') -Filter '*.md' | Sort-Object Name

# Converts YAML front matter into a visible table and pre-renders Mermaid blocks.
# Pandoc consumes front matter as metadata, which would otherwise drop ADR status from the output.
function Convert-Source([System.IO.FileInfo]$file, [string]$stem) {
    $text = Get-Content $file.FullName -Raw

    if ($text -match '(?s)\A---\r?\n(.*?)\r?\n---\r?\n(.*)\z') {
        $rows = foreach ($line in ($matches[1] -split "\r?\n")) {
            if ($line -match '^\s*([A-Za-z-]+)\s*:\s*(.*)$') {
                "| {0} | {1} |" -f $matches[1], $matches[2]
            }
        }
        $body = $matches[2]
        # Insert the table immediately after the first heading so it reads as a control block.
        $table = "`n| Field | Value |`n|---|---|`n" + ($rows -join "`n") + "`n"
        $body = [regex]::Replace($body, '(?m)^(#\s+.*)$', "`$1`n$table", 1)
        $text = $body
    }

    if ($mmdc) {
        $i = 0
        $text = [regex]::Replace($text, '(?s)```mermaid\r?\n(.*?)```', {
                param($m)
                $script:i++
                $mmd = Join-Path $work "$stem-$($script:i).mmd"
                $png = Join-Path $work "$stem-$($script:i).png"
                [System.IO.File]::WriteAllText($mmd, $m.Groups[1].Value, [System.Text.UTF8Encoding]::new($false))
                & $mmdc -i $mmd -o $png -b white -w 1400 --quiet 2>&1 | Out-Null
                if (Test-Path $png) { "![]($($png -replace '\\', '/'))" }
                else { "``````text`n" + $m.Groups[1].Value + "```````n" }
            })
    }

    $out = Join-Path $work "$stem.md"
    [System.IO.File]::WriteAllText($out, $text, [System.Text.UTF8Encoding]::new($false))
    return $out
}

$built = @()
foreach ($src in $sources) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($src.Name)
    # Mirror the source folder structure under dist/ rather than flattening with a prefix.
    $subdir = if ($src.Directory.Name -eq 'docs') { '' } else { $src.Directory.Name }
    $outDir = if ($subdir) { Join-Path $dist $subdir } else { $dist }
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $stem = if ($subdir) { "$subdir-$name" } else { $name }   # temp files stay unique
    $prepared = Convert-Source $src $stem
    $docx = Join-Path $outDir "$name.docx"

    $args = @(
        $prepared
        '--from', 'gfm+yaml_metadata_block'
        '--to', 'docx'
        '--output', $docx
        '--toc', '--toc-depth=3'
        '--resource-path', "$work;$docs"
    )
    $reference = Join-Path $docs '_assets/reference.docx'
    if (Test-Path $reference) { $args += @('--reference-doc', $reference) }

    & $pandoc @args
    if ($LASTEXITCODE -ne 0) {
        # The usual cause is a hidden Word instance still holding the file, left behind when a
        # previous run was interrupted before its COM cleanup ran.
        $orphans = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -eq 0 })
        if ($orphans) {
            Write-Warning ("{0} hidden Word instance(s) are running and may be holding output files open." -f $orphans.Count)
            Write-Warning "Close them with: Get-Process WINWORD | Where-Object { `$_.MainWindowHandle -eq 0 } | Stop-Process"
            Write-Warning "This does not affect Word windows you have open yourself."
        }
        throw "pandoc failed on $($src.Name)"
    }

    $built += [pscustomobject]@{ Source = $src.Name; Docx = $docx; Pdf = $null }
    Write-Host ("  docx  " + (Resolve-Path -Relative $docx))
}

if ($Format -in 'pdf', 'all') {
    $word = $null
    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0
    }
    catch {
        Write-Warning "Word not available. Skipping PDF generation. DOCX output is unaffected."
    }

    if ($word) {
        try {
            foreach ($item in $built) {
                $pdf = [System.IO.Path]::ChangeExtension($item.Docx, '.pdf')
                $doc = $word.Documents.Open($item.Docx, $false, $true)
                try {
                    # Refresh the table of contents, which Pandoc emits as a placeholder.
                    if ($doc.TablesOfContents.Count -gt 0) { $doc.TablesOfContents.Item(1).Update() }
                    $doc.SaveAs([ref]$pdf, [ref]17)   # 17 = wdFormatPDF
                    $item.Pdf = $pdf
                    Write-Host ("  pdf   " + (Resolve-Path -Relative $pdf))
                }
                finally { $doc.Close([ref]0) }
            }
        }
        finally {
            $word.Quit()
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
        }
    }
}

if ($Format -eq 'pdf') { Get-ChildItem $dist -Filter '*.docx' -Recurse | Remove-Item -Force }

Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "$($built.Count) documents written to docs/dist/"
