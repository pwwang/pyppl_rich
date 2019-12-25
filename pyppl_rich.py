from pyppl.plugin import hookimpl
from pyppl.logger import logger

__version__ = '0.0.2'

def format_dict(val, keylen, alias = None):
	"""Format the dict values in log
	Value            | Alias | Formatted
	-----------------|-------|-------------
	"a"              |       | a
	"a"              | b     | [b] a
	{"a": 1}         | l     | [l] { a: 1 }
	{"a": 1, "b": 2} | x     | [x] { a: 1,
	                 |       |       b: 2 }
	Diot(a=1)        |       | <Diot> { a: 1 }
	Diot(a=1,b=2)    | b     | [b] <Diot>
	                 |       |     { a: 1,
	                 |       |       b: 2 }
	"""
	alias = '[%s] ' % alias if alias else ''
	if not isinstance(val, dict):
		ret = alias
		return ret + (repr(val) if val == '' else str(val))

	valtype = val.__class__.__name__
	valtype = '' if valtype == 'dict' else '<%s> ' % valtype

	if len(val) == 0:
		return alias + valtype + '{  }'
	if len(val) == 1:
		return formatDict(alias + valtype + '{ %s: %s }' % list(val.items())[0], 0)

	valkeylen = max(len(key) for key in val)
	ret = [alias + valtype]
	key0, val0 = list(val.items())[0]
	if not alias or not valtype:
		braceindt = len(alias + valtype)
		ret[0] += '{ %s: %s,' % (
			key0.ljust(valkeylen), repr(val0) if val0 == '' else val0)
	else:
		braceindt = len(alias)

	for keyi, vali in val.items():
		if keyi == key0 and (not alias or not valtype):
			continue
		fmt = '%s{ %s: %s,' if keyi == key0 else '%s  %s: %s,'
		ret.append(fmt % (' ' * (braceindt + keylen + 4),
			keyi.ljust(valkeylen), repr(vali) if vali == '' else vali))
	ret[-1] += ' }'
	return '\n'.join(ret)

@hookimpl
def logger_init(logger):
	"""Initiate log levels"""
	logger.add_level('P_PROPS', 'CRITICAL')
	logger.add_level('P_ARGS', 'CRITICAL')
	logger.add_level('CONFIG', 'CRITICAL')
	logger.add_level('INPUT', 'CRITICAL')
	logger.add_level('OUTPUT', 'CRITICAL')

@hookimpl
def proc_prerun(proc):
	"""Log properties have been set and args before running"""
	prop_keys = [key for key in proc._setcounter
		if proc._setcounter[key] > 0 and key != 'id']
	prop_keys.append('runner')
	args_keys = list(proc.args)
	key_maxlen = 0
	if prop_keys:
		key_maxlen = max(key_maxlen,
			max(len(key) for key in prop_keys))
	if args_keys:
		key_maxlen = max(key_maxlen,
			max(len(key) for key in args_keys))
	for key in prop_keys:
		if key == 'runner':
			continue
		logger.p_props('%s => %s' % (
			key.ljust(key_maxlen),
			format_dict(getattr(proc, key), key_maxlen)), proc = proc.id)
	logger.p_props('runner => %s [profile: %s]' % (
		proc.runner.runner, proc._runner), proc = proc.id)
	for key in args_keys:
		logger.p_args('%s => %s' % (
			key.ljust(key_maxlen),
			format_dict(proc.args[key], key_maxlen)), proc = proc.id)

	# plugin configs
	if proc.config:
		key_maxlen = max(len(key) for key in proc.config)
		for key in proc.config:
			logger.config('%s => %s' % (
				key.ljust(key_maxlen),
				format_dict(proc.config[key])), proc = proc.id)

@hookimpl
def job_build(job, status):
	"""Log INPUT and OUTPUT and job #0 after job is built"""
	if job.index == 0:
		key_maxlen = 0
		key_maxlen = max(key_maxlen, max(len(key) for key in job.input))
		key_maxlen = max(key_maxlen, max(len(key) for key in job.output))
		for key, type_and_data in job.input.items():
			data = type_and_data[1]

			if not isinstance(data, list):
				job.logger('%s => %s' % (
					key.ljust(key_maxlen), data), level = 'input')
				continue

			ldata = len(data)
			if ldata <= 1:
				job.logger("{} => [ {} ]".format(
					key.ljust(key_maxlen), data and data[0] or ''), level = 'input')
			elif ldata == 2:
				job.logger("{} => [ {},".format(
					key.ljust(key_maxlen), data[0]), level = 'input')
				job.logger("{}      {} ]".format(
					' '.ljust(key_maxlen), data[1]), level = 'input')
			else:
				job.logger("{} => [ {},".format(
					key.ljust(key_maxlen), data[0]), level = 'input')
				job.logger("{}      {},".format(
					' '.ljust(key_maxlen), data[1]), level = 'input')
				if ldata > 3:
					job.logger("{}      ... ({}),".format(
						' '.ljust(key_maxlen), len(data) - 3), level = 'input')
				job.logger("{}      {} ]".format(
					' '.ljust(key_maxlen), data[-1]), level = 'input')

		for key in job.output:
			job.logger('%s => %s' % (
				key.ljust(key_maxlen), job.output[key][1]), level = 'output')
