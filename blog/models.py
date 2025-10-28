from django.db import models
from django.conf import settings  # WAŻNE - używamy settings zamiast importować User

class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tytuł")
    slug = models.SlugField(unique=True, verbose_name="Slug (URL)")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # To zamiast User - wskazuje na Twój custom user
        on_delete=models.CASCADE,
        verbose_name="Autor"
    )
    content = models.TextField(verbose_name="Treść")
    excerpt = models.TextField(
        max_length=300, 
        blank=True, 
        verbose_name="Krótki opis (meta)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data aktualizacji")
    published = models.BooleanField(default=False, verbose_name="Opublikowany")


    featured_image = models.ImageField(
        upload_to='media/blog/images/',  # ← Musi być DOKŁADNIE tak
        blank=True,
        null=True,
        verbose_name="Zdjęcie wyróżniające"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Post"
        verbose_name_plural = "Posty"
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog:post_detail', kwargs={'slug': self.slug})