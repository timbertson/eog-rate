import os, sys
import dumbattr
import operator

from eog_rate.const import RATING, TAGS, COMMENT
from eog_rate import util
import optparse

def ls(roots, show_details=True):
	for root in roots:
		for path, attrs in _each(root):
			_print(
					path,
					rating=util.get_rating(attrs),
					tags=util.get_tags(attrs),
					comment=util.get_comment(attrs),
					show_details=show_details)

def _print(path, rating, tags, comment, show_details):
	if not show_details:
		print(path)
		return
	stars = '*' * rating
	parts = ["%3s %s" % (stars, path)]
	if tags:
		parts.append(" [%s]" % (", ".join(tags),))
	if comment:
		parts.append(" #%s" % (comment,))
	print("\t".join(parts))

def query(predicate, roots, show_details=True):
	expr = compile(predicate, '(predicate)', 'eval')
	for root in roots:
		for path, attrs in _each(root):
			rating = util.get_rating(attrs)
			tags = util.get_tags(attrs)
			comment = util.get_comment(attrs)
			show = eval(expr, {
				'rating': rating,
				'tags': tags,
				'r':rating,
				't':tags,
				'comment':comment,
				'c':comment,
				'op':operator,
			})
			if show:
				_print(path, rating=rating, tags=tags, comment=comment, show_details=show_details)

def modify(opts, paths):
	cache = dumbattr.CachingAttributeStore()
	for path in paths:
		attrs = dumbattr.load(path)

		tags = util.get_tags(attrs)
		orig_tags = tags.copy()

		if opts.set_tags is not None:
			tags = util.parse_tag_str(opts.set_tags)
		else:
			tags.update(opts.add_tags)
			tags.difference_update(opts.remove_tags)
		if tags != orig_tags:
			if tags:
				attrs[TAGS] = util.render_tags(tags)
			else:
				del attrs[TAGS]
			# print("Updated tags to %r for %s" % (tags, path))

		if opts.set_rating is not None:
			if opts.set_rating:
				attrs[RATING] = str(opts.set_rating)
			else:
				del attrs[RATING]
			# print("Updated rating to %r for %s" % (rating, path))

		if opts.set_comment is not None:
			if opts.set_comment:
				attrs[COMMENT] = opts.set_comment
			else:
				del attrs[COMMENT]


def _each(root):
	if os.path.isfile(root):
		root, filename = os.path.split(root)
		attrs = dumbattr.stored_view(root).get(filename, {})
		yield root, attrs
	else:
		for path, dirs, files in os.walk(root):
			meta = dumbattr.stored_view(path)
			if meta:
				for filename in sorted(files):
					try:
						attrs = meta[filename]
					except KeyError: continue
					else:
						yield os.path.join(path, filename), attrs

def main(argv=None):
	p = optparse.OptionParser(usage="%prog [OPTIONS] path [path ...]\nor:    %prog run (to launch eog itself)",
			description="Lists, queries or sets eog-rate metadata.\n\n" +
			"Use `%prog run [args ...]` to launch eog itself with this plugin enabled",
			prog="eog-rate")
	p.add_option('-q','--query', help='python predicate to filter on, which can use the following variables: `rating` or `r` (int), `tags` or `t` (set of strings)')
	p.add_option('-p','--path', action='store_true', dest='path_only', help='print path only (no rating or tags)')
	p.add_option('--tag', dest='add_tags', action='append', default=[], metavar='TAG', help='add tag to existing set for all files listed')
	p.add_option('--untag', dest='remove_tags', action='append', default=[], metavar='TAG', help='remove tag from existing set for all files listed')
	p.add_option('--comment', dest='set_comment', help='set comment for all files listed')
	p.add_option('--set-tags', metavar='TAGS', help='set tags to the given value (a comma-separated list) for all files listed')
	p.add_option('--rating', dest='set_rating', metavar='NUMBER', help='set rating to the given value (typically between 0-3, but this is not enforced)', type='int')
	opts, paths = p.parse_args(argv)
	assert len(paths) > 0, "Insufficient arguments"
	if paths[0] == 'run':
		print("Running eog...")
		cmd = ['eog', '--new-instance'] + paths[1:]
		os.execvp('eog',cmd)
	if opts.add_tags or opts.remove_tags or (opts.set_tags is not None) or (opts.set_comment is not None) or opts.set_rating is not None:
		# modification mode:
		return modify(opts, paths)
	elif opts.query:
		# query mode
		return query(opts.query, paths, show_details = not opts.path_only)
	else:
		# list mode by default
		return ls(paths, show_details = not opts.path_only)


if __name__ == '__main__':
	sys.exit(main())

