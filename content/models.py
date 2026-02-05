from django.db import models


class News(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()

    # картинка для карточки/лайтбокса
    image = models.ImageField(upload_to="news/", blank=True, null=True)

    # дата публикации для лайтбокса :contentReference[oaicite:4]{index=4}
    published_at = models.DateTimeField()

    # сортировка для слайдера (drag-and-drop на админке можно имитировать этим полем)
    order = models.PositiveIntegerField(default=0)

    # чтобы можно было скрывать новость, не удаляя
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-published_at"]

    def __str__(self):
        return self.title
