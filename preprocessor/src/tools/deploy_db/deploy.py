import argparse
import os
import subprocess
from pathlib import Path
from preprocessor.main import remove_temp_zarr_hierarchy_storage_folder
from preprocessor.src.preprocessors.implementations.sff.preprocessor.constants import CSV_WITH_ENTRY_IDS_FILE, DEFAULT_DB_PATH, RAW_INPUT_FILES_DIR, TEMP_ZARR_HIERARCHY_STORAGE_PATH
from preprocessor.src.tools.deploy_db.build_and_deploy import DEFAULT_FRONTEND_PORT, DEFAULT_HOST, DEFAULT_PORT

def parse_script_args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db_path", type=Path, default=DEFAULT_DB_PATH, help='path to db folder')
    parser.add_argument("--api_port", type=str, default=str(DEFAULT_PORT), help='default api port')
    parser.add_argument("--api_hostname", type=str, default=DEFAULT_HOST, help='default host')
    # NOTE: this will quantize everything (except u2/u1 thing), not what we need
    parser.add_argument("--frontend_port", type=str, default=str(DEFAULT_FRONTEND_PORT), help='default frontend port')
    
    args=parser.parse_args()
    return args

def _free_port(port_number: str):
    lst = ['killport', str(port_number)]
    subprocess.call(lst)

def run_api(args):
    if os.path.isabs(args.db_path):
        db_path = args.db_path
    else:
        db_path = Path(os.getcwd()) / args.db_path
    deploy_env = {
        **os.environ,
        # check if relative path => then convert to absolute
        'DB_PATH': db_path,
        'HOST': args.api_hostname,
        'PORT': args.api_port
        }
    lst = [
        "python", "serve.py"
    ]
    # if not figure out how to pass full path
    subprocess.Popen(lst, env=deploy_env, cwd='server/')

def run_frontend(args):
    deploy_env = {
        **os.environ,
        'REACT_APP_API_HOSTNAME': '',
        'REACT_APP_API_PORT': args.api_port,
        # NOTE: later, for now set to empty string
        'REACT_APP_API_PREFIX': ''
        }

    subprocess.call(["yarn", "--cwd", "frontend"], env=deploy_env)
    subprocess.call(["yarn", "--cwd", "frontend", "build"], env=deploy_env)
    lst = [
        "serve",
        "-s", "frontend/build",
        "-l", str(args.frontend_port)
    ]
        
    subprocess.Popen(lst)
    # subprocess.call(lst)

def shut_down_ports(args):
    _free_port(args.frontend_port)
    _free_port(args.api_port)


def deploy(args):
    shut_down_ports(args)
    run_api(args)
    run_frontend(args)

if __name__ == '__main__':
    args = parse_script_args()
    deploy(args)


