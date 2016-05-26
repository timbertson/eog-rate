#!/usr/bin/env python
import os
import subprocess
import traceback
from gi.repository import GObject, Eog, Gtk, Gio, GLib
import logging
import dumbattr
logging.getLogger('dumbattr').setLevel(logging.INFO)

from .const import RATING, TAGS, COMMENT
from . import util

_MENU_ID = 'eog-rate'

class EogRatePlugin(GObject.Object, Eog.WindowActivatable):

	# Override EogWindowActivatable's window property
	window = GObject.property(type=Eog.Window)

	def __init__(self):
		GObject.Object.__init__(self)
		self.app = Eog.Application.get_instance()
		self.actions = []
		self.statusbars = ()
		self.thumbview_signal = None
	
	@property
	def _gear_menu_section(self):
		return self.window.get_gear_menu_section('plugins-section')

	def do_activate(self):
		self.do_deactivate() # idempotent
		model = self._gear_menu_section
		menu = Gio.Menu()
		item = Gio.MenuItem.new_section(_(u'Rate'), menu)
		item.set_attribute([('id', 's', _MENU_ID)])

		def add_menu_item(label, action_name, cb, accel = None):
			action = Gio.SimpleAction.new(action_name)
			full_action_name = 'win.' + action_name
			action.connect('activate', cb, self.window)
			self.window.add_action(action)
			self.actions.append(action_name)

			menu.append(label, full_action_name)
			if accel is not None:
				self.app.set_accels_for_action(full_action_name, [accel])
				print("NOTE: set up accels %r for action %r" % (
					self.app.get_accels_for_action(full_action_name), full_action_name)
				)

		star = u'\u2605'
		for i in range(0,4):
			accel = str(i)
			if i > 0:
				# workaround for https://bugzilla.gnome.org/show_bug.cgi?id=690931
				accel = str(i+1)

			add_menu_item(
				label = u'%s: %s' % (i, star * i),
				action_name = 'eog-rate-%s' % (i,),
				cb = self.make_rate_cb(i),
				accel = accel)

		add_menu_item(
			label = _(u'Edit tags'),
			action_name = 'eog-rate-tag',
			cb = self.wrap_errors(self.edit_tag_cb),
			accel = '<Ctrl>t')

		add_menu_item(
			label = _(u'Edit comment'),
			action_name = 'eog-rate-comment',
			cb = self.wrap_errors(self.edit_comment_cb),
			accel = '<Ctrl>k')

		model.append_item(item)

		# insert statusbar
		window_statusbar = self.window.get_statusbar()
		self.statusbars = (Gtk.Statusbar(), Gtk.Statusbar(), Gtk.Statusbar())
		for bar in self.statusbars:
			window_statusbar.pack_end(bar, False, False, 10)

		# bind statusbar updates
		thumbview = self.window.get_thumb_view()
		self.thumbview_signal = (thumbview, thumbview.connect_after("selection-changed", self.update_statusbar))
		self.update_statusbar(thumbview)
	
	def do_deactivate(self):
		for action in self.actions:
			self.window.remove_action(action)
		self.actions = []

		menu = self._gear_menu_section
		for i in range(0, menu.get_n_items()):
			value = menu.get_item_attribute_value(i, 'id', GLib.VariantType.new('s'))
			if value and value.get_string() == _MENU_ID:
				menu.remove(i)
				break

		# un-bind statubar updates
		if self.thumbview_signal:
			(thumbview, signal) = self.thumbview_signal
			thumbview.disconnect(signal)
			self.thumbview_signal = None

		# remove statusbar
		for bar in self.statusbars:
			bar.destroy()
		self.statusbars = ()
	
	def _statusbar_at(self, idx):
		try:
			return self.statusbars[idx]
		except KeyError:
			return None

	@property
	def statusbar_stars(self): return self._statusbar_at(0)

	@property
	def statusbar_tags(self): return self._statusbar_at(1)

	@property
	def statusbar_comment(self): return self._statusbar_at(2)
	
	def wrap_errors(self, fn):
		def _(*a, **k):
			try:
				return fn(*a, **k)
			except Exception as e:
				dialog = Gtk.MessageDialog(
						parent=self.window,
						flags=(Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL),
						message_type = Gtk.MessageType.ERROR,
						buttons = Gtk.ButtonsType.OK,
						message_format="An error occurred in eog-rate:")
				dialog.format_secondary_text('''%s: %s\n\n%s''' % (type(e).__name__, str(e), traceback.format_exc()))
				dialog.run()
				dialog.destroy()
				raise
		return _

	def _change_attr(self, attrs, key, val):
		if not val:
			if key in attrs:
				del attrs[key]
		else:
			attrs[key] = str(val)
		self.update_ui(attrs)

	def make_rate_cb(self, val):
		def cb(action, param, window):
			attrs = self.current_attrs(window)
			self._change_attr(attrs, RATING, val)
		return self.wrap_errors(cb)

	def current_attrs(self, window):
		thumbview = window.get_thumb_view()
		img = thumbview.get_first_selected_image()
		f = img.get_file()
		return dumbattr.load(os.path.realpath(f.get_path()))

	def update_ui(self, attrs):
		stars = util.get_rating(attrs)
		STAR = u'\u2605'
		VACANT_STAR = u'\u2606'
		star_str = (STAR * stars) + (VACANT_STAR * (3 - stars))

		tags = util.get_tags(attrs)
		comment = util.get_comment(attrs, max_length=15)

		self.statusbar_stars.pop(0)
		self.statusbar_stars.push(0, star_str)
		self.statusbar_stars.show()
		
		if tags:
			self.statusbar_tags.pop(0)
			tags = "[%s]" % (util.render_tags(tags),)
			self.statusbar_tags.push(0, tags)
			self.statusbar_tags.show()
		else:
			self.statusbar_tags.hide()

		if comment:
			self.statusbar_comment.pop(0)
			comment = "#%s" % (comment,)
			self.statusbar_comment.push(0, comment)
			self.statusbar_comment.show()
		else:
			self.statusbar_comment.hide()

	def update_statusbar(self, thumbview):
		num_selected = thumbview.get_n_selected()

		# if num_selected == 0:
		# 	print "(no selection)"
		# if num_selected > 1:
		# 	print "(multi selection)"

		if num_selected != 1:
			for bar in self.statusbars:
				bar.hide()
			return

		attrs = self.current_attrs(self.window)
		self.update_ui(attrs)

	def edit_tag_cb(self, action, param, window):
		attrs = self.current_attrs(window)
		tags = util.get_tags(attrs)
		dialog = Gtk.Dialog("Tag editor", parent=window, flags=(Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL))

		entry = Gtk.Entry()
		#TODO: GtkEntryCompletion
		entry.set_text(util.render_tags(tags))
		label = Gtk.Label("Edit tags:")
		box = dialog.get_content_area()
		box.add(label)
		box.add(entry)

		dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
		dialog.add_button("OK", Gtk.ResponseType.OK)
		dialog.set_default_response(Gtk.ResponseType.OK)
		entry.set_property("activates-default", True)

		dialog.show_all()

		def cb(dialog, response):
			if response == Gtk.ResponseType.OK:
				self._change_attr(attrs, TAGS, entry.get_text().strip())
			else:
				pass # cancelled
			dialog.destroy()
		dialog.connect("response", cb)
		dialog.show()


	def edit_comment_cb(self, action, param, window):
		attrs = self.current_attrs(window)
		comment = attrs.get(COMMENT, '')
		dialog = Gtk.Dialog("Comment editor", parent=window, flags=(Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL))

		entry = Gtk.Entry()
		#TODO: GtkEntryCompletion
		entry.set_text(comment)
		label = Gtk.Label("Edit comment:")
		box = dialog.get_content_area()
		box.add(label)
		box.add(entry)

		dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
		dialog.add_button("OK", Gtk.ResponseType.OK)
		dialog.set_default_response(Gtk.ResponseType.OK)
		entry.set_property("activates-default", True)

		dialog.show_all()

		def cb(dialog, response):
			if response == Gtk.ResponseType.OK:
				self._change_attr(attrs, COMMENT, entry.get_text().strip())
			else:
				pass # cancelled
			dialog.destroy()
		dialog.connect("response", cb)
		dialog.show()
