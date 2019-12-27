import pytest
import cmdy
import sys
from diot import Diot, OrderedDiot
from pathlib import Path
from pyppl_rich import format_dict

python = cmdy.python.bake(_exe = sys.executable, _raise = False)

pipeline1 = Path(__file__).parent.joinpath('pipeline1.py')


@pytest.mark.parametrize('val,keylen,alias,expt',[
	('a', 0, None, "a"),
	('a', 0, 'b', "[b] a"),
	(Diot(), 0, 'l', '[l] <Diot> {  }'),
	({"a":1}, 0, 'l', '[l] { a: 1 }'),
	({"a":1, "b":2}, 0, 'x',
	# =>
	    '[x] { a: 1,\n'
	'          b: 2, }'),
	({"a":1, "b11":2}, 0, None,
	# =>
	    '{ a  : 1,\n'
	'      b11: 2, }'),
	({"a":1, "b":2}, 4, 'x11',
	# =>
	        '[x11] { a: 1,\n'
	'                b: 2, }'),
	(OrderedDiot([("a",1), ("b",2)]), 4, 'x11',
	# =>
	        '[x11] <OrderedDiot> \n'
	'              { a: 1,\n'
	'                b: 2, }'),
])
def test_format_dict(val, keylen, alias, expt):
	assert format_dict(val, keylen, alias) == expt

def test_rich():
	err = python(pipeline1).stderr
	assert 'a      => 1' in err
	assert '... (2),' in err
	assert 'p1: [1/1] infile => [ ' in err
	assert 'p1: forks  => 2' in err
	assert 'p1: runner => local' in err
	assert 'afile  => ' in err
	assert 'p1: [1/1] bfile  => [ ' in err
	assert 'p1: [1/1] cfile  => [ ' in err
