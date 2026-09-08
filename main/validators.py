"""Fayl yuklash uchun maxsus validatorlar.

@deconstructible — bu dekorator validatorni migratsiyaga "seriyalash"
imkonini beradi. Model maydonida ishlatilgan har qanday validator
makemigrations tomonidan faylga yozilishi kerak, shuning uchun u
qayta tiklanadigan (deconstructible) bo'lishi shart.
"""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class MaxFileSizeValidator:
    """Fayl hajmi berilgan megabaytdan oshmasligini tekshiradi."""

    def __init__(self, max_mb):
        self.max_mb = max_mb
        self.max_bytes = max_mb * 1024 * 1024

    def __call__(self, file):
        if file.size > self.max_bytes:
            actual_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f"Fayl hajmi {self.max_mb} MB dan oshmasligi kerak "
                f"(yuklangan fayl: {actual_mb:.1f} MB)."
            )

    def __eq__(self, other):
        # Migratsiya "o'zgardimi?" deb solishtirganda kerak bo'ladi
        return isinstance(other, MaxFileSizeValidator) and self.max_mb == other.max_mb
