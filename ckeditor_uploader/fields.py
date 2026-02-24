from django.db import models


class RichTextUploadingField(models.TextField):
    """
    Legacy-compatible field used only to keep historical migrations importable.
    """

