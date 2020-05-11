"""Richer information in logs for PyPPL"""
import re
import time
from os import path
from pyppl.plugin import hookimpl
from pyppl.logger import Logger
from pyppl.config import config
from pyppl.utils import format_secs
from pyppl._proc import (OUT_FILETYPE,
                         OUT_DIRTYPE,
                         OUT_STDOUTTYPE,
                         OUT_STDERRTYPE,
                         IN_FILETYPE,
                         IN_FILESTYPE)

__version__ = "0.0.4"

logger = Logger(plugin='rich') # pylint: disable=invalid-name


def format_dict(val, keylen, alias=None):
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
        return format_dict(
            alias + valtype + '{ %s: %s }' % list(val.items())[0], 0)

    valkeylen = max(len(key) for key in val)
    ret = [alias + valtype]
    key0, val0 = list(val.items())[0]
    if not alias or not valtype:
        braceindt = len(alias + valtype)
        ret[0] += '{ %s: %s,' % (
            key0.ljust(valkeylen), repr(val0) \
                if isinstance(val0, str) and re.search(r'\s+', val0) else val0)
    else:
        braceindt = len(alias)

    for keyi, vali in val.items():
        if keyi == key0 and (not alias or not valtype):
            continue
        fmt = '%s{ %s: %s,' if keyi == key0 else '%s  %s: %s,'
        ret.append(fmt % (
            ' ' * (braceindt + keylen + 4),
            keyi.ljust(valkeylen),
            (repr(vali)
             if isinstance(vali, str) and re.search(r'\s+', vali)
             else vali)
        ))
    ret[-1] += ' }'
    return '\n'.join(ret)


@hookimpl
def logger_init(logger):  # pylint: disable=redefined-outer-name
    """Initiate log levels"""
    logger.add_level('P_PROPS', 'CRITICAL')
    logger.add_level('P_ARGS', 'CRITICAL')
    logger.add_level('P_CONF', 'CRITICAL')
    logger.add_level('INPUT', 'CRITICAL')
    logger.add_level('OUTPUT', 'CRITICAL')

@hookimpl
def proc_prerun(proc):
    """Log properties have been set and args before running"""
    proc.props.rich_timer = time.time()
    prop_keys = [
        key for key in proc._setcounter
        if proc._setcounter[key] > 0 and key != 'id'
    ]
    prop_keys.append('runner')
    args_keys = list(proc.args)
    key_maxlen = 0
    if prop_keys:
        key_maxlen = max(key_maxlen, max(len(key) for key in prop_keys))
    if args_keys:
        key_maxlen = max(key_maxlen, max(len(key) for key in args_keys))
    for key in prop_keys:
        if key == 'runner':
            continue
        logger.p_props('%s => %s' %
                       (key.ljust(key_maxlen),
                        format_dict(getattr(proc, key), key_maxlen)),
                       proc=proc.id)

    logger.p_props(
        '%s => %s %s' %
        ('runner'.ljust(key_maxlen), proc.runner.runner,
         ('[profile: %s]' %
          proc._runner) if not isinstance(proc._runner, dict) else ''),
        proc=proc.id)
    for key in args_keys:
        logger.p_args(
            '%s => %s' %
            (key.ljust(key_maxlen), format_dict(proc.args[key], key_maxlen)),
            proc=proc.id)

    # plugin configs
    if proc.config:
        key_maxlen = max(len(key) for key in proc.config)
        for key in proc.config:
            # only if the plugin config is explicitly set
            # and key was set in setup
            if proc.config._meta.setcounter.get(
                    key, 0) == 0 or key not in config.config:
                continue
            logger.p_conf('%s => %s' %
                          (key.ljust(key_maxlen),
                           format_dict(proc.config[key], keylen=key_maxlen)),
                          proc=proc.id)


@hookimpl
def proc_postrun(proc, status):
    """Show time elapsed for a process"""
    if status == 'succeeded':
        logger.p_done('Time elapsed: %s',
                      format_secs(time.time() - proc.props.rich_timer),
                      proc=proc.id)


@hookimpl
def pyppl_prerun(ppl):
    """Set a timer for the pipeline execution"""
    ppl.props.rich_timer = time.time()


@hookimpl
def pyppl_postrun(ppl):
    """Show time elapsed when pipeline is done"""
    logger.done('Total time elapsed: %s',
                format_secs(time.time() - ppl.props.rich_timer))


@hookimpl
def job_build(job, status):  # pylint: disable=unused-argument
    """Log INPUT and OUTPUT and job #0 after job is built"""
    if job.index == 0:
        key_maxlen = 0
        key_maxlen = max(key_maxlen, max(len(key) for key in job.input))
        key_maxlen = max(key_maxlen, max(len(key) for key in job.output))
        for key, type_and_data in job.input.items():
            dtype, data = type_and_data
            if dtype in IN_FILETYPE:
                data = '<workdir>/%s/input/%s' % (job.index + 1,
                                                  path.basename(data))
            elif dtype in IN_FILESTYPE:
                data = ['<workdir>/%s/input/%s' % (job.index + 1,
                                                   path.basename(dat))
                        for dat in data]

            if not isinstance(data, list):
                job.logger('%s => %s' % (key.ljust(key_maxlen), data),
                           level='input')
                continue

            ldata = len(data)
            if ldata <= 1:
                job.logger("{} => [ {} ]".format(key.ljust(key_maxlen),
                                                 data and data[0] or ''),
                           level='input')
            elif ldata == 2:
                job.logger("{} => [ {},".format(key.ljust(key_maxlen),
                                                data[0]),
                           level='input')
                job.logger("{}      {} ]".format(' '.ljust(key_maxlen),
                                                 data[1]),
                           level='input')
            else:
                job.logger("{} => [ {},".format(key.ljust(key_maxlen),
                                                data[0]),
                           level='input')
                job.logger("{}      {},".format(' '.ljust(key_maxlen),
                                                data[1]),
                           level='input')
                if ldata > 3:
                    job.logger("{}      ... ({}),".format(
                        ' '.ljust(key_maxlen),
                        len(data) - 3),
                               level='input')
                job.logger("{}      {} ]".format(' '.ljust(key_maxlen),
                                                 data[-1]),
                           level='input')

        for key in job.output:
            dtype, data = type_and_data = job.output[key]
            if dtype in OUT_DIRTYPE + OUT_FILETYPE:
                data = '<workdir>/%s/output/%s' % (job.index + 1,
                                                   path.basename(data))
            elif dtype in OUT_STDOUTTYPE + OUT_STDERRTYPE:
                data = '<workdir>/%s/%s' % (job.index + 1,
                                            path.basename(data))
            job.logger('%s => %s' %
                       (key.ljust(key_maxlen), data),
                       level='output')
