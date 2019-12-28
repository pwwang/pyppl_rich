
from pyppl import Proc, PyPPL, config_plugins
import pyppl_rich
config_plugins(pyppl_rich)
from tempfile import gettempdir

p1 = Proc(
	input = 'infile:files, afile:file, bfile:files, cfile:files',
	output = 'a:1',
	cache = False,
	script = "echo 1",
	args = {'a': 1})

p1.input = [__file__] *5, __file__, [__file__], [__file__]*2
p1.forks = 2

PyPPL(ppldir = gettempdir() + '/pyppl_rich_tests').start(p1).run()
