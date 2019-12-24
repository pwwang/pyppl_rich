from pyppl.plugin import hookimpl
#from pyppl.logger import logger

__version__ = '0.0.1'

@hookimpl
def proc_prerun(proc):
	print('XXXXXXX')