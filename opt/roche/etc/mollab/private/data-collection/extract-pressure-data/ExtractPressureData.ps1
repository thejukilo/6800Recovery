$rootPath = "./PressureData/"
$fileNameExtension = "abcdefghijklmnopqrstuvwxyz"
$fileNameExtensionCounter = 0
$sampleTransferPipettorDataFound = $false
$processHeadDataFound = $false

function ExtractEventBody {
    param (
        [string]$line
    )
    $eventContent = ConvertFrom-Json $line
    return $eventContent.Body
}

function GetUniquePath {
    param (
        [string]$path
    )

    if (Test-Path $path -PathType leaf) {
        $fileNameWithoutExtension = $path.Substring(0, $path.LastIndexOf('.'))
        $newFileName = $fileNameWithoutExtension + "_" + $fileNameExtension[$fileNameExtensionCounter]
        $Script:fileNameExtensionCounter++
        return $newFileName + [System.IO.Path]::GetExtension($path)
    }

    return $path
}

function GetRunId {
    param (
        [hashtable]$runIdDictionary,
        [array]$workOrderIds
    )

    foreach ($workOrderId in $workOrderIds) {
        if ($null -ne $workOrderId) {
            return $runIdDictionary[$workOrderId]
        }
    }
    
    throw "No run id found for work order ids in PressureDataCollected event, event stream might be corrupted!"
}

function WritePressureData {
    param (
        [string]$data,
        [string]$filePath,
        [string]$filename,
        [string]$workOrderIds = $null
    )

    $fullPath = $filePath + "/" + $filename
    $fullPath = GetUniquePath $fullPath
    New-Item -ItemType Directory -Force -Path $filePath

    # Write a line with the work order ids in case of process head
    if ($workOrderIds)
    {
        Set-Content -Path $fullPath -Value $workOrderIds
    }

    # Use this line if no data conversion is necessary
    $dataAsText = $data
    # Use the following line if the pressure data is encoded as Base64
    # $dataAsText = [Convert]::FromBase64String($data)

    $dataAsText = $dataAsText.replace('\n',"`r`n")
    $dataAsText = $dataAsText.replace('\t',"`t")

    Add-Content -Path $fullPath -Value $dataAsText
}

# This function is a workaround and only required because of different behavior on Windows as on Linux.
# Maybe in future the Timestamp property of the events is a datetime and not a string on Windows too.
function GetFormattedTimestamp {
    param (
        [datetime]$timeStamp
    )

    $formattedTimestamp = $timeStamp.ToUniversalTime().ToString("yyyy-MM-dd_HH.mm.ss.fff")
    return $formattedTimestamp
}

Try {
    # Delete PressureData folder before extracting data
    if (Test-Path $rootPath) {
        Remove-Item $rootPath -Recurse -ErrorAction Ignore
    }

    # Create empty hash table for the mapping from workOrderId to runId
    $runIdDictionary = @{}

    Get-ChildItem -Path ./eventstream/*.log |
        ForEach-Object {
            foreach ($line in [IO.File]::ReadLines($_)) {
                if ($line -match "SamplePipettorPressureDataCollected") {
                    $sampleTransferPipettorDataFound = $true
                    $samplePipettorPressureDataCollected = ExtractEventBody $line

                    $runId = GetRunId $runIdDictionary $samplePipettorPressureDataCollected.WorkOrderId
                    $path = $rootPath + "RunId_" + $runId + "/SampleTransferPipettor/WorkOrderId_" + $samplePipettorPressureDataCollected.WorkOrderId

                    $timestamp = GetFormattedTimestamp $samplePipettorPressureDataCollected.Timestamp
                    $pipettingActionName = $samplePipettorPressureDataCollected.PipettingStep
                    $filename = $timestamp + "_" + $pipettingActionName + ".arf"

                    WritePressureData $samplePipettorPressureDataCollected.PressureData $path $filename
                }
				elseif ($line -match "SamplePipettorLevelDetectionDataCollected") {
                    $sampleTransferPipettorDataFound = $true
                    $samplePipettorLevelDetectionDataCollected = ExtractEventBody $line

                    $runId = GetRunId $runIdDictionary $samplePipettorLevelDetectionDataCollected.WorkOrderId
                    $path = $rootPath + "RunId_" + $runId + "/SampleTransferPipettor/WorkOrderId_" + $samplePipettorLevelDetectionDataCollected.WorkOrderId

                    $timestamp = GetFormattedTimestamp $samplePipettorLevelDetectionDataCollected.Timestamp
                    $pipettingActionName = "VolumeCheck"
                    $filename = $timestamp + "_" + $pipettingActionName + ".arf"

                    WritePressureData $samplePipettorLevelDetectionDataCollected.MeasuredLevelDetectionData $path $filename
                }				
                elseif ($line -match "ProcessPipettorPressureDataCollected") {
                    $processHeadDataFound = $true
                    $processPipettorPressureDataCollected = ExtractEventBody $line

                    $runId = GetRunId $runIdDictionary $processPipettorPressureDataCollected.WorkOrderIds
                    $path = $rootPath + "RunId_" + $runId + "/ProcessHead_" + $processPipettorPressureDataCollected.PipettorId

                    $timestamp = GetFormattedTimestamp $processPipettorPressureDataCollected.Timestamp
                    $processStepName = $processPipettorPressureDataCollected.ProcessStepId
                    $pipettingActionName = $processPipettorPressureDataCollected.PipettingStep
                    $filename = $timestamp + "_" + $processStepName + "_" + $pipettingActionName + ".arf"

                    $workOrderIdsLine = "WorkOrderIDs: " + '"' + ($processPipettorPressureDataCollected.WorkOrderIds -join '","') + '"'
                    WritePressureData $processPipettorPressureDataCollected.PressureData $path $filename $workOrderIdsLine
                }
                elseif ($line -match "RunExecutionStarted") {
                    New-Item -ItemType Directory -Force -Path $rootPath
                    $runIdFile = $rootPath + "RunIds_WorkOrderIds.txt"
                    $runExecutionStarted = ExtractEventBody $line
                    $runId = $runExecutionStarted.RunId
                    $runIdLine = "RunId: " + $runId
                    Add-Content -Path $runIdFile -Value $runIdLine 

                    foreach ($workOrder in $runExecutionStarted.AssignedWorkOrders) {
                        $workOrderLine = "WorkOrderId: " + $workOrder.id
                        switch ($workOrder.discriminator) {
                            SampleWorkOrder { 
                                $workOrderLine = $workOrderLine + " SampleId: " + $workOrder.SampleId
                            }
                            ControlWorkOrder { 
                                $workOrderLine = $workOrderLine + " ControlName: " + $workOrder.ControlName
                            }
                            Default {
                                $message = "Unknown WorkOrder discriminator '" + $workOrder.discriminator + "', cannot extract SampleId or ControlName!"
                                Write-Host $message -ForegroundColor Red
                                $workOrderLine = $workOrderLine + " " + $message
                            }
                        }
                        Add-Content -Path $runIdFile -Value $workOrderLine
                        $runIdDictionary[$workOrder.Id] = $runId
                    }
                    Add-Content -Path $runIdFile -Value ""
                }
            }
        }

    # Inform the user if sample transfer pipettor pressure data was found
    if ($sampleTransferPipettorDataFound) {
        Write-Host "All PressureData files for the SampleTransferPipettor successfully exported and stored" -ForegroundColor Green
    } else {
        Write-Host "No PressureData for the SampleTransferPipettor found" -ForegroundColor Red
    }

    # Inform the user if process head pressure data was found
    if ($processHeadDataFound) {
        Write-Host "All PressureData files for the ProcessHead successfully exported and stored" -ForegroundColor Green
    } else {
        Write-Host "No PressureData for the ProcessHead found" -ForegroundColor Red
    }
}
Catch {
    Write-Host $_.Exception.Message`n -ForegroundColor Red
}