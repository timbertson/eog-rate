#!/usr/bin/env python
import os
import subprocess
import traceback
from gi.repository import GObject, Eog, Gtk
import logging
import dumbattr
logging.getLogger('dumbattr').setLevel(logging.INFO)

from .const import RATING, TAGS, COMMENT
from . import util

ui_str = """
	<ui>
	  <menubar name="MainMenu">
	    <menu name="ToolsMenu" action="Tools">
	      <separator/>
	      <menuitem name="eog_rate_label" action="eog_rate_label"/>
	      <menuitem name="eog_rate_0" action="eog_rate_0"/>
	      <menuitem name="eog_rate_1" action="eog_rate_1"/>
	      <menuitem name="eog_rate_2" action="eog_rate_2"/>
	      <menuitem name="eog_rate_3" action="eog_rate_3"/>
	      <menuitem name="eog_rate_tag" action="eog_rate_tag"/>
	      <menuitem name="eog_rate_comment" action="eog_rate_comment"/>
	      <separator/>
	    </menu>
	  </menubar>
	</ui>
	"""

class EogRatePlugin(GObject.Object, Eog.WindowActivatable):

	# Override EogWindowActivatable's window property
	window = GObject.property(type=Eog.Window)

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		ui_manager = self.window.get_ui_manager()
		self.action_group = Gtk.ActionGroup('eog_rate')

		action = Gtk.Action('eog_rate_label', _(u'Rate'), None, None)
		action.set_sensitive(False)
		self.action_group.add_action(action)

		star = u'\u2605'
		for i in range(0,4):
			action = Gtk.Action('eog_rate_%s' % i, _(u'%s: %s' % (i, star * i)), None, None)
			action.connect('activate', self.make_rate_cb(i), self.window)
			# accel = '<alt>%s' % (i,)
			accel = str(i)
			if i > 0:
				# workaround for https://bugzilla.gnome.org/show_bug.cgi?id=690931
				accel = str(i+1)
			self.action_group.add_action_with_accel(action, accel)

		action = Gtk.Action('eog_rate_tag', _(u'Edit tags'), None, None)
		action.connect('activate', self.wrap_errors(self.edit_tag_cb), self.window)
		self.action_group.add_action_with_accel(action, "<Ctrl>t")

		action = Gtk.Action('eog_rate_comment', _(u'Edit comment'), None, None)
		action.connect('activate', self.wrap_errors(self.edit_comment_cb), self.window)
		self.action_group.add_action_with_accel(action, "<Ctrl>k")

		ui_manager.insert_action_group(self.action_group, 0)
		self.ui_id = ui_manager.add_ui_from_string(ui_str)

		# insert statusbar
		window_statusbar = self.window.get_statusbar()
		self.statusbars = (Gtk.Statusbar(), Gtk.Statusbar(), Gtk.Statusbar())
		for bar in self.statusbars:
			window_statusbar.pack_end(bar, False, False, 10)

		self.statusbar_comment, self.statusbar_tags, self.statusbar_stars = self.statusbars

		# bind statusbar updates
		thumbview = self.window.get_thumb_view()
		self.thumbview_signal = (thumbview, thumbview.connect_after("selection-changed", self.update_statusbar))
		self.update_statusbar(thumbview)
	
	def do_deactivate(self):
		ui_manager = self.window.get_ui_manager()
		ui_manager.remove_ui(self.ui_id)
		self.ui_id = 0
		ui_manager.remove_action_group(self.action_group)
		self.action_group = None
		ui_manager.ensure_update()

		# un-bind statubar updates
		(thumbview, signal) = self.thumbview_signal
		thumbview.disconnect(signal)

		# remove statusbar
		for bar in self.statusbars:
			bar.destroy()
		self.statusbars = None
		self.statusbar_stars, self.statusbar_tags, self.statusbar_comment = (None, None, None)
	
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
		def cb(action, window):
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

	def edit_tag_cb(self, action, window):
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


	def edit_comment_cb(self, action, window):
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
