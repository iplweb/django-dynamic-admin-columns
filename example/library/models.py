from django.db import models
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    title = models.CharField(_("Title"), max_length=255)
    author = models.CharField(_("Author"), max_length=255)
    isbn = models.CharField(_("ISBN"), max_length=13, blank=True, default="")
    pages = models.PositiveIntegerField(_("Pages"), default=0)
    notes = models.TextField(_("Notes"), blank=True, default="")
    published_on = models.DateField(_("Published on"), null=True, blank=True)
    language = models.CharField(_("Language"), max_length=8, blank=True, default="")

    class Meta:
        ordering = ("title",)
        verbose_name = _("Book")
        verbose_name_plural = _("Books")

    def __str__(self):
        return self.title
