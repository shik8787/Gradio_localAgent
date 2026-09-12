$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerRoot = Join-Path $ProjectRoot "qwen-agent\qwen-agent-src"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $ProjectRoot "logs"
$OutputLog = Join-Path $LogDirectory "gradio.stdout.log"
$ErrorLog = Join-Path $LogDirectory "gradio.stderr.log"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found: $Python"
}

# Task Scheduler stops PowerShell, not its children. Keep the Python tree in a
# kill-on-close job so stopping or restarting the task cannot leave port 7860 busy.
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class GradioLifetimeJob
{
    [StructLayout(LayoutKind.Sequential)]
    private struct BasicLimits
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IoCounters
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ExtendedLimits
    {
        public BasicLimits Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemoryLimit, JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateJobObject(IntPtr attributes, string name);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetInformationJobObject(
        SafeFileHandle job, int infoClass, ref ExtendedLimits info, uint length);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AssignProcessToJobObject(SafeFileHandle job, IntPtr process);

    public static SafeFileHandle Attach()
    {
        var job = CreateJobObject(IntPtr.Zero, null);
        if (job.IsInvalid)
            throw new Win32Exception(Marshal.GetLastWin32Error());

        var limits = new ExtendedLimits();
        limits.Basic.LimitFlags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (!SetInformationJobObject(job, 9, ref limits,
                                     (uint)Marshal.SizeOf(typeof(ExtendedLimits))) ||
            !AssignProcessToJobObject(job, Process.GetCurrentProcess().Handle))
        {
            var error = Marshal.GetLastWin32Error();
            job.Dispose();
            throw new Win32Exception(error);
        }
        return job;
    }
}
'@
$LifetimeJob = [GradioLifetimeJob]::Attach()

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
Set-Location -LiteralPath $ServerRoot

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONUTF8 = "1"
$env:GRADIO_ANALYTICS_ENABLED = "False"
$Process = Start-Process -FilePath $Python `
    -ArgumentList "-u", "web_agent.py" `
    -WorkingDirectory $ServerRoot `
    -RedirectStandardOutput $OutputLog `
    -RedirectStandardError $ErrorLog `
    -NoNewWindow -Wait -PassThru

[GC]::KeepAlive($LifetimeJob)
exit $Process.ExitCode
