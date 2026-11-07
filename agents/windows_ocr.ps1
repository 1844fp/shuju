param([Parameter(Mandatory=$true)][string]$ImagePath, [int]$PdfPage = 0)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$storageFileType = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$streamType = [Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime]
$decoderType = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$bitmapType = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$engineType = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
$resultType = [Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
    $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Wait-Result($operation, [type]$resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.GetAwaiter().GetResult()
}
$engine = $engineType::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) { throw 'No Windows OCR language available' }
$file = Wait-Result ($storageFileType::GetFileFromPathAsync($ImagePath)) $storageFileType
$max = [Math]::Min($engineType::MaxImageDimension, 4096)
if ($PdfPage -gt 0) {
    $pdfType = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime]
    $optionsType = [Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType=WindowsRuntime]
    $memoryStream = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
    $pdf = Wait-Result ($pdfType::LoadFromFileAsync($file)) $pdfType
    $page = $pdf.GetPage($PdfPage - 1)
    $stream = $memoryStream::new()
    try {
        $size = $page.Size
        $scale = [Math]::Min($max, 2400) / [Math]::Max($size.Width, $size.Height)
        $options = $optionsType::new()
        $options.DestinationWidth = [Math]::Max(1, [Math]::Floor($size.Width * $scale))
        $options.DestinationHeight = [Math]::Max(1, [Math]::Floor($size.Height * $scale))
        $action = $page.RenderToStreamAsync($stream, $options)
        $asActionTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
            $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
        } | Select-Object -First 1
        [void]$asActionTask.Invoke($null, @($action)).GetAwaiter().GetResult()
        $stream.Seek(0)
    } catch { $stream.Dispose(); throw } finally { $page.Dispose() }
} else {
    $stream = Wait-Result ($file.OpenReadAsync()) $streamType
}
try {
    $decoder = Wait-Result ($decoderType::CreateAsync($stream)) $decoderType
    if ($decoder.PixelWidth -gt $max -or $decoder.PixelHeight -gt $max) { throw 'Image dimensions exceed OCR limit' }
    $bitmap = Wait-Result ($decoder.GetSoftwareBitmapAsync()) $bitmapType
    try {
        $result = Wait-Result ($engine.RecognizeAsync($bitmap)) $resultType
        @{text = $result.Text; language = $engine.RecognizerLanguage.LanguageTag} | ConvertTo-Json -Compress
    } finally { $bitmap.Dispose() }
} finally { $stream.Dispose() }
