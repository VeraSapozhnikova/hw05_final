import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.username = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая заголовок",
            slug="test-slug",
            description="Тестовое описание",
        )
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.image_name = "small_gif"
        cls.uploaded = SimpleUploadedFile(
            name=cls.image_name, content=small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            text="Тест 15символов",
            pub_date="Тестовая дата",
            author=cls.username,
            group=cls.group,
            image=cls.uploaded,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.username)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def check_contex(self, response, bool=False):
        """Проверка контекста. Общая функция для тестов страниц."""
        if bool:
            post = response.context.get("post")
        else:
            post = response.context["page_obj"][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image.name, f"posts/{self.uploaded}")
        self.assertContains(response, "<img", count=2)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон и HTTP статус."""
        templates_page_names = {
            reverse("posts:group_list", kwargs={"slug": self.group.slug}): (
                "posts/group_list.html"
            ),
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:profile", kwargs={"username": (self.username)}
            ): "posts/profile.html",
            reverse("posts:post_create"): "posts/create_post.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": (self.post.pk)}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": (self.post.pk)}
            ): "posts/create_post.html",
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_show_correct_context(self):
        """Шаблоны posts сформированы с правильным контекстом."""
        namespace_list = {
            reverse("posts:index"): "page_obj",
            reverse("posts:group_list", args=[self.group.slug]): "page_obj",
            reverse("posts:profile", args=[self.username]): "page_obj",
            reverse("posts:post_detail", args=[self.post.pk]): "post",
        }
        for reverse_name, context in namespace_list.items():
            first_object = self.guest_client.get(reverse_name)
            if context == "post":
                first_object = first_object.context[context]
            else:
                first_object = first_object.context[context][0]
            post_text = first_object.text
            post_author = first_object.author
            post_group = first_object.group
            posts_dict = {
                post_text: self.post.text,
                post_author: self.username,
                post_group: self.group,
            }
            for post_param, test_post_param in posts_dict.items():
                with self.subTest(
                    post_param=post_param, test_post_param=test_post_param
                ):
                    self.assertEqual(post_param, test_post_param)

    def test_create_post_show_correct_context(self):
        """Шаблоны create и edit сформированы с правильным контекстом."""
        namespace_list = [
            reverse("posts:post_create"),
            reverse("posts:post_edit", args=[self.post.pk]),
        ]
        for reverse_name in namespace_list:
            response = self.authorized_client.get(reverse_name)
            form_fields = {
                "text": forms.fields.CharField,
                "group": forms.fields.ChoiceField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context["form"].fields[value]
                    self.assertIsInstance(form_field, expected)

    def test_post_another_group(self):
        """Пост не попал в другую группу."""
        response = self.authorized_client.get(
            reverse("posts:group_list", args={self.group.slug})
        )
        first_object = response.context["page_obj"][0]
        post_text = first_object.text
        self.assertTrue(post_text, "Тестовый текст")

    def test_cache(self):
        """Тестируем кэш."""
        post = Post.objects.create(
            text="text",
            author=self.username,
            group=self.group
        )
        response = self.authorized_client.get(reverse("posts:index"))
        response_post = response.context["page_obj"][0]
        self.assertEqual(post, response_post)
        post.delete()
        response_2 = self.authorized_client.get(reverse("posts:index"))
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse("posts:index"))
        self.assertNotEqual(response.content, response_3.content)


class PostPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.username = User.objects.create_user(username="author")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        for post_number in range(13):
            cls.post = Post.objects.create(
                text="Тест 15символов", author=cls.username, group=cls.group
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.username)

    def test_first_page_contains_ten_posts(self):
        """Количество постов на первой странице должно быть равно 10."""
        namespace_list = {
            "posts:index": reverse("posts:index"),
            "posts:group_list": reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ),
            "posts:profile": reverse(
                "posts:profile", kwargs={"username": self.username}
            ),
        }
        count_posts = 10
        for template, reverse_name in namespace_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context["page_obj"]), count_posts)

    def test_second_page_contains_ten_posts(self):
        """Количество постов на второй странице должно быть равно 3."""
        namespace_list = {
            "posts:index": reverse("posts:index") + "?page=2",
            "posts:group_list": reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            )
            + "?page=2",
            "posts:profile": reverse(
                "posts:profile", kwargs={"username": self.username}
            )
            + "?page=2",
        }
        count_posts = 3
        for template, reverse_name in namespace_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context["page_obj"]), count_posts)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.username_follower = User.objects.create_user(username="user")
        cls.username_following = User.objects.create_user(username="user_1")
        cls.post = Post.objects.create(
            author=cls.username_following,
            text="Тестовый текст",
        )

    def setUp(self):
        self.following_client = Client()
        self.follower_client = Client()
        self.following_client.force_login(self.username_following)
        self.follower_client.force_login(self.username_follower)

    def test_follow(self):
        """Зарегистрированный пользователь может подписываться."""
        follower_count = Follow.objects.count()
        self.follower_client.get(
            reverse(
                "posts:profile_follow",
                args=(self.username_following.username,)
            )
        )
        self.assertEqual(Follow.objects.count(), follower_count + 1)

    def test_unfollow(self):
        """Зарегистрированный пользователь может отписаться."""
        Follow.objects.create(
            user=self.username_follower, author=self.username_following
        )
        follower_count = Follow.objects.count()
        self.follower_client.get(
            reverse(
                "posts:profile_unfollow",
                args=(self.username_following.username,)
            )
        )
        self.assertEqual(Follow.objects.count(), follower_count - 1)

    def test_new_post_see_follower(self):
        """Пост появляется в ленте подписавшихся."""
        posts = Post.objects.create(
            text=self.post.text,
            author=self.username_following,
        )
        follow = Follow.objects.create(
            user=self.username_follower, author=self.username_following
        )
        response = self.follower_client.get(reverse("posts:follow_index"))
        post = response.context["page_obj"][0]
        self.assertEqual(post, posts)
        follow.delete()
        response_2 = self.follower_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response_2.context["page_obj"]), 0)
