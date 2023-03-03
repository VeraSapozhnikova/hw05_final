from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post

from .test_models import PostModelTest

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.username = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.username,
            text='Тест 15символов',
        )
        cls.non_author = User.objects.create_user(username='non_author')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.username)
        self.non_author_client = Client()
        self.non_author_client.force_login(self.non_author)

    def test_for_public_pages(self):
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{PostsURLTests.group.slug}/',
            'posts/profile.html':
            f'/profile/{PostsURLTests.username.username}/',
            'posts/post_detail.html': f'/posts/{PostModelTest.post.id}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertTemplateUsed(response, template)

    def test_pages_only_authorized(self):
        """
        Шаблон и страница /сreate/ доступна авторизованному
        пользователю.
        """
        address = '/create/'
        template = 'posts/create_post.html'
        response = self.non_author_client.get(address)
        self.assertTemplateUsed(response, template)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_only_author(self):
        """
        Шаблон и страница /сreate/id/ доступна автору
        для редактирования.
        """
        address = f'/posts/{PostModelTest.post.id}/edit/'
        template = 'posts/create_post.html'
        response = self.authorized_client.get(address)
        self.assertTemplateUsed(response, template)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_null_page(self):
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_authorized_correct_template(self):
        """
        Проверка шаблона /follow.html/.
        """
        response = self.authorized_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'posts/follow.html')
