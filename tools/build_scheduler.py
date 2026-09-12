"""Build the native solver for the current platform before packaging."""
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scheduler.native_bridge import native_binary

if __name__=='__main__':
    source=native_binary()
    target=Path(__file__).resolve().parents[1]/'scheduler'/'native'/source.name
    if source.resolve()!=target.resolve(): shutil.copy2(source,target)
    print(target)
