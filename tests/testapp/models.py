from django.db import models


class Book(models.Model):
    title = models.CharField("Title", max_length=255)
    author = models.CharField("Author", max_length=255)
    isbn = models.CharField("ISBN", max_length=13)
    pages = models.PositiveIntegerField("Pages")
    notes = models.TextField("Notes", blank=True, default="")
    legacy_data = models.TextField("Legacy data", blank=True, default="")

    def __str__(self):
        return self.title
