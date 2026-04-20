"""Модуль содержит дополнительные классы
для настройки основных классов приложения.
"""
from django.db.models import Model, Q
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)


class AddDelViewMixin:
    """
    Добавляет во Viewset дополнительные методы.

    Содержит методы для добавления или удаления объекта связи
    Many-to-Many между моделями.
    Требует определения атрибутов `add_serializer` и `link_model`.

    Example:
        class ExampleViewSet(ModelViewSet, AddDelViewMixin)
            ...
            add_serializer = ExamplSerializer
            link_model = M2M_Model
    """

    add_serializer: ModelSerializer | None = None
    link_model: Model | None = None

    def _create_relation(self, obj_id: int | str) -> Response:
        """Добавляет связь M2M между объектами.

        Args:
            obj_id (int | str):
                `id` объекта, с которым требуется создать связь.

        Returns:
            Responce: Статус подтверждающий/отклоняющий действие.
        """
        from django.db import transaction

        obj = get_object_or_404(self.queryset, pk=obj_id)
        filter_kwargs = self._get_filter_kwargs(obj)

        if self.link_model.objects.filter(**filter_kwargs).exists():
            return Response(
                {"error": "Действие выполнено ранее."},
                status=HTTP_400_BAD_REQUEST,
            )

        if hasattr(self.link_model, 'author') and obj == self.request.user:
            return Response(
                {"error": "Нельзя подписаться на самого себя."},
                status=HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                self.link_model.objects.create(**filter_kwargs)
        except IntegrityError:
            return Response(
                {"error": "Действие не может быть выполнено."},
                status=HTTP_400_BAD_REQUEST,
            )

        serializer: ModelSerializer = self.add_serializer(obj)
        return Response(serializer.data, status=HTTP_201_CREATED)

    def _get_filter_kwargs(self, obj):
        """Возвращает аргументы для фильтрации связи.

        Args:
            obj: Объект для создания связи.

        Returns:
            dict: Аргументы для filter()/create().
        """
        if hasattr(self.link_model, 'recipe'):
            return {
                'recipe': obj,
                'user': self.request.user
            }
        else:
            return {
                'author': obj,
                'user': self.request.user
            }

    def _delete_relation(self, q: Q) -> Response:
        """Удаляет связь M2M между объектами.

        Args:
            q (Q):
                Условие фильтрации объектов.

        Returns:
            Responce: Статус подтверждающий/отклоняющий действие.
        """
        obj = self.link_model.objects.filter(q & Q(user=self.request.user)).first()
        if not obj:
            return Response(
                {"error": f"{self.link_model.__name__} не существует"},
                status=HTTP_400_BAD_REQUEST,
            )

        obj.delete()
        return Response(status=HTTP_204_NO_CONTENT)
