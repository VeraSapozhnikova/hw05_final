from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import POST_LENGTH, Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.username = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.username,
            text='Текст длинее 15 символов',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_value = post.text[:POST_LENGTH]
        self.assertEqual(str(post), expected_value)


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='тестовый заголовок',
            slug='test-slug',
            description='тестовое описание'
        )

    def test_models_have_correct_names(self):
        """Метод Group.__str__ выводит Group.title."""
        group = GroupModelTest.group
        expected_value = group.title
        self.assertEqual(str(group), expected_value)
