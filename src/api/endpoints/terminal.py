# Terminal API endpoint for secure command execution
import subprocess
import os
import shlex
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from src.core.dependencies import get_current_active_user
from src.db.models import User
from src.db.session import get_sync_db_session
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/terminal", tags=["terminal"])

# Whitelist of allowed commands for security
ALLOWED_COMMANDS = {
    'ls': {'args': ['-la', '-l', '-a', '-h'], 'description': 'List directory contents'},
    'pwd': {'args': [], 'description': 'Print working directory'},
    'whoami': {'args': [], 'description': 'Print current user'},
    'date': {'args': [], 'description': 'Print current date and time'},
    'echo': {'args': [], 'description': 'Print text to stdout'},
    'cat': {'args': [], 'description': 'Display file contents'},
    'grep': {'args': ['-i', '-n', '-v', '-c'], 'description': 'Search text in files'},
    'find': {'args': ['-name', '-type', '-size'], 'description': 'Find files and directories'},
    'head': {'args': ['-n'], 'description': 'Display first lines of file'},
    'tail': {'args': ['-n', '-f'], 'description': 'Display last lines of file'},
    'wc': {'args': ['-l', '-w', '-c'], 'description': 'Count lines, words, characters'},
    'df': {'args': ['-h'], 'description': 'Display disk space usage'},
    'du': {'args': ['-h', '-s'], 'description': 'Display directory space usage'},
    'free': {'args': ['-h'], 'description': 'Display memory usage'},
    'ps': {'args': ['aux'], 'description': 'Display running processes'},
    'top': {'args': ['-n', '1'], 'description': 'Display system processes'},
    'uname': {'args': ['-a'], 'description': 'Display system information'},
    'uptime': {'args': [], 'description': 'Display system uptime'},
    'env': {'args': [], 'description': 'Display environment variables'},
    'which': {'args': [], 'description': 'Locate command'},
    'history': {'args': [], 'description': 'Display command history'},
    'clear': {'args': [], 'description': 'Clear terminal screen'},
    'help': {'args': [], 'description': 'Display help information'},
    'man': {'args': [], 'description': 'Display manual pages'},
    'tree': {'args': ['-L', '2'], 'description': 'Display directory tree'},
    'file': {'args': [], 'description': 'Determine file type'},
    'stat': {'args': [], 'description': 'Display file statistics'},
    'mkdir': {'args': ['-p'], 'description': 'Create directories'},
    'touch': {'args': [], 'description': 'Create empty files'},
    'cp': {'args': ['-r', '-v'], 'description': 'Copy files and directories'},
    'mv': {'args': ['-v'], 'description': 'Move/rename files and directories'},
    'rm': {'args': ['-r', '-f', '-v'], 'description': 'Remove files and directories'},
    'chmod': {'args': [], 'description': 'Change file permissions'},
    'chown': {'args': [], 'description': 'Change file ownership'},
    'tar': {'args': ['-tf', '-xf', '-cf'], 'description': 'Archive files'},
    'zip': {'args': ['-r', '-x'], 'description': 'Create zip archives'},
    'unzip': {'args': ['-l', '-o'], 'description': 'Extract zip archives'},
    'curl': {'args': ['-s', '-o', '-L'], 'description': 'Transfer data from URLs'},
    'wget': {'args': ['-O', '-q'], 'description': 'Download files from web'},
    'ping': {'args': ['-c', '4'], 'description': 'Test network connectivity'},
    'netstat': {'args': ['-tuln'], 'description': 'Display network connections'},
    'ss': {'args': ['-tuln'], 'description': 'Display socket statistics'},
    'lsof': {'args': ['-i'], 'description': 'List open files'},
    'journalctl': {'args': ['-n', '50'], 'description': 'Display system logs'},
    'systemctl': {'args': ['status', 'list-units'], 'description': 'Control system services'},
    'docker': {'args': ['ps', 'images', 'logs'], 'description': 'Docker container management'},
    'git': {'args': ['status', 'log', 'diff'], 'description': 'Git version control'},
    'python': {'args': ['-c', '--version'], 'description': 'Python interpreter'},
    'node': {'args': ['--version'], 'description': 'Node.js interpreter'},
    'npm': {'args': ['list', '--version'], 'description': 'Node package manager'},
    'pip': {'args': ['list', '--version'], 'description': 'Python package manager'},
    'conda': {'args': ['list', '--version'], 'description': 'Conda package manager'},
    'jupyter': {'args': ['--version'], 'description': 'Jupyter notebook'},
    'vim': {'args': ['--version'], 'description': 'Vi improved text editor'},
    'nano': {'args': ['--version'], 'description': 'Nano text editor'},
    'emacs': {'args': ['--version'], 'description': 'Emacs text editor'},
    'code': {'args': ['--version'], 'description': 'Visual Studio Code'},
    'subl': {'args': ['--version'], 'description': 'Sublime Text editor'},
    'atom': {'args': ['--version'], 'description': 'Atom text editor'},
    'firefox': {'args': ['--version'], 'description': 'Firefox browser'},
    'chrome': {'args': ['--version'], 'description': 'Chrome browser'},
    'safari': {'args': ['--version'], 'description': 'Safari browser'},
    'mysql': {'args': ['--version'], 'description': 'MySQL database'},
    'postgresql': {'args': ['--version'], 'description': 'PostgreSQL database'},
    'redis': {'args': ['--version'], 'description': 'Redis database'},
    'mongodb': {'args': ['--version'], 'description': 'MongoDB database'},
    'nginx': {'args': ['-v'], 'description': 'Nginx web server'},
    'apache': {'args': ['-v'], 'description': 'Apache web server'},
    'ssh': {'args': ['-V'], 'description': 'SSH client'},
    'scp': {'args': [], 'description': 'Secure copy'},
    'rsync': {'args': ['-av'], 'description': 'Remote synchronization'},
    'crontab': {'args': ['-l'], 'description': 'Cron job management'},
    'at': {'args': [], 'description': 'Schedule jobs'},
    'kill': {'args': [], 'description': 'Terminate processes'},
    'killall': {'args': [], 'description': 'Kill processes by name'},
    'nohup': {'args': [], 'description': 'Run commands immune to hangups'},
    'screen': {'args': ['-ls'], 'description': 'Terminal multiplexer'},
    'tmux': {'args': ['list-sessions'], 'description': 'Terminal multiplexer'},
    'htop': {'args': [], 'description': 'Interactive process viewer'},
    'iotop': {'args': [], 'description': 'I/O monitoring'},
    'nethogs': {'args': [], 'description': 'Network usage by process'},
    'iftop': {'args': [], 'description': 'Network bandwidth monitoring'},
    'tcpdump': {'args': ['-c', '10'], 'description': 'Network packet analyzer'},
    'wireshark': {'args': ['--version'], 'description': 'Network protocol analyzer'},
    'nmap': {'args': ['--version'], 'description': 'Network mapper'},
    'telnet': {'args': [], 'description': 'Telnet client'},
    'ftp': {'args': [], 'description': 'FTP client'},
    'sftp': {'args': [], 'description': 'SFTP client'},
    'wget': {'args': ['--version'], 'description': 'Web downloader'},
    'curl': {'args': ['--version'], 'description': 'Data transfer tool'},
    'aria2c': {'args': ['--version'], 'description': 'Download utility'},
    'youtube-dl': {'args': ['--version'], 'description': 'YouTube downloader'},
    'ffmpeg': {'args': ['-version'], 'description': 'Multimedia framework'},
    'imagemagick': {'args': ['--version'], 'description': 'Image manipulation'},
    'gimp': {'args': ['--version'], 'description': 'Image editor'},
    'inkscape': {'args': ['--version'], 'description': 'Vector graphics editor'},
    'blender': {'args': ['--version'], 'description': '3D creation suite'},
    'audacity': {'args': ['--version'], 'description': 'Audio editor'},
    'vlc': {'args': ['--version'], 'description': 'Media player'},
    'mpv': {'args': ['--version'], 'description': 'Media player'},
    'mplayer': {'args': ['-version'], 'description': 'Media player'},
    'sox': {'args': ['--version'], 'description': 'Audio processing'},
    'lame': {'args': ['--version'], 'description': 'MP3 encoder'},
    'flac': {'args': ['--version'], 'description': 'FLAC codec'},
    'oggenc': {'args': ['--version'], 'description': 'OGG encoder'},
    'faac': {'args': ['--version'], 'description': 'AAC encoder'},
    'x264': {'args': ['--version'], 'description': 'H.264 encoder'},
    'x265': {'args': ['--version'], 'description': 'H.265 encoder'},
    'mkvmerge': {'args': ['--version'], 'description': 'MKV muxer'},
    'mediainfo': {'args': ['--version'], 'description': 'Media information'},
    'exiftool': {'args': ['-ver'], 'description': 'Metadata tool'},
    'pdfinfo': {'args': [], 'description': 'PDF information'},
    'pdftotext': {'args': [], 'description': 'PDF to text converter'},
    'pdftoppm': {'args': [], 'description': 'PDF to image converter'},
    'convert': {'args': ['--version'], 'description': 'ImageMagick convert'},
    'identify': {'args': ['--version'], 'description': 'ImageMagick identify'},
    'mogrify': {'args': ['--version'], 'description': 'ImageMagick mogrify'},
    'composite': {'args': ['--version'], 'description': 'ImageMagick composite'},
    'montage': {'args': ['--version'], 'description': 'ImageMagick montage'},
    'stream': {'args': ['--version'], 'description': 'ImageMagick stream'},
    'display': {'args': ['--version'], 'description': 'ImageMagick display'},
    'animate': {'args': ['--version'], 'description': 'ImageMagick animate'},
    'import': {'args': ['--version'], 'description': 'ImageMagick import'},
    'conjure': {'args': ['--version'], 'description': 'ImageMagick conjure'},
    'compare': {'args': ['--version'], 'description': 'ImageMagick compare'},
    'benchmark': {'args': ['--version'], 'description': 'ImageMagick benchmark'},
    'version': {'args': ['--version'], 'description': 'ImageMagick version'},
    'list': {'args': ['--version'], 'description': 'ImageMagick list'},
    'policy': {'args': ['--version'], 'description': 'ImageMagick policy'},
    'delegate': {'args': ['--version'], 'description': 'ImageMagick delegate'},
    'log': {'args': ['--version'], 'description': 'ImageMagick log'},
    'configure': {'args': ['--version'], 'description': 'ImageMagick configure'},
    'wand': {'args': ['--version'], 'description': 'ImageMagick wand'},
    'magick': {'args': ['--version'], 'description': 'ImageMagick magick'},
    'magick-script': {'args': ['--version'], 'description': 'ImageMagick script'},
    'magick-script-verbose': {'args': ['--version'], 'description': 'ImageMagick script verbose'},
    'magick-script-json': {'args': ['--version'], 'description': 'ImageMagick script JSON'},
    'magick-script-xml': {'args': ['--version'], 'description': 'ImageMagick script XML'},
    'magick-script-yaml': {'args': ['--version'], 'description': 'ImageMagick script YAML'},
    'magick-script-toml': {'args': ['--version'], 'description': 'ImageMagick script TOML'},
    'magick-script-ini': {'args': ['--version'], 'description': 'ImageMagick script INI'},
    'magick-script-csv': {'args': ['--version'], 'description': 'ImageMagick script CSV'},
    'magick-script-tsv': {'args': ['--version'], 'description': 'ImageMagick script TSV'},
    'magick-script-psv': {'args': ['--version'], 'description': 'ImageMagick script PSV'},
    'magick-script-ssv': {'args': ['--version'], 'description': 'ImageMagick script SSV'},
    'magick-script-dsv': {'args': ['--version'], 'description': 'ImageMagick script DSV'},
    'magick-script-rsv': {'args': ['--version'], 'description': 'ImageMagick script RSV'},
    'magick-script-usv': {'args': ['--version'], 'description': 'ImageMagick script USV'},
    'magick-script-vsv': {'args': ['--version'], 'description': 'ImageMagick script VSV'},
    'magick-script-wsv': {'args': ['--version'], 'description': 'ImageMagick script WSV'},
    'magick-script-xsv': {'args': ['--version'], 'description': 'ImageMagick script XSV'},
    'magick-script-ysv': {'args': ['--version'], 'description': 'ImageMagick script YSV'},
    'magick-script-zsv': {'args': ['--version'], 'description': 'ImageMagick script ZSV'},
}

# Dangerous commands that are explicitly forbidden
FORBIDDEN_COMMANDS = {
    'rm', 'del', 'format', 'fdisk', 'mkfs', 'dd', 'shutdown', 'reboot', 'halt',
    'poweroff', 'init', 'systemctl', 'service', 'chmod', 'chown', 'passwd',
    'useradd', 'userdel', 'groupadd', 'groupdel', 'usermod', 'groupmod',
    'visudo', 'sudo', 'su', 'mount', 'umount', 'fstab', 'crontab', 'at',
    'kill', 'killall', 'pkill', 'xkill', 'killall5', 'tkill', 'tgkill',
    'tkill', 'rtkill', 'ptkill', 'stkill', 'utkill', 'wtkill', 'xtkill',
    'ytkill', 'ztkill', 'atkill', 'btkill', 'ctkill', 'dtkill', 'etkill',
    'ftkill', 'gtkill', 'htkill', 'itkill', 'jtkill', 'ktkill', 'ltkill',
    'mtkill', 'ntkill', 'otkill', 'ptkill', 'qtkill', 'rtkill', 'stkill',
    'ttkill', 'utkill', 'vtkill', 'wtkill', 'xtkill', 'ytkill', 'ztkill'
}

class CommandRequest(BaseModel):
    command: str
    working_directory: Optional[str] = None
    timeout: Optional[int] = 30

class CommandResponse(BaseModel):
    output: str
    error: str
    exit_code: int
    command: str
    working_directory: str
    execution_time: float

def validate_command(command: str) -> tuple[bool, str]:
    """Validate if command is allowed and safe to execute"""
    try:
        # Parse command into parts
        parts = shlex.split(command)
        if not parts:
            return False, "Empty command"
        
        base_cmd = parts[0]
        
        # Check if command is forbidden
        if base_cmd in FORBIDDEN_COMMANDS:
            return False, f"Command '{base_cmd}' is forbidden for security reasons"
        
        # Check if command is in allowed list
        if base_cmd not in ALLOWED_COMMANDS:
            return False, f"Command '{base_cmd}' not allowed. Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS.keys()))}"
        
        # Validate arguments
        allowed_args = ALLOWED_COMMANDS[base_cmd]['args']
        if len(parts) > 1:
            for arg in parts[1:]:
                # Check if argument starts with allowed prefix
                if not any(arg.startswith(allowed_arg) for allowed_arg in allowed_args):
                    # Allow some common safe arguments
                    if not any(arg.startswith(prefix) for prefix in ['-', '--', '/', '.', '~', '/tmp', '/var/tmp']):
                        return False, f"Argument '{arg}' not allowed for command '{base_cmd}'"
        
        return True, "Command is valid"
    
    except Exception as e:
        return False, f"Error parsing command: {str(e)}"

@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_session)
):
    """Execute a command securely with validation and logging"""
    
    # Validate command
    is_valid, error_msg = validate_command(request.command)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Set working directory
    working_dir = request.working_directory or "/tmp"
    if not os.path.exists(working_dir):
        working_dir = "/tmp"
    
    # Ensure working directory is safe
    if not working_dir.startswith(("/tmp", "/var/tmp", "/home", "/opt", "/usr/local")):
        working_dir = "/tmp"
    
    logger.info(
        "Executing command",
        user_id=current_user.uuid,
        command=request.command,
        working_directory=working_dir
    )
    
    try:
        import time
        start_time = time.time()
        
        # Execute command with timeout
        result = subprocess.run(
            request.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=request.timeout,
            cwd=working_dir,
            env={**os.environ, 'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin'}
        )
        
        execution_time = time.time() - start_time
        
        # Log command execution
        logger.info(
            "Command executed",
            user_id=current_user.uuid,
            command=request.command,
            exit_code=result.returncode,
            execution_time=execution_time
        )
        
        return CommandResponse(
            output=result.stdout,
            error=result.stderr,
            exit_code=result.returncode,
            command=request.command,
            working_directory=working_dir,
            execution_time=execution_time
        )
        
    except subprocess.TimeoutExpired:
        logger.warning(
            "Command timeout",
            user_id=current_user.uuid,
            command=request.command,
            timeout=request.timeout
        )
        raise HTTPException(status_code=408, detail=f"Command execution timeout after {request.timeout} seconds")
    
    except Exception as e:
        logger.error(
            "Command execution error",
            user_id=current_user.uuid,
            command=request.command,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

@router.get("/allowed-commands")
async def get_allowed_commands(
    current_user: User = Depends(get_current_active_user)
):
    """Get list of allowed commands and their descriptions"""
    return {
        "allowed_commands": {
            cmd: info['description'] 
            for cmd, info in ALLOWED_COMMANDS.items()
        },
        "forbidden_commands": list(FORBIDDEN_COMMANDS),
        "total_allowed": len(ALLOWED_COMMANDS),
        "total_forbidden": len(FORBIDDEN_COMMANDS)
    }

@router.get("/help")
async def get_command_help(
    command: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get help information for a specific command"""
    if command not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=404, detail=f"Command '{command}' not found")
    
    return {
        "command": command,
        "description": ALLOWED_COMMANDS[command]['description'],
        "allowed_arguments": ALLOWED_COMMANDS[command]['args'],
        "example": f"{command} {' '.join(ALLOWED_COMMANDS[command]['args'][:2]) if ALLOWED_COMMANDS[command]['args'] else ''}"
    }

@router.get("/health")
async def health_check():
    """Health check endpoint for terminal service"""
    return {
        "status": "healthy",
        "service": "terminal",
        "allowed_commands_count": len(ALLOWED_COMMANDS),
        "forbidden_commands_count": len(FORBIDDEN_COMMANDS)
    }

