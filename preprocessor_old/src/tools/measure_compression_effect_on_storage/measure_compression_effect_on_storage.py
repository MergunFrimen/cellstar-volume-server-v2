
from glob import glob
from pathlib import Path
from pprint import pprint
from preprocessor_old.src.preprocessors.implementations.sff.preprocessor.constants import DEFAULT_DB_PATH
from preprocessor_old.src.tools.get_dir_size.get_dir_size import get_dir_size

# TODO: compare with filesystem properties

def measure_compression_effect_on_storage():
    '''Measures per db'''
    d = {}
    db_dirs = glob('test-data/db*')
    for db_dir_str in db_dirs:
        db_dir = Path(db_dir_str)
        d[str(db_dir.name)] = get_dir_size(db_dir)

    return d

if __name__ == '__main__':
    d = measure_compression_effect_on_storage()
    pprint(d)


