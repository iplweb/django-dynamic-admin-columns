from django.db import models


class Book(models.Model):
    title = models.CharField("Title", max_length=255)
    author = models.CharField("Author", max_length=255)
    isbn = models.CharField("ISBN", max_length=13, blank=True, default="")
    pages = models.PositiveIntegerField("Pages", default=0)
    notes = models.TextField("Notes", blank=True, default="")
    published_on = models.DateField("Published on", null=True, blank=True)

    class Meta:
        ordering = ("title",)
        verbose_name = "Book"
        verbose_name_plural = "Books"

    def __str__(self):
        return self.title
