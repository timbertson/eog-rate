import os, sys
import dumbattr
import operator

from eog_rate.const import RATING, TAGS
import optparse

def ls(roots, show_details=True):
	for root in roots:
		for path, attrs in _each(root):
			_print(
					path,
					rating=_parse_rating(attrs),
					tags=_parse_tags(attrs),
					show_details=show_details)

def _parse_tags(attrs):
	try:
		s = attrs[TAGS]
	except KeyError:
		return set()
	else:
		return set([t.strip() for t in s.split(",")])

def _parse_rating(attrs):
	s = attrs.get(RATING, 0)
	try:
		return int(s)
	except ValueError:
		return 0


def _print(path, rating, tags, show_details):
	if not show_details:
		print path
		return
	stars = '*' * rating
	parts = ["%3s %s" % (stars, path)]
	if tags:
		parts.append("// %s" % (", ".join(tags),))
	print "\t".join(parts)

def query(predicate, roots, show_details=True):
	expr = compile(predicate, '(predicate)', 'eval')
	for root in roots:
		for path, attrs in _each(root):
			rating = _parse_rating(attrs)
			tags = _parse_tags(attrs)
			show = eval(expr, {'rating': rating, 'tags': tags, 'r':rating,'t':tags,'op':operator})
			if show:
				_print(path, rating=rating, tags=tags, show_details=show_details)

def _each(root):
	if os.path.isfile(root):
		root, filename = os.path.split(root)
		attrs = dumbattr.stored_view(root).get(filename, {})
		if RATING in attrs or TAGS in attrs:
			yield root, attrs
	else:
		for path, dirs, files in os.walk(root):
			meta = dumbattr.stored_view(path)
			if meta:
				for filename, attrs in meta.items():
					if RATING in attrs or TAGS in attrs:
						yield os.path.join(path, filename), attrs

def main(argv=None):
	p = optparse.OptionParser(usage="%prog [OPTIONS] path", description="Lists eog-rate metadata for all files under a given directory")
	p.add_option('-q','--query', help='python predicate to filter on, which can use the following variables: `rating` or `r` (int), `tags` or `t` (set of strings)')
	p.add_option('-p','--path', action='store_true', dest='path_only', help='print path only (no rating or tags)')
	opts, paths = p.parse_args(argv)
	assert len(paths) > 0, "Insufficient arguments"
	if opts.query:
		return query(opts.query, paths, show_details = not opts.path_only)
	else:
		return ls(paths, show_details = not opts.path_only)


if __name__ == '__main__':
	sys.exit(main())

