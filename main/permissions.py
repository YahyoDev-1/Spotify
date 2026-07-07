from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Obyekt egasigina uni o'zgartira oladi, qolganlarga faqat o'qish.

    has_object_permission bitta obyekt ustida amal bo'lganda ishlaydi
    (retrieve, update, delete) — list va create'ga ta'sir qilmaydi.
    """

    def has_object_permission(self, request, view, obj):
        # GET, HEAD, OPTIONS — "xavfsiz" metodlar, hammaga ruxsat
        if request.method in permissions.SAFE_METHODS:
            return True
        # Yozish amallari faqat egasiga
        return obj.user == request.user
