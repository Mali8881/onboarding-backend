"""
Compatibility shim for legacy migrations.

The project migrated to django-ckeditor-5, but old migrations import
ckeditor_uploader.fields.RichTextUploadingField.
"""

