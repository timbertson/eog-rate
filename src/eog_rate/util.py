from .const import RATING, TAGS, COMMENT

def get_rating(attrs):
	s = attrs.get(RATING, 0)
	try:
		return int(s)
	except ValueError:
		return 0

def get_comment(attrs, max_length=None):
	val = attrs.get(COMMENT, "")
	if max_length is None:
		return val

	ellipsis = '...'
	return val if len(val) <= max_length else (val[:len(val) - len(ellipsis)] + ellipsis)

def get_tags(attrs):
	try:
		s = attrs[TAGS]
	except KeyError:
		return set()
	else:
		return parse_tag_str(s)

def parse_tag_str(tag_str):
	return set([t.strip() for t in tag_str.split(",") if t.strip()])

def render_tags(tag_set):
	return ", ".join(sorted(tag_set))
